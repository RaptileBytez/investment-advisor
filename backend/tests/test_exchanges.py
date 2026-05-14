"""Ticker-suffix → exchange mapping is the foundation for currency and
benchmark selection — every region must resolve correctly."""

from __future__ import annotations

import pytest

from app.data.exchanges import US_EXCHANGE, info_for


@pytest.mark.parametrize(
    ("ticker", "region", "currency", "benchmark"),
    [
        ("AAPL",   "US", "USD", "^GSPC"),
        ("MSFT",   "US", "USD", "^GSPC"),
        ("SAP.DE", "DE", "EUR", "^GDAXI"),
        ("BMW.DE", "DE", "EUR", "^GDAXI"),
        ("AIR.PA", "FR", "EUR", "^FCHI"),
        ("ASML.AS","NL", "EUR", "^AEX"),
        ("BP.L",   "GB", "GBP", "^FTSE"),
        ("NESN.SW","CH", "CHF", "^SSMI"),
        ("7203.T", "JP", "JPY", "^N225"),
        ("BHP.AX", "AU", "AUD", "^AXJO"),
    ],
)
def test_info_for_returns_expected_mapping(ticker, region, currency, benchmark):
    info = info_for(ticker)
    assert info.region == region
    assert info.currency == currency
    assert info.benchmark == benchmark


def test_unknown_suffix_falls_back_to_us():
    # An odd-looking suffix that doesn't match any registered exchange.
    assert info_for("FOO.XYZ") == US_EXCHANGE


def test_case_insensitive():
    assert info_for("sap.de").region == "DE"
    assert info_for("SAP.DE").region == "DE"
