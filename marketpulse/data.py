"""Official TWSE / TPEx dated EOD adapters, normalize, and local store."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from http.client import IncompleteRead
from pathlib import Path
from typing import Any

import pandas as pd

USER_AGENT = "MarketPulse/0.2 (local personal research; no redistribution)"
TWSE_SLEEP_SEC = float(os.environ.get("MARKETPULSE_TWSE_SLEEP", "5"))

TWSE_MI_INDEX = (
    "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
    "?response=json&date={yyyymmdd}&type=ALLBUT0999"
)
# Public dated page. The older stk_quote_result.php endpoint ignores `d=`
# and returns the latest session; do not use it for historical replay.
TPEX_DAILY_QUOTES = (
    "https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQuotes"
    "?date={yyyy}/{mm}/{dd}&response=json"
)

BARS_COLUMNS = [
    "date",
    "market",
    "symbol",
    "name",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "trading_value",
]
INDEX_COLUMNS = ["date", "close"]

COMMON_STOCK = re.compile(r"^\d{4}$")


def is_listed_common(symbol: str) -> bool:
    """TWSE/TPEx ordinary shares: 4-digit, not ETFs (00xx) or TDRs (91xx)."""
    if not COMMON_STOCK.fullmatch(symbol):
        return False
    if symbol.startswith("00"):
        return False
    if symbol.startswith("91"):
        return False
    return True


def parse_num(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "--", "---", "n/a", "N/A", "-", "無", "除權", "除息", "除權息"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_yyyymmdd(value: str | date) -> date:
    if isinstance(value, date):
        return value
    text = str(value).strip().replace("/", "")
    return datetime.strptime(text, "%Y%m%d").date()


def daterange(start: date, end: date) -> list[date]:
    days: list[date] = []
    cur = start
    while cur <= end:
        days.append(cur)
        cur += timedelta(days=1)
    return days


def _fetch_json_via_wget(url: str, timeout: float = 30.0) -> str:
    """Fallback when HiNetCDN returns naked HTTP 307 to urllib."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(prefix="mp-fetch-", suffix=".json", delete=False) as tmp:
        dest = tmp.name
    try:
        subprocess.run(
            [
                "wget",
                "-q",
                "-O",
                dest,
                f"--timeout={int(timeout)}",
                f"--user-agent={USER_AGENT}",
                url,
            ],
            check=True,
            timeout=timeout + 10,
        )
        return Path(dest).read_text(encoding="utf-8")
    finally:
        try:
            os.unlink(dest)
        except OSError:
            pass


def fetch_json(url: str, timeout: float = 30.0, retries: int = 4) -> dict[str, Any]:
    last_err: Exception | None = None
    raw = ""
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            last_err = exc
            # HiNetCDN sometimes answers 307 with an HTML "security" page and
            # no Location — urllib cannot follow that. wget often still gets
            # the JSON, so fall through to the wget path below.
            if exc.code == 307:
                try:
                    raw = _fetch_json_via_wget(url, timeout=timeout)
                    break
                except Exception as wget_exc:  # noqa: BLE001 - surface as last_err
                    last_err = wget_exc
                    if attempt + 1 < retries:
                        time.sleep(3.0 * (attempt + 1))
                        continue
                    raise RuntimeError(f"HTTP 307 for {url} (wget fallback failed: {wget_exc})") from wget_exc
            if exc.code in {429, 500, 502, 503, 504, 520, 522, 524} and attempt + 1 < retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, IncompleteRead, TimeoutError, OSError) as exc:
            last_err = exc
            if attempt + 1 < retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise RuntimeError(f"request failed for {url}: {exc}") from exc
    else:
        raise RuntimeError(f"request failed for {url}: {last_err}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"non-JSON response from {url}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"unexpected JSON type from {url}")
    return payload


