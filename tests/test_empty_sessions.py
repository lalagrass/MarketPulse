"""spec 011 DO-2 / 012 DO-3: official closure table first, mtime last."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from marketpulse.cli import app
from marketpulse.data import (
    EMPTY_FETCH_FAILED,
    EMPTY_HOLIDAY,
    EMPTY_HOLIDAY_MTIME,
    EMPTY_UNKNOWN,
    MAX_PREMATURE_RETRY,
    HolidayCalendar,
    calendar_path,
    empty_session_verdicts,
    format_empty_session_verdicts,
    load_holiday_calendar,
    mtime_derived_sessions,
    parse_holiday_payload,
    premature_empty_sessions,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TWSE_EMPTY = {"stat": "很抱歉，沒有符合條件的資料!", "type": "ALLBUT0999"}
TPEX_EMPTY = {
    "stat": "ok",
    "date": "2026/09/01",
    "tables": [{"title": "上櫃股票每日收盤行情", "fields": ["代號"], "data": []}],
}


# Trimmed from the real 2026 response (data/raw/calendar/2026.json): two
# closures, one settlement-only closure, and the two rows that name TRADING
# days and must not be read as closures.
OFFICIAL_2026 = {
    "stat": "ok",
    "title": "115 年市場開休市日期",
    "queryYear": 2026,
    "total": 5,
    "fields": ["日期", "名稱", "說明"],
    "data": [
        ["2026-01-01", "中華民國開國紀念日", "依規定放假1日。"],
        ["2026-01-02", "國曆新年開始交易日", "國曆新年開始交易。"],
        ["2026-02-11", "農曆春節前最後交易日", "農曆春節前最後交易。"],
        ["2026-02-12", "市場無交易，僅辦理結算交割作業", ""],
        ["2026-06-19", "端午節", "依規定放假1日。"],
    ],
}


def _calendar(payload: dict = OFFICIAL_2026) -> HolidayCalendar:
    year, closures = parse_holiday_payload(payload)
    return HolidayCalendar(frozenset(closures), frozenset({year}))


def _write_calendar(data_dir: Path, payload: dict = OFFICIAL_2026) -> Path:
    path = calendar_path(data_dir, int(payload["queryYear"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _stamp(path: Path, when: datetime) -> None:
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def _write_pair(
    data_dir: Path,
    session: date,
    *,
    mtime: datetime,
    tpex_date: str | None = None,
) -> None:
    ymd = session.strftime("%Y%m%d")
    twse = data_dir / "raw" / "twse" / f"{ymd}.json"
    tpex = data_dir / "raw" / "tpex" / f"{ymd}.json"
    twse.parent.mkdir(parents=True, exist_ok=True)
    tpex.parent.mkdir(parents=True, exist_ok=True)
    twse.write_text(json.dumps(TWSE_EMPTY), encoding="utf-8")
    payload = dict(TPEX_EMPTY)
    payload["date"] = tpex_date or f"{session:%Y/%m/%d}"
    tpex.write_text(json.dumps(payload), encoding="utf-8")
    _stamp(twse, mtime)
    _stamp(tpex, mtime)


def test_premature_mtime_is_fetch_failed(tmp_path: Path) -> None:
    session = date(2026, 9, 1)
    _write_pair(
        tmp_path,
        session,
        mtime=datetime(2026, 8, 31, 16, 30, tzinfo=timezone.utc),
    )
    cal = _calendar()
    assert empty_session_verdicts(tmp_path, cal) == [(session, EMPTY_FETCH_FAILED)]
    assert premature_empty_sessions(tmp_path, cal) == [session]


def test_not_on_the_table_and_not_premature_is_unknown(tmp_path: Path) -> None:
    """012 DO-3: 2026-07-10 (typhoon) is not on the official table, and the
    table has no 臨時停市 rows at all — so it is a stated unknown, not a
    silent holiday. 011 called this 官方休市 on mtime alone."""
    session = date(2026, 7, 10)
    _write_pair(
        tmp_path,
        session,
        mtime=datetime(2026, 8, 31, 16, 29, tzinfo=timezone.utc),
    )
    cal = _calendar()
    assert empty_session_verdicts(tmp_path, cal) == [(session, EMPTY_UNKNOWN)]
    assert premature_empty_sessions(tmp_path, cal) == []
    assert mtime_derived_sessions(empty_session_verdicts(tmp_path, cal)) == []


def test_on_the_table_is_official_holiday_without_mtime(tmp_path: Path) -> None:
    """012 DO-3 step 1: a table hit is 官方休市 whatever the mtime says."""
    session = date(2026, 6, 19)
    _write_pair(
        tmp_path,
        session,
        # mtime that 011 would have read as a fetch failure.
        mtime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    cal = _calendar()
    assert empty_session_verdicts(tmp_path, cal) == [(session, EMPTY_HOLIDAY)]
    assert mtime_derived_sessions(empty_session_verdicts(tmp_path, cal)) == []


def test_settlement_only_row_is_a_closure_and_trading_rows_are_not() -> None:
    """The official table carries the trading days around a closure too:
    「農曆春節前最後交易日」 trades, 「市場無交易，僅辦理結算交割作業」 does not."""
    year, closures = parse_holiday_payload(OFFICIAL_2026)
    assert year == 2026
    assert closures == {date(2026, 1, 1), date(2026, 2, 12), date(2026, 6, 19)}


def test_a_year_with_no_table_falls_back_to_mtime_out_loud(tmp_path: Path) -> None:
    """012 DO-3 fallback: the TWSE endpoint serves the current year only, so
    older years have no table. Those dates keep the 011 mtime verdict and are
    labelled as such — never a silent 官方休市."""
    session = date(2025, 5, 1)
    _write_pair(
        tmp_path,
        session,
        mtime=datetime(2025, 6, 1, 0, 0, tzinfo=timezone.utc),
    )
    cal = _calendar()
    rows = empty_session_verdicts(tmp_path, cal)
    assert rows == [(session, EMPTY_HOLIDAY_MTIME)]
    assert mtime_derived_sessions(rows) == [session]
    text = format_empty_session_verdicts(rows, cal)
    assert "靠 mtime 才判得出來的日期共 1 天" in text
    assert "本次判定未使用官方休市表的年份：2025" in text


def test_calendar_fetch_failure_falls_back_and_says_so(tmp_path: Path, monkeypatch) -> None:
    """Offline or a format change: back to 011 behaviour, and it says it."""
    import marketpulse.data as data_mod

    def boom(url: str, *args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(data_mod, "fetch_json", boom)
    session = date(2026, 7, 10)
    _write_pair(
        tmp_path,
        session,
        mtime=datetime(2026, 8, 31, 16, 29, tzinfo=timezone.utc),
    )
    cal = load_holiday_calendar(tmp_path, {2026}, today=date(2026, 9, 7))
    assert cal.available is False
    rows = empty_session_verdicts(tmp_path, cal)
    assert rows == [(session, EMPTY_HOLIDAY_MTIME)]
    text = format_empty_session_verdicts(rows, cal)
    assert "本次判定未使用官方休市表" in text


def test_cached_calendar_is_not_refetched(tmp_path: Path, monkeypatch) -> None:
    """快取檔存在時不重抓 — refresh asks the endpoint at most once a year."""
    import marketpulse.data as data_mod

    calls = []

    def counted(url: str, *args, **kwargs):
        calls.append(url)
        return OFFICIAL_2026

    monkeypatch.setattr(data_mod, "fetch_json", counted)
    _write_calendar(tmp_path)
    cal = load_holiday_calendar(tmp_path, {2026}, today=date(2026, 9, 7))
    assert calls == []
    assert cal.covers(2026)
    assert date(2026, 6, 19) in cal.closures


def test_fetch_is_cached_under_the_year_the_payload_claims(tmp_path: Path, monkeypatch) -> None:
    """The endpoint ignores every year parameter and answers with the current
    year. Key the cache by `queryYear`, never by the year we asked for."""
    import marketpulse.data as data_mod

    monkeypatch.setattr(data_mod, "fetch_json", lambda url, *a, **k: OFFICIAL_2026)
    cal = load_holiday_calendar(tmp_path, {2025, 2026}, today=date(2026, 9, 7))
    assert calendar_path(tmp_path, 2026).exists()
    assert not calendar_path(tmp_path, 2025).exists()
    assert cal.years == frozenset({2026})
    assert cal.covers(2026) and not cal.covers(2025)


def test_weekend_files_are_not_listed(tmp_path: Path) -> None:
    saturday = date(2026, 9, 5)
    _write_pair(
        tmp_path,
        saturday,
        mtime=datetime(2026, 9, 6, 0, 0, tzinfo=timezone.utc),
    )
    assert empty_session_verdicts(tmp_path, _calendar()) == []


def test_usable_session_is_not_listed(tmp_path: Path) -> None:
    from tests.conftest import FIXTURES

    session = date(2026, 8, 28)
    ymd = session.strftime("%Y%m%d")
    twse = tmp_path / "raw" / "twse" / f"{ymd}.json"
    tpex = tmp_path / "raw" / "tpex" / f"{ymd}.json"
    twse.parent.mkdir(parents=True, exist_ok=True)
    tpex.parent.mkdir(parents=True, exist_ok=True)
    twse.write_text((FIXTURES / "twse_mi_index.json").read_text(encoding="utf-8"))
    tpex.write_text((FIXTURES / "tpex_daily_quotes.json").read_text(encoding="utf-8"))
    assert empty_session_verdicts(tmp_path, _calendar()) == []


def test_format_prints_each_date_and_verdict(tmp_path: Path) -> None:
    _write_pair(
        tmp_path,
        date(2026, 7, 10),
        mtime=datetime(2026, 8, 31, 16, 29, tzinfo=timezone.utc),
    )
    _write_pair(
        tmp_path,
        date(2026, 9, 1),
        mtime=datetime(2026, 8, 31, 16, 30, tzinfo=timezone.utc),
    )
    cal = _calendar()
    text = format_empty_session_verdicts(empty_session_verdicts(tmp_path, cal), cal)
    assert text.startswith("empty sessions: 2")
    assert f"2026-07-10  {EMPTY_UNKNOWN}" in text
    assert "2026-09-01  抓取失敗" in text
    assert "靠 mtime 才判得出來的日期共 1 天：2026-09-01" in text


def test_retry_cap_is_three() -> None:
    assert MAX_PREMATURE_RETRY == 3


def test_validate_prints_holiday_and_fetch_failed(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    _write_pair(
        data_dir,
        date(2026, 7, 10),
        mtime=datetime(2026, 8, 31, 16, 29, tzinfo=timezone.utc),
    )
    _write_pair(
        data_dir,
        date(2026, 9, 1),
        mtime=datetime(2026, 8, 31, 16, 30, tzinfo=timezone.utc),
    )
    _write_calendar(data_dir)  # cached: validate must not reach the network
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["validate", "--data-dir", str(data_dir)])
    assert f"2026-07-10  {EMPTY_UNKNOWN}" in result.output
    assert "2026-09-01  抓取失敗" in result.output
    assert "empty sessions: 2" in result.output
    assert "靠 mtime 才判得出來的日期共 1 天" in result.output


@pytest.mark.skipif(
    not (REPO_ROOT / "data" / "raw" / "twse" / "20260710.json").exists(),
    reason="live 2026-07-10 raw file not on this machine",
)
def test_live_2026_07_10_is_unknown_not_a_holiday() -> None:
    """011 B4 called the typhoon Bavi close 官方休市 on mtime alone. 012 DO-3:
    the official table has no 臨時停市 rows, so this date must land in the
    stated-unknown branch. Uses the cached table only (no network)."""
    data_dir = REPO_ROOT / "data"
    cal = load_holiday_calendar(data_dir, {2026}, fetch=False)
    if not cal.covers(2026):
        pytest.skip("official 2026 calendar not cached on this machine")
    found = dict(empty_session_verdicts(data_dir, cal))
    assert found[date(2026, 7, 10)] == EMPTY_UNKNOWN
    assert found[date(2026, 6, 19)] == EMPTY_HOLIDAY
