"""Strategy verdicts on synthetic price series + fundamentals.

We assert verdict direction (BUY / HOLD / SELL) on deterministic inputs.
Exact score thresholds are intentionally not over-asserted so that
re-tuning the weights doesn't churn the tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.data.provider import Fundamentals
from app.strategies import registry
from app.strategies.base import Verdict
from app.strategies.buy_hold import BuyHoldStrategy
from app.strategies.dca import DCAStrategy, simulate_dca
from app.strategies.momentum import MomentumStrategy, _rsi, _twelve_one_momentum
from app.strategies.value import ValueStrategy


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def rising_close(n: int = 500, *, start: float = 100.0, end: float = 200.0) -> pd.DataFrame:
    """A clean monotonically rising price series."""
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    closes = np.linspace(start, end, n)
    return _to_ohlcv(idx, closes)


def falling_close(n: int = 500, *, start: float = 200.0, end: float = 100.0) -> pd.DataFrame:
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    closes = np.linspace(start, end, n)
    return _to_ohlcv(idx, closes)


def noisy_close(n: int = 500, *, seed: int = 42, drift: float = 0.0005, vol: float = 0.03) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    returns = rng.normal(loc=drift, scale=vol, size=n)
    closes = 100.0 * np.cumprod(1 + returns)
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return _to_ohlcv(idx, closes)


def _to_ohlcv(idx: pd.DatetimeIndex, closes: np.ndarray) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open":   closes,
            "High":   closes,
            "Low":    closes,
            "Close":  closes,
            "Volume": np.ones_like(closes) * 1_000_000,
        },
        index=idx,
    )


# ──────────────────────────────────────────────────────────────
# Registry
# ──────────────────────────────────────────────────────────────
def test_registry_lists_all_four_strategies():
    assert set(registry.available()) == {"buy_hold", "dca", "value", "momentum"}


def test_registry_get_returns_instance():
    s = registry.get("buy_hold")
    assert isinstance(s, BuyHoldStrategy)


def test_registry_unknown_raises():
    with pytest.raises(ValueError):
        registry.get("not_a_strategy")


# ──────────────────────────────────────────────────────────────
# Buy & Hold
# ──────────────────────────────────────────────────────────────
def test_buy_hold_buys_steady_compounder():
    strat = BuyHoldStrategy()
    result = strat.score("STEADY", rising_close())
    assert result.verdict == Verdict.BUY
    assert result.score >= 0.65


def test_buy_hold_sells_declining_name():
    strat = BuyHoldStrategy()
    result = strat.score("DOWN", falling_close())
    assert result.verdict == Verdict.SELL


def test_buy_hold_rationale_non_empty():
    strat = BuyHoldStrategy()
    result = strat.score("STEADY", rising_close())
    assert len(result.rationale) > 20


def test_buy_hold_raises_on_short_history():
    strat = BuyHoldStrategy()
    with pytest.raises(ValueError):
        strat.score("SHORT", rising_close(n=30))


# ──────────────────────────────────────────────────────────────
# Momentum
# ──────────────────────────────────────────────────────────────
def test_momentum_buys_uptrend():
    strat = MomentumStrategy()
    result = strat.score("UP", rising_close())
    assert result.verdict == Verdict.BUY


def test_momentum_sells_downtrend():
    strat = MomentumStrategy()
    result = strat.score("DOWN", falling_close())
    assert result.verdict == Verdict.SELL


def test_twelve_one_momentum_basic():
    # Build a series where t-252 = 100, t-21 = 150 → 50% momentum.
    closes = np.array([100.0] * 232 + list(np.linspace(100, 150, 20)) + [150.0] * 21)
    series = pd.Series(closes)
    momentum = _twelve_one_momentum(series)
    # Allow a small tolerance — linspace can fractional things.
    assert 0.45 < momentum < 0.55


def test_rsi_on_constant_series_is_nan():
    series = pd.Series([100.0] * 60)
    rsi = _rsi(series)
    assert rsi.iloc[-1] != rsi.iloc[-1]  # NaN (no movement → div by zero)


# ──────────────────────────────────────────────────────────────
# Value
# ──────────────────────────────────────────────────────────────
def _funds(**overrides) -> Fundamentals:
    defaults = {
        "ticker": "ACME",
        "currency": "USD",
        "market_cap": 1e10,
        "trailing_pe": 10.0,
        "price_to_book": 1.2,
        "debt_to_equity": 40.0,
        "dividend_yield": 0.04,
        "free_cash_flow_yield": 0.08,
        "eps": 5.0,
        "sector": "Industrials",
    }
    defaults.update(overrides)
    return Fundamentals(**defaults)


def test_value_buys_cheap_fundamentals():
    strat = ValueStrategy()
    result = strat.score("ACME", noisy_close(), fundamentals=_funds())
    assert result.verdict == Verdict.BUY


def test_value_sells_expensive_fundamentals():
    strat = ValueStrategy()
    expensive = _funds(
        trailing_pe=80.0,
        price_to_book=12.0,
        debt_to_equity=350.0,
        dividend_yield=0.0,
        free_cash_flow_yield=-0.05,
    )
    result = strat.score("HIGH", noisy_close(), fundamentals=expensive)
    assert result.verdict == Verdict.SELL


def test_value_raises_without_fundamentals():
    strat = ValueStrategy()
    with pytest.raises(ValueError):
        strat.score("ACME", noisy_close(), fundamentals=None)


def test_value_handles_missing_ratios_gracefully():
    """When most ratios are None, score lands near neutral."""
    strat = ValueStrategy()
    sparse = Fundamentals(ticker="X", currency="USD")
    result = strat.score("X", noisy_close(), fundamentals=sparse)
    # Default-neutral signals yield a HOLD verdict around 0.5.
    assert result.verdict == Verdict.HOLD


# ──────────────────────────────────────────────────────────────
# DCA
# ──────────────────────────────────────────────────────────────
def test_simulate_dca_positive_on_rising_series():
    close = rising_close()["Close"]
    sim = simulate_dca(close, per_period_amount=100.0, cadence_days=21)
    assert sim.total_return > 0
    assert sim.total_invested > 0
    assert sim.final_value > sim.total_invested


def test_simulate_dca_negative_on_falling_series():
    close = falling_close()["Close"]
    sim = simulate_dca(close, per_period_amount=100.0, cadence_days=21)
    assert sim.total_return < 0


def test_dca_strategy_recommends_buy_on_rising_asset():
    strat = DCAStrategy()
    result = strat.score("UP", rising_close())
    assert result.verdict == Verdict.BUY


def test_dca_strategy_warns_on_failing_asset():
    strat = DCAStrategy()
    result = strat.score("DOWN", falling_close())
    # On a clear bear, DCA should not be BUY.
    assert result.verdict in {Verdict.SELL, Verdict.HOLD}