def find_table(tables: list[dict[str, Any]], *needles: str) -> dict[str, Any]:
    """Match tables by title substring. Never use tables[i] ordinal."""
    for table in tables:
        title = str(table.get("title") or "")
        if all(needle in title for needle in needles):
            return table
    joined = ", ".join(repr(t.get("title")) for t in tables)
    raise KeyError(f"no table matching {needles!r}; titles={joined}")


def _row_map(fields: list[str], row: list[Any]) -> dict[str, Any]:
    return {fields[i]: row[i] if i < len(row) else None for i in range(len(fields))}


def parse_twse_payload(payload: dict[str, Any], session: date | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    stat = str(payload.get("stat") or "")
    if stat.upper() != "OK":
        return empty_bars(), empty_index()
    tables = payload.get("tables") or []
    if not tables:
        return empty_bars(), empty_index()

    if session is None:
        if payload.get("date"):
            session = parse_yyyymmdd(str(payload["date"]))
        else:
            raise ValueError("TWSE payload missing date")

    stock_table = find_table(tables, "每日收盤行情")
    fields = list(stock_table.get("fields") or [])
    rows: list[dict[str, Any]] = []
    for raw in stock_table.get("data") or []:
        item = _row_map(fields, raw)
        symbol = str(item.get("證券代號") or "").strip()
        if not is_listed_common(symbol):
            continue
        rows.append(
            {
                "date": session,
                "market": "TWSE",
                "symbol": symbol,
                "name": str(item.get("證券名稱") or "").strip(),
                "open": parse_num(item.get("開盤價")),
                "high": parse_num(item.get("最高價")),
                "low": parse_num(item.get("最低價")),
                "close": parse_num(item.get("收盤價")),
                "volume": parse_num(item.get("成交股數")),
                "trading_value": parse_num(item.get("成交金額")),
            }
        )
    bars = pd.DataFrame(rows, columns=BARS_COLUMNS) if rows else empty_bars()

    index_table = find_table(tables, "價格指數", "臺灣證券交易所")
    idx_fields = list(index_table.get("fields") or [])
    taiex: list[dict[str, Any]] = []
    for raw in index_table.get("data") or []:
        item = _row_map(idx_fields, raw)
        name = str(item.get("指數") or "").strip()
        if name == "發行量加權股價指數":
            close = parse_num(item.get("收盤指數"))
            if close is not None:
                taiex.append({"date": session, "close": close})
            break
    index = pd.DataFrame(taiex, columns=INDEX_COLUMNS) if taiex else empty_index()
    return bars, index


def parse_tpex_payload(payload: dict[str, Any], session: date | None = None) -> pd.DataFrame:
    stat = str(payload.get("stat") or "").lower()
    if stat not in {"ok", "ok "}:
        return empty_bars()
    tables = payload.get("tables") or []
    if not tables:
        return empty_bars()

    quoted_date = payload.get("date")
    if quoted_date:
        quoted = parse_yyyymmdd(str(quoted_date))
        if session is not None and quoted != session:
            raise ValueError(
                f"TPEx payload date {quoted.isoformat()} != requested {session.isoformat()}"
            )
        session = quoted
    elif session is None:
        raise ValueError("TPEx payload missing date")

    try:
        stock_table = find_table(tables, "上櫃股票行情")
    except KeyError:
        return empty_bars()
    fields = list(stock_table.get("fields") or [])
    rows: list[dict[str, Any]] = []
    for raw in stock_table.get("data") or []:
        item = _row_map(fields, raw)
        symbol = str(item.get("代號") or "").strip()
        if not is_listed_common(symbol):
            continue
        rows.append(
            {
                "date": session,
                "market": "TPEx",
                "symbol": symbol,
                "name": str(item.get("名稱") or "").strip(),
                "open": parse_num(item.get("開盤")),
                "high": parse_num(item.get("最高")),
                "low": parse_num(item.get("最低")),
                "close": parse_num(item.get("收盤")),
                "volume": parse_num(item.get("成交股數")),
                "trading_value": parse_num(item.get("成交金額(元)")),
            }
        )
    return pd.DataFrame(rows, columns=BARS_COLUMNS) if rows else empty_bars()


def empty_bars() -> pd.DataFrame:
    return pd.DataFrame(columns=BARS_COLUMNS)


def empty_index() -> pd.DataFrame:
    return pd.DataFrame(columns=INDEX_COLUMNS)


def twse_url(session: date) -> str:
    return TWSE_MI_INDEX.format(yyyymmdd=session.strftime("%Y%m%d"))


def tpex_url(session: date) -> str:
    return TPEX_DAILY_QUOTES.format(
        yyyy=session.strftime("%Y"),
        mm=session.strftime("%m"),
        dd=session.strftime("%d"),
    )


def raw_paths(data_dir: Path, session: date) -> tuple[Path, Path]:
    ymd = session.strftime("%Y%m%d")
    twse = data_dir / "raw" / "twse" / f"{ymd}.json"
    tpex = data_dir / "raw" / "tpex" / f"{ymd}.json"
    return twse, tpex


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def twse_payload_usable(payload: dict[str, Any]) -> bool:
    try:
        bars, index = parse_twse_payload(payload)
    except (KeyError, ValueError, TypeError):
        return False
    return not bars.empty or not index.empty


def tpex_payload_usable(payload: dict[str, Any], session: date) -> bool:
    try:
        bars = parse_tpex_payload(payload, session=session)
    except (KeyError, ValueError, TypeError):
        return False
    return not bars.empty


def raw_file_usable(path: Path, market: str, session: date) -> bool:
    if not path.exists():
        return False
    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    if market == "twse":
        return twse_payload_usable(payload)
    return tpex_payload_usable(payload, session)


def last_complete_session(data_dir: Path) -> date | None:
    bars_path = data_dir / "normalized" / "bars.parquet"
    index_path = data_dir / "normalized" / "index.parquet"
    if not bars_path.exists() or not index_path.exists():
        return None
    bars, index = read_normalized(data_dir)
    if bars.empty or index.empty:
        return None
    twse = set(bars.loc[bars["market"] == "TWSE", "date"])
    tpex = set(bars.loc[bars["market"] == "TPEx", "date"])
    taiex = set(index["date"])
    sessions = twse & tpex & taiex
    return max(sessions) if sessions else None


def utc_mtime_date(path: Path) -> date | None:
    """File mtime as a UTC calendar date. Used to tell 'fetched before the
    session happened' from 'fetched after, official empty' without a
    holiday calendar (spec 011 DO-2)."""
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).date()


