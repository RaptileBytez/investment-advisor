"""Region → benchmark / risk-free rate mapping."""

from __future__ import annotations

import pytest

from app.risk.benchmarks import (
    DEFAULT_CONFIG,
    get_config_for_region,
    get_config_for_ticker,
    get_risk_free_rate,
)


@pytest.mark.parametrize(
    ("ticker", "expected_region", "expected_benchmark"),
    [
        ("AAPL",   "US", "^GSPC"),
        ("SAP.DE", "DE", "^GDAXI"),
        ("AIR.PA", "FR", "^FCHI"),
        ("BP.L",   "GB", "^FTSE"),
        ("NESN.SW","CH", "^SSMI"),
        ("7203.T", "JP", "^N225"),
    ],
)
def test_config_for_ticker(ticker, expected_region, expected_benchmark):
    cfg = get_config_for_ticker(ticker)
    assert cfg.region == expected_region
    assert cfg.benchmark_ticker == expected_benchmark


def test_unknown_region_falls_back_to_default():
    assert get_config_for_region("ZZ") == DEFAULT_CONFIG


class _FakeProvider:
    """Stand-in for tests that don't need a real DataProvider."""

    def __init__(self, mapping: dict[str, float]):
        self._mapping = mapping

    def get_quote(self, ticker):  # noqa: ANN001
        from datetime import UTC, datetime

        from app.data.provider import ProviderError, Quote

        if ticker not in self._mapping:
            raise ProviderError(f"no quote for {ticker}")
        return Quote(
            ticker=ticker,
            price=self._mapping[ticker],
            currency="USD",
            timestamp=datetime.now(UTC),
        )

    # The other methods are unused here.
    def search(self, *args, **kwargs): ...     # noqa: ANN001
    def get_history(self, *args, **kwargs): ...  # noqa: ANN001
    def get_fundamentals(self, *args, **kwargs): ...  # noqa: ANN001


def test_risk_free_rate_uses_live_when_available():
    # ^IRX is quoted in percent. A 5.25% T-bill should resolve to 0.0525.
    provider = _FakeProvider({"^IRX": 5.25})
    assert get_risk_free_rate("US", provider) == pytest.approx(0.0525)


def test_risk_free_rate_falls_back_when_provider_errors():
    provider = _FakeProvider({})  # no quotes available
    rate = get_risk_free_rate("US", provider)
    assert rate == DEFAULT_CONFIG.risk_free_rate_fallback


def test_risk_free_rate_uses_static_for_regions_without_ticker():
    provider = _FakeProvider({})
    rate = get_risk_free_rate("DE", provider)
    assert rate == get_config_for_region("DE").risk_free_rate_fallback
