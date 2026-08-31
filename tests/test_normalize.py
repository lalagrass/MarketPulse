from __future__ import annotations

import json
from datetime import date

import pandas as pd
import pytest

from marketpulse.data import (
    is_listed_common,
    parse_tpex_payload,
    parse_twse_payload,
    validate_normalized,
)


def test_common_stock_filter() -> None:
    assert is_listed_common("2330")
    assert is_listed_common("3081")
    assert not is_listed_common("0050")
    assert not is_listed_common("006201")
    assert not is_listed_common("2330A")
    assert not is_listed_common("9105")
    assert not is_listed_common("00631L")


def test_parse_twse_fixture(twse_fixture) -> None:
    payload = json.loads(twse_fixture.read_text(encoding="utf-8"))
    bars, index = parse_twse_payload(payload)
    assert set(bars["symbol"]) == {"2330", "1101"}
    assert "0050" not in set(bars["symbol"])
    assert "2330A" not in set(bars["symbol"])
    row = bars.set_index("symbol").loc["2330"]
    assert row["close"] == 2420.0
    assert row["trading_value"] == 36465015980.0
    assert row["market"] == "TWSE"
    assert list(index["close"]) == [46331.45]
    assert list(index["date"]) == [date(2026, 8, 28)]


def test_parse_tpex_fixture(tpex_fixture) -> None:
    payload = json.loads(tpex_fixture.read_text(encoding="utf-8"))
    bars = parse_tpex_payload(payload)
    assert set(bars["symbol"]) == {"3081", "8358"}
    assert bars.set_index("symbol").loc["3081", "close"] == 80.0
    assert bars.set_index("symbol").loc["8358", "trading_value"] == 26_000_000.0


def test_tpex_rejects_date_mismatch(tpex_fixture) -> None:
    payload = json.loads(tpex_fixture.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="date"):
        parse_tpex_payload(payload, session=date(2026, 8, 27))


def test_validate_duplicate_pk(twse_fixture) -> None:
    payload = json.loads(twse_fixture.read_text(encoding="utf-8"))
    bars, index = parse_twse_payload(payload)
    doubled = bars.copy()
    issues = validate_normalized(pd.concat([bars, doubled], ignore_index=True), index)
    assert any("duplicate" in item for item in issues)