def fetched_before_session(path: Path, session: date) -> bool:
    mt = utc_mtime_date(path)
    return mt is not None and mt < session


def should_fetch(
    path: Path,
    *,
    market: str,
    session: date,
    last_complete: date | None,
    today: date,
    force: bool = False,
) -> bool:
    if force or not path.exists():
        return True
    if raw_file_usable(path, market, session):
        return False
    if last_complete is None:
        return True
    if session >= today or session > last_complete:
        return True
    # B2: an unusable file written before its session is a fetch failure,
    # not a holiday. Existence alone must not freeze it forever.
    return fetched_before_session(path, session)


def _twse_fetch_label(payload: dict[str, Any]) -> str:
    if twse_payload_usable(payload):
        return "ok"
    stat = str(payload.get("stat") or "")
    return f"empty:{stat}" if stat else "empty"


def _tpex_fetch_label(payload: dict[str, Any], session: date) -> str:
    quoted = payload.get("date")
    if quoted:
        try:
            if parse_yyyymmdd(str(quoted)) != session:
                return f"date-mismatch:{quoted}"
        except ValueError:
            return f"date-mismatch:{quoted}"
    if tpex_payload_usable(payload, session):
        return "ok"
    return "empty"


def cached_label(path: Path, market: str, session: date) -> str:
    if raw_file_usable(path, market, session):
        return "cached"
    if fetched_before_session(path, session):
        return "fetch-failed"
    return "holiday"


