"""spec 011 DO-2: official holiday vs fetch failure on empty weekday files."""

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
    MAX_PREMATURE_RETRY,
    empty_session_verdicts,
    format_empty_session_verdicts,
    premature_empty_sessions,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TWSE_EMPTY = {"stat": "很抱歉，沒有符合條件的資料!", "type": "ALLBUT0999"}
TPEX_EMPTY = {
    "stat": "ok",
    "date": "2026/09/01",
    "tables": [{"title": "上櫃股票每日收盤行情", "fields": ["代號"], "data": []}],
}


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
    assert empty_session_verdicts(tmp_path) == [(session, EMPTY_FETCH_FAILED)]
    assert premature_empty_sessions(tmp_path) == [session]


def test_post_session_mtime_is_holiday(tmp_path: Path) -> None:
    session = date(2026, 7, 10)
    _write_pair(
        tmp_path,
        session,
        mtime=datetime(2026, 8, 31, 16, 29, tzinfo=timezone.utc),
    )
    assert empty_session_verdicts(tmp_path) == [(session, EMPTY_HOLIDAY)]
    assert premature_empty_sessions(tmp_path) == []


def test_weekend_files_are_not_listed(tmp_path: Path) -> None:
    saturday = date(2026, 9, 5)
    _write_pair(
        tmp_path,
        saturday,
        mtime=datetime(2026, 9, 6, 0, 0, tzinfo=timezone.utc),
    )
    assert empty_session_verdicts(tmp_path) == []


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
    assert empty_session_verdicts(tmp_path) == []


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
    text = format_empty_session_verdicts(empty_session_verdicts(tmp_path))
    assert text.startswith("empty sessions: 2")
    assert "2026-07-10  官方休市" in text
    assert "2026-09-01  抓取失敗" in text


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
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["validate", "--data-dir", str(data_dir)])
    assert "2026-07-10  官方休市" in result.output
    assert "2026-09-01  抓取失敗" in result.output
    assert "empty sessions: 2" in result.output


@pytest.mark.skipif(
    not (REPO_ROOT / "data" / "raw" / "twse" / "20260710.json").exists(),
    reason="live 2026-07-10 raw file not on this machine",
)
def test_live_2026_07_10_is_holiday() -> None:
    """B4: typhoon Bavi full-day close must be 官方休市."""
    found = dict(empty_session_verdicts(REPO_ROOT / "data"))
    assert found[date(2026, 7, 10)] == EMPTY_HOLIDAY
