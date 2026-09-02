from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from marketpulse.cli import _write_snapshot_meta, format_ops_status
from marketpulse.data import (
    last_complete_session,
    raw_file_usable,
    should_fetch,
    tpex_payload_usable,
    twse_payload_usable,
)
from marketpulse.product import LATEST_CHART_NAME, default_chart_path
from tests.conftest import FIXTURES, make_bars, make_index, session_dates


def _twse_ok() -> dict:
    return json.loads((FIXTURES / "twse_mi_index.json").read_text(encoding="utf-8"))


def _tpex_ok() -> dict:
    return json.loads((FIXTURES / "tpex_daily_quotes.json").read_text(encoding="utf-8"))


def test_twse_fixture_usable() -> None:
    assert twse_payload_usable(_twse_ok())


def test_twse_empty_stat_not_usable() -> None:
    assert not twse_payload_usable({"stat": "很抱歉，沒有符合條件的資料!", "type": "ALLBUT0999"})


def test_tpex_fixture_usable() -> None:
    assert tpex_payload_usable(_tpex_ok(), date(2026, 8, 28))


def test_tpex_date_mismatch_not_usable() -> None:
    assert not tpex_payload_usable(_tpex_ok(), date(2026, 8, 27))


def test_tpex_zero_rows_not_usable() -> None:
    payload = {
        "stat": "ok",
        "date": "2026/09/01",
        "tables": [{"title": "上櫃股票每日收盤行情", "fields": ["代號"], "data": []}],
    }
    assert not tpex_payload_usable(payload, date(2026, 9, 1))


def test_raw_file_usable_roundtrip(tmp_path: Path) -> None:
    session = date(2026, 8, 28)
    twse = tmp_path / "twse.json"
    twse.write_text(json.dumps(_twse_ok()), encoding="utf-8")
    assert raw_file_usable(twse, "twse", session)
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"stat": "很抱歉，沒有符合條件的資料!"}), encoding="utf-8")
    assert not raw_file_usable(empty, "twse", session)


def test_should_fetch_usable_cached(tmp_path: Path) -> None:
    session = date(2026, 8, 28)
    path = tmp_path / "twse.json"
    path.write_text(json.dumps(_twse_ok()), encoding="utf-8")
    assert not should_fetch(
        path,
        market="twse",
        session=session,
        last_complete=date(2026, 8, 28),
        today=date(2026, 9, 3),
    )


def test_should_fetch_trailing_empty(tmp_path: Path) -> None:
    session = date(2026, 9, 3)
    path = tmp_path / "twse.json"
    path.write_text(json.dumps({"stat": "很抱歉，沒有符合條件的資料!"}), encoding="utf-8")
    assert should_fetch(
        path,
        market="twse",
        session=session,
        last_complete=date(2026, 9, 2),
        today=date(2026, 9, 3),
    )


def test_should_fetch_holiday_before_complete_kept(tmp_path: Path) -> None:
    session = date(2026, 9, 1)
    path = tmp_path / "twse.json"
    path.write_text(json.dumps({"stat": "很抱歉，沒有符合條件的資料!"}), encoding="utf-8")
    assert not should_fetch(
        path,
        market="twse",
        session=session,
        last_complete=date(2026, 9, 2),
        today=date(2026, 9, 3),
    )


def test_should_fetch_force_and_missing(tmp_path: Path) -> None:
    session = date(2026, 8, 28)
    missing = tmp_path / "nope.json"
    assert should_fetch(
        missing,
        market="twse",
        session=session,
        last_complete=date(2026, 8, 28),
        today=date(2026, 9, 3),
    )
    path = tmp_path / "twse.json"
    path.write_text(json.dumps(_twse_ok()), encoding="utf-8")
    assert should_fetch(
        path,
        market="twse",
        session=session,
        last_complete=date(2026, 8, 28),
        today=date(2026, 9, 3),
        force=True,
    )


def test_last_complete_session_from_normalized(tmp_path: Path) -> None:
    dates = session_dates(3, start=date(2026, 8, 31))
    bars = make_bars(
        dates,
        {"2330": [100.0, 101.0, 102.0], "3081": [10.0, 11.0, 12.0]},
        twse=("2330",),
        tpex=("3081",),
    )
    # Drop TPEx on the last day so complete sessions stop at the middle date.
    bars = bars[~((bars["date"] == dates[-1]) & (bars["market"] == "TPEx"))]
    index = make_index(dates, [1000.0, 1001.0, 1002.0])
    out = tmp_path / "normalized"
    out.mkdir()
    bars.to_parquet(out / "bars.parquet", index=False)
    index.to_parquet(out / "index.parquet", index=False)
    assert last_complete_session(tmp_path) == dates[1]
    assert last_complete_session(tmp_path / "missing") is None


def test_snapshot_meta_includes_as_of(tmp_path: Path) -> None:
    parquet = tmp_path / "theme_daily.parquet"
    parquet.write_bytes(b"")
    meta = _write_snapshot_meta(
        parquet,
        classification_version="test",
        rows=11,
        as_of=date(2026, 9, 2),
    )
    payload = json.loads(meta.read_text(encoding="utf-8"))
    assert payload["as_of"] == "2026-09-02"
    assert payload["rows"] == 11


def test_default_chart_path_latest_without_start(tmp_path: Path) -> None:
    assert default_chart_path(tmp_path, None, None) == tmp_path / LATEST_CHART_NAME
    assert default_chart_path(tmp_path, date(2026, 1, 2), None) is None
    explicit = tmp_path / "custom.png"
    assert default_chart_path(tmp_path, None, explicit) == explicit


def test_format_ops_status_trailing_empty(tmp_path: Path) -> None:
    raw_twse = tmp_path / "raw" / "twse"
    raw_tpex = tmp_path / "raw" / "tpex"
    raw_twse.mkdir(parents=True)
    raw_tpex.mkdir(parents=True)
    (raw_twse / "20260903.json").write_text(
        json.dumps({"stat": "很抱歉，沒有符合條件的資料!"}),
        encoding="utf-8",
    )
    (raw_tpex / "20260903.json").write_text(
        json.dumps({"stat": "ok", "date": "2026/09/03", "tables": []}),
        encoding="utf-8",
    )
    dates = session_dates(2, start=date(2026, 9, 1))
    bars = make_bars(
        dates,
        {"2330": [100.0, 101.0], "3081": [10.0, 11.0]},
        twse=("2330",),
        tpex=("3081",),
    )
    index = make_index(dates, [1000.0, 1001.0])
    out = tmp_path / "normalized"
    out.mkdir()
    bars.to_parquet(out / "bars.parquet", index=False)
    index.to_parquet(out / "index.parquet", index=False)
    snap = tmp_path / "snapshots"
    snap.mkdir()
    frame = pd.DataFrame({"date": [dates[-1]], "theme_id": ["alpha"], "rank": [1]})
    frame.to_parquet(snap / "theme_daily.parquet", index=False)
    text = format_ops_status(
        tmp_path,
        chart_path=tmp_path / "reports" / LATEST_CHART_NAME,
        effective=(date(2026, 7, 8), dates[-1]),
    )
    assert "raw last attempt: 2026-09-03  twse=empty  tpex=empty  (will retry)" in text
    assert f"bars/snapshot as_of: {dates[-1].isoformat()}" in text
    assert "rotation_latest.png" in text