EMPTY_HOLIDAY = "官方休市"
EMPTY_FETCH_FAILED = "抓取失敗"
EMPTY_UNKNOWN = "未知：臨時停市或抓取失敗"
EMPTY_HOLIDAY_MTIME = "官方休市（依 mtime，該年度無官方表）"
# Verdicts that rest on a file's mtime rather than on the official calendar.
# One `cp -r` or one restore-from-backup and these go wrong silently — that is
# why 012 DO-3 counts them out loud.
MTIME_DERIVED = frozenset({EMPTY_FETCH_FAILED, EMPTY_HOLIDAY_MTIME})
MTIME_MARK = "← 依 mtime"
MAX_PREMATURE_RETRY = 3

# TWSE 市場開休市日期. Official, free, same origin as the EOD feeds (D13).
# The endpoint IGNORES every year parameter tried (yy / queryYear / year, in
# both western and ROC years, 2026-09-07): it always answers with the current
# year and names it in `queryYear`. So the cache is keyed by the year the
# PAYLOAD claims, never by the year we asked for, and past years cannot be
# fetched after the fact — the cache can only accumulate from now on. TPEx's
# tradingDate behaves the same way and returns HTML inside JSON.
TWSE_HOLIDAY_SCHEDULE = (
    "https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json"
)
# The table lists BOTH closures and the trading days around them
# (「農曆春節前最後交易日」,「農曆春節後開始交易日」,「國曆新年開始交易日」).
# A row is a trading day when its 名稱 says 交易日 without saying 無交易 —
# 「市場無交易，僅辦理結算交割作業」 is a closure and must stay one.
HOLIDAY_TRADING_MARK = "交易日"
HOLIDAY_NO_TRADE_MARK = "無交易"


@dataclass(frozen=True)
class HolidayCalendar:
    """Official closure dates, and which years we actually have a table for.

    A year we could not load is not an empty year — it is a year whose
    verdicts have to fall back to mtime, out loud (spec 012 DO-3).
    """

    closures: frozenset[date]
    years: frozenset[int]

    def covers(self, year: int) -> bool:
        return year in self.years

    @property
    def available(self) -> bool:
        return bool(self.years)


def calendar_path(data_dir: Path, year: int) -> Path:
    return data_dir / "raw" / "calendar" / f"{year}.json"


def parse_holiday_payload(payload: object) -> tuple[int | None, set[date]]:
    """(the year the payload claims, its closure dates). Rows that name a
    trading day are not closures; see HOLIDAY_TRADING_MARK."""
    if not isinstance(payload, dict):
        return None, set()
    year = payload.get("queryYear")
    try:
        year = int(year) if year is not None else None
    except (TypeError, ValueError):
        year = None
    closures: set[date] = set()
    for row in payload.get("data") or []:
        if not isinstance(row, (list, tuple)) or not row:
            continue
        name = str(row[1]) if len(row) > 1 else ""
        if HOLIDAY_TRADING_MARK in name and HOLIDAY_NO_TRADE_MARK not in name:
            continue
        try:
            closures.add(date.fromisoformat(str(row[0]).strip()))
        except ValueError:
            continue
    return year, closures


