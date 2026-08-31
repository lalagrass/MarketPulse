"""Official TWSE / TPEx dated EOD adapters, normalize, and local store."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
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


def fetch_json(url: str, timeout: float = 30.0) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed for {url}: {exc}") from exc
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


def download_session(session: date, data_dir: Path, *, force: bool = False) -> dict[str, str]:
    twse_path, tpex_path = raw_paths(data_dir, session)
    status = {"date": session.isoformat(), "twse": "skip", "tpex": "skip"}

    if force or not twse_path.exists():
        payload = fetch_json(twse_url(session))
        save_json(twse_path, payload)
        stat = str(payload.get("stat") or "")
        status["twse"] = "ok" if stat.upper() == "OK" else f"empty:{stat}"
        time.sleep(TWSE_SLEEP_SEC)
    else:
        status["twse"] = "cached"

    if force or not tpex_path.exists():
        payload = fetch_json(tpex_url(session))
        save_json(tpex_path, payload)
        n = 0
        tables = payload.get("tables") or []
        if tables:
            n = len(tables[0].get("data") or [])
        quoted = payload.get("date")
        if quoted and parse_yyyymmdd(str(quoted)) != session:
            status["tpex"] = f"date-mismatch:{quoted}"
        elif n == 0:
            status["tpex"] = "empty"
        else:
            status["tpex"] = "ok"
    else:
        status["tpex"] = "cached"
    return status


def download_range(start: date, end: date, data_dir: Path, *, force: bool = False) -> pd.DataFrame:
    rows = []
    for session in daterange(start, end):
        if session.weekday() >= 5:
            continue
        info = download_session(session, data_dir, force=force)
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
