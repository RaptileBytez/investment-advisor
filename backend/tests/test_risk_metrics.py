"""Risk-metric assertions against hand-computed values.

These tests are the canary on a critical part of the system — if the math
is wrong, every recommendation is wrong. They use deterministic synthetic
inputs and check both the values and the edge-case behaviour."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from app.risk.metrics import (
    annualized_volatility,
    beta,
    cagr,
    daily_log_returns,
    daily_simple_returns,
    herfindahl_index,
    max_drawdown,
    sharpe_ratio,
    value_at_risk,
)


# ──────────────────────────────────────────────────────────────
# Returns
# ──────────────────────────────────────────────────────────────
def test_simple_returns_basic():
    prices = pd.Series([100.0, 110.0, 99.0])
    ret = daily_simple_returns(prices)
    assert math.isclose(ret.iloc[0], 0.10, rel_tol=1e-9)
    assert math.isclose(ret.iloc[1], -0.10, rel_tol=1e-9)


def test_log_returns_basic():
    prices = pd.Series([100.0, 110.0])
    ret = daily_log_returns(prices)
    assert math.isclose(ret.iloc[0], math.log(1.1), rel_tol=1e-9)


# ──────────────────────────────────────────────────────────────
# Volatility
# ──────────────────────────────────────────────────────────────
def test_volatility_zero_for_constant_returns():
    ret = pd.Series([0.01] * 100)
    assert annualized_volatility(ret) == 0.0


def test_volatility_annualizes_correctly():
    # std(daily) = 0.01 → annualised should be 0.01 * sqrt(252)
    ret = pd.Series([0.01, -0.01] * 60)
    annual = annualized_volatility(ret)
    expected = pd.Series([0.01, -0.01] * 60).std(ddof=1) * math.sqrt(252)
    assert math.isclose(annual, expected, rel_tol=1e-9)


def test_volatility_handles_empty():
    assert math.isnan(annualized_volatility(pd.Series([], dtype=float)))


# ──────────────────────────────────────────────────────────────
# Sharpe
# ──────────────────────────────────────────────────────────────
def test_sharpe_textbook_example():
    # Mean daily return 0.001, std 0.01, rf=0 → Sharpe = (0.001 / 0.01) * sqrt(252)
    rng = np.random.default_rng(seed=42)
    ret = pd.Series(rng.normal(loc=0.001, scale=0.01, size=10_000))
    s = sharpe_ratio(ret, risk_free_rate=0.0)
    # Should land near 0.1 * sqrt(252) ≈ 1.587, allow generous tolerance.
    assert 1.3 < s < 1.9


def test_sharpe_zero_variance_returns_nan():
    ret = pd.Series([0.01] * 100)
    assert math.isnan(sharpe_ratio(ret, risk_free_rate=0.01))


def test_sharpe_subtracts_risk_free_rate():
    rng = np.random.default_rng(seed=7)
    ret = pd.Series(rng.normal(loc=0.0, scale=0.01, size=5_000))
    high = sharpe_ratio(ret, risk_free_rate=0.0)
    low = sharpe_ratio(ret, risk_free_rate=0.10)  # 10% rf
    assert high > low


# ──────────────────────────────────────────────────────────────
# Beta
# ──────────────────────────────────────────────────────────────
def test_beta_one_when_identical():
    rng = np.random.default_rng(seed=1)
    market = pd.Series(rng.normal(0, 0.01, 500))
    assert math.isclose(beta(market, market), 1.0, abs_tol=1e-9)


def test_beta_two_when_double_market():
    rng = np.random.default_rng(seed=2)
    market = pd.Series(rng.normal(0, 0.01, 500))
    asset = market * 2
    assert math.isclose(beta(asset, market), 2.0, abs_tol=1e-9)


def test_beta_zero_for_uncorrelated():
    rng = np.random.default_rng(seed=3)
    market = pd.Series(rng.normal(0, 0.01, 5_000))
    asset = pd.Series(rng.normal(0, 0.01, 5_000))
    assert abs(beta(asset, market)) < 0.1


def test_beta_handles_mismatched_index():
    a = pd.Series([0.01, 0.02, 0.03], index=[1, 2, 3])
    b = pd.Series([0.01, 0.02, 0.03], index=[2, 3, 4])
    # Two overlapping points → finite value.
    assert not math.isnan(beta(a, b))


# ──────────────────────────────────────────────────────────────
# Max drawdown
# ──────────────────────────────────────────────────────────────
def test_max_drawdown_known_series():
    # Peak at 100, trough at 60 → -40% drawdown.
    prices = pd.Series([50, 80, 100, 90, 60, 70, 80])
    assert math.isclose(max_drawdown(prices), -0.40, rel_tol=1e-9)


def test_max_drawdown_monotonically_increasing_is_zero():
    prices = pd.Series([100, 110, 120, 130])
    assert max_drawdown(prices) == 0.0


# ──────────────────────────────────────────────────────────────
# VaR
# ──────────────────────────────────────────────────────────────
def test_var_95_on_uniform_series():
    # Symmetric daily returns [-0.05 … +0.05]; 5th percentile ≈ -0.045.
    returns = pd.Series(np.linspace(-0.05, 0.05, 100))
    v = value_at_risk(returns, confidence=0.95)
    assert 0.04 < v < 0.05


def test_var_returns_nan_for_tiny_sample():
    assert math.isnan(value_at_risk(pd.Series([0.01, -0.02])))


def test_var_rejects_bad_confidence():
    with pytest.raises(ValueError):
        value_at_risk(pd.Series([0.0] * 50), confidence=1.5)


# ──────────────────────────────────────────────────────────────
# HHI
# ──────────────────────────────────────────────────────────────
def test_hhi_perfect_diversification():
    # Four equal weights → HHI = 4 * (0.25^2) = 0.25 = 1/N
    assert math.isclose(herfindahl_index([1, 1, 1, 1]), 0.25, rel_tol=1e-9)


def test_hhi_perfect_concentration():
    # Single position → HHI = 1.0
    assert herfindahl_index([1.0]) == 1.0


def test_hhi_empty_is_nan():
    assert math.isnan(herfindahl_index([]))


def test_hhi_handles_unnormalised_weights():
    # 2:1:1 ratio → normalised to [0.5, 0.25, 0.25] → HHI = 0.375
    assert math.isclose(herfindahl_index([20, 10, 10]), 0.375, rel_tol=1e-9)


# ──────────────────────────────────────────────────────────────
# CAGR
# ──────────────────────────────────────────────────────────────
def test_cagr_one_year_double():
    # 252 daily steps, price doubles → CAGR = 100%
    prices = pd.Series(np.linspace(100, 200, 253))
    c = cagr(prices)
    assert math.isclose(c, 1.0, abs_tol=1e-6)


def test_cagr_flat_is_zero():
    prices = pd.Series([100.0] * 252)
    assert math.isclose(cagr(prices), 0.0, abs_tol=1e-9)