def load_holiday_calendar(
    data_dir: Path,
    years: Iterable[int],
    *,
    fetch: bool = True,
    today: date | None = None,
) -> HolidayCalendar:
    """Cached official closures for ``years``. Fetches at most one payload per
    call, and only when the current year's cache file is absent — the endpoint
    has one year to give, so asking twice buys nothing."""
    wanted = sorted(set(years))
    closures: set[date] = set()
    covered: set[int] = set()
    for year in wanted:
        path = calendar_path(data_dir, year)
        if not path.exists():
            continue
        try:
            claimed, dates = parse_holiday_payload(load_json(path))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if claimed != year:
            continue
        closures |= dates
        covered.add(year)
    current = (today or date.today()).year
    if fetch and current in wanted and current not in covered:
        try:
            payload = fetch_json(TWSE_HOLIDAY_SCHEDULE)
            claimed, dates = parse_holiday_payload(payload)
        except Exception:  # noqa: BLE001 - offline / format change falls back
            claimed, dates = None, set()
        if claimed is not None:
            save_json(calendar_path(data_dir, claimed), payload)
            if claimed in wanted:
                closures |= dates
                covered.add(claimed)
    return HolidayCalendar(frozenset(closures), frozenset(covered))


def empty_session_verdicts(
    data_dir: Path,
    calendar: HolidayCalendar | None = None,
) -> list[tuple[date, str]]:
    """Weekday raw dates where neither market is usable.

    In order (spec 012 DO-3):

    1. on the official closure table  → 官方休市, reproducible, no mtime
    2. weekend                        → not a session at all; not listed here
    3. not on the table, no data      → 未知：臨時停市或抓取失敗. The typhoon
       closures the table never carries land here, and so do fetch failures.
       mtime is only a clue in this branch, and it is marked as one:
       抓取失敗 means a file's UTC mtime date is before its session (we asked
       before the day happened).

    A year with no official table at all falls back to the 011 mtime verdict,
    labelled 官方休市（依 mtime）— never silently.
    """
    sessions = [d for d in iter_raw_dates(data_dir) if d.weekday() < 5]
    if calendar is None:
        calendar = load_holiday_calendar(data_dir, {d.year for d in sessions})
    rows: list[tuple[date, str]] = []
    for session in sessions:
        twse_path, tpex_path = raw_paths(data_dir, session)
        twse_ok = raw_file_usable(twse_path, "twse", session)
        tpex_ok = raw_file_usable(tpex_path, "tpex", session)
        if twse_ok or tpex_ok:
            continue
        if session in calendar.closures:
            rows.append((session, EMPTY_HOLIDAY))
            continue
        premature = fetched_before_session(twse_path, session) or fetched_before_session(
            tpex_path, session
        )
        if premature:
            rows.append((session, EMPTY_FETCH_FAILED))
        elif calendar.covers(session.year):
            rows.append((session, EMPTY_UNKNOWN))
        else:
            rows.append((session, EMPTY_HOLIDAY_MTIME))
    return rows


def mtime_derived_sessions(rows: list[tuple[date, str]]) -> list[date]:
    """The dates whose verdict rests on a file mtime — the number DO-3 exists
    to shrink."""
    return [d for d, verdict in rows if verdict in MTIME_DERIVED]


def format_empty_session_verdicts(
    rows: list[tuple[date, str]],
    calendar: HolidayCalendar | None = None,
) -> str:
    lines = [f"empty sessions: {len(rows)}"]
    for session, verdict in rows:
        mark = f"  {MTIME_MARK}" if verdict in MTIME_DERIVED else ""
        lines.append(f"  {session.isoformat()}  {verdict}{mark}")
    mtime_dates = mtime_derived_sessions(rows)
    lines.append(
        f"靠 mtime 才判得出來的日期共 {len(mtime_dates)} 天"
        + ("：" + " ".join(d.isoformat() for d in mtime_dates) if mtime_dates else "")
    )
    if calendar is not None:
        uncovered = sorted({d.year for d, _ in rows} - set(calendar.years))
        if uncovered:
            lines.append(
                "本次判定未使用官方休市表的年份："
                + "、".join(str(y) for y in uncovered)
                + "（TWSE 端點只提供當年度；這些日期退回 011 的 mtime 行為）"
            )
        if not calendar.available:
            lines.append("本次判定未使用官方休市表：一年都沒讀到，全部退回 mtime 行為")
    return "\n".join(lines)


def premature_empty_sessions(
    data_dir: Path,
    calendar: HolidayCalendar | None = None,
) -> list[date]:
    return [
        d
        for d, verdict in empty_session_verdicts(data_dir, calendar)
        if verdict == EMPTY_FETCH_FAILED
    ]


def last_raw_attempt(data_dir: Path) -> dict[str, Any] | None:
    dates = iter_raw_dates(data_dir)
    if not dates:
        return None
    session = dates[-1]
    twse_path, tpex_path = raw_paths(data_dir, session)
    twse_ok = raw_file_usable(twse_path, "twse", session)
    tpex_ok = raw_file_usable(tpex_path, "tpex", session)
    return {
        "date": session,
        "twse": "ok" if twse_ok else "empty",
        "tpex": "ok" if tpex_ok else "empty",
        "usable": twse_ok and tpex_ok,
    }


def download_session(
    session: date,
    data_dir: Path,
    *,
    force: bool = False,
    last_complete: date | None = None,
    today: date | None = None,
) -> dict[str, str]:
    today = today or date.today()
    twse_path, tpex_path = raw_paths(data_dir, session)
    status = {"date": session.isoformat(), "twse": "skip", "tpex": "skip"}

    if should_fetch(
        twse_path,
        market="twse",
        session=session,
        last_complete=last_complete,
        today=today,
        force=force,
    ):
        payload = fetch_json(twse_url(session))
        save_json(twse_path, payload)
        status["twse"] = _twse_fetch_label(payload)
        time.sleep(TWSE_SLEEP_SEC)
    else:
        status["twse"] = cached_label(twse_path, "twse", session)

    if should_fetch(
        tpex_path,
        market="tpex",
        session=session,
        last_complete=last_complete,
        today=today,
        force=force,
    ):
        payload = fetch_json(tpex_url(session))
        save_json(tpex_path, payload)
        status["tpex"] = _tpex_fetch_label(payload, session)
    else:
        status["tpex"] = cached_label(tpex_path, "tpex", session)
    return status


def download_range(
    start: date,
    end: date,
    data_dir: Path,
    *,
    force: bool = False,
    today: date | None = None,
) -> pd.DataFrame:
    today = today or date.today()
    last_complete = last_complete_session(data_dir)
    rows = []
    for session in daterange(start, end):
        if session.weekday() >= 5:
            continue
        info = download_session(
            session,
            data_dir,
            force=force,
            last_complete=last_complete,
            today=today,
        )
        rows.append(info)
        print(
            f"{info['date']}  twse={info['twse']}  tpex={info['tpex']}",
            flush=True,
        )
    return pd.DataFrame(rows)


def load_raw_session(session: date, data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    twse_path, tpex_path = raw_paths(data_dir, session)
    bars = empty_bars()
    index = empty_index()
    if twse_path.exists():
        twse_bars, index = parse_twse_payload(load_json(twse_path), session)
        bars = pd.concat([bars, twse_bars], ignore_index=True)
    if tpex_path.exists():
        tpex_bars = parse_tpex_payload(load_json(tpex_path), session)
        bars = pd.concat([bars, tpex_bars], ignore_index=True)
    return bars, index


def iter_raw_dates(data_dir: Path) -> list[date]:
    twse_dir = data_dir / "raw" / "twse"
    tpex_dir = data_dir / "raw" / "tpex"
    names = set()
    if twse_dir.exists():
        names.update(p.stem for p in twse_dir.glob("*.json"))
    if tpex_dir.exists():
        names.update(p.stem for p in tpex_dir.glob("*.json"))
    return sorted(parse_yyyymmdd(name) for name in names)


def normalize_all(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    bar_frames: list[pd.DataFrame] = []
    index_frames: list[pd.DataFrame] = []
    for session in iter_raw_dates(data_dir):
        bars, index = load_raw_session(session, data_dir)
        if not bars.empty:
            bar_frames.append(bars)
        if not index.empty:
            index_frames.append(index)
    bars = (
        pd.concat(bar_frames, ignore_index=True)
        if bar_frames
        else empty_bars()
    )
    index = (
        pd.concat(index_frames, ignore_index=True)
        if index_frames
        else empty_index()
    )
    if not bars.empty:
        bars["symbol"] = bars["symbol"].astype(str)
        bars = bars.sort_values(["date", "market", "symbol"]).reset_index(drop=True)
    if not index.empty:
        index = index.sort_values("date").reset_index(drop=True)
    return bars, index


def write_normalized(data_dir: Path, bars: pd.DataFrame, index: pd.DataFrame) -> None:
    out = data_dir / "normalized"
    out.mkdir(parents=True, exist_ok=True)
    bars.to_parquet(out / "bars.parquet", index=False)
    index.to_parquet(out / "index.parquet", index=False)


def read_normalized(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    bars_path = data_dir / "normalized" / "bars.parquet"
    index_path = data_dir / "normalized" / "index.parquet"
    if not bars_path.exists() or not index_path.exists():
        raise FileNotFoundError("normalized parquet missing; run validate first")
    bars = pd.read_parquet(bars_path)
    index = pd.read_parquet(index_path)
    bars["date"] = pd.to_datetime(bars["date"]).dt.date
    index["date"] = pd.to_datetime(index["date"]).dt.date
    bars["symbol"] = bars["symbol"].astype(str)
    return bars, index


def validate_normalized(bars: pd.DataFrame, index: pd.DataFrame) -> list[str]:
    """Return human-readable issues. Failures must be visible; do not drop rows."""
    issues: list[str] = []
    if bars.empty:
        issues.append("bars is empty")
        return issues
    dup = bars.duplicated(subset=["date", "symbol"], keep=False)
    if dup.any():
        issues.append(f"duplicate (date, symbol) rows: {int(dup.sum())}")
    bad_ohlc = bars[
        bars[["open", "high", "low", "close"]].notna().all(axis=1)
        & (
            (bars["high"] < bars["low"])
            | (bars["high"] < bars["close"])
            | (bars["low"] > bars["close"])
        )
    ]
    if not bad_ohlc.empty:
        issues.append(f"illegal OHLC rows: {len(bad_ohlc)}")
    neg = bars[(bars["volume"] < 0) | (bars["trading_value"] < 0)]
    if not neg.empty:
        issues.append(f"negative volume/value rows: {len(neg)}")

    dates = sorted(set(bars["date"]))
    twse_dates = set(bars.loc[bars["market"] == "TWSE", "date"])
    tpex_dates = set(bars.loc[bars["market"] == "TPEx", "date"])
    index_dates = set(index["date"]) if not index.empty else set()
    missing_taiex = [d for d in dates if d not in index_dates]
    if missing_taiex:
        issues.append(f"missing TAIEX on {len(missing_taiex)} session(s)")
    only_twse = sorted(twse_dates - tpex_dates)
    only_tpex = sorted(tpex_dates - twse_dates)
    if only_twse:
        issues.append(f"TWSE without TPEx: {len(only_twse)} session(s)")
    if only_tpex:
        issues.append(f"TPEx without TWSE: {len(only_tpex)} session(s)")
    return issues


def coverage_report(bars: pd.DataFrame, index: pd.DataFrame) -> str:
    if bars.empty:
        return "no bars"
    dates = sorted(set(bars["date"]))
    lines = [
        f"sessions: {len(dates)}  {dates[0]} → {dates[-1]}",
        f"TWSE rows: {int((bars['market']=='TWSE').sum())}",
        f"TPEx rows: {int((bars['market']=='TPEx').sum())}",
        f"TAIEX sessions: {0 if index.empty else index['date'].nunique()}",
    ]
    return "\n".join(lines)
