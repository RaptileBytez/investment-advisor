"""Risk metrics — pure functions over pandas Series / DataFrames.

Every metric is a closed-form computation that takes numerical input and
returns a number. The data layer is *not* called from here; that keeps the
math unit-testable against textbook values and lets the recommendation
engine compose metrics freely.

Conventions:
- Returns mean daily simple returns (price ratio - 1) unless explicitly
  named `log_returns`.
- Annualisation factor `periods_per_year` defaults to 252 (US trading days);
  callers may pass 250 (Europe) or 260 (24/5 markets) if needed.
- All metrics return `float`; functions that cannot compute (insufficient
  data, zero variance, …) return `nan` so callers can handle uniformly.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

import numpy as np
import pandas as pd

DEFAULT_PERIODS_PER_YEAR = 252


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def daily_simple_returns(prices: pd.Series) -> pd.Series:
    """Daily simple returns: (P_t / P_{t-1}) - 1. Drops the first NaN."""
    return prices.pct_change().dropna()


def daily_log_returns(prices: pd.Series) -> pd.Series:
    """Daily log returns: ln(P_t / P_{t-1}). Drops the first NaN."""
    return np.log(prices / prices.shift(1)).dropna()


# ──────────────────────────────────────────────────────────────
# Volatility
# ──────────────────────────────────────────────────────────────
def annualized_volatility(
    returns: pd.Series,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
) -> float:
    """Annualised standard deviation of returns. Returns NaN if <2 samples."""
    if returns.size < 2:
        return float("nan")
    return float(returns.std(ddof=1) * math.sqrt(periods_per_year))


# ──────────────────────────────────────────────────────────────
# Sharpe ratio
# ──────────────────────────────────────────────────────────────
def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
) -> float:
    """Annualised Sharpe ratio: (mean excess return) / (std of excess return).

    `risk_free_rate` is the *annual* rate (0.04 = 4%). It's converted to a
    per-period rate before subtracting from the return series, which is the
    convention used in most textbooks and quant libraries."""
    if returns.size < 2:
        return float("nan")
    per_period_rf = risk_free_rate / periods_per_year
    excess = returns - per_period_rf
    std = excess.std(ddof=1)
    if std == 0 or math.isnan(std):
        return float("nan")
    return float((excess.mean() / std) * math.sqrt(periods_per_year))


# ──────────────────────────────────────────────────────────────
# Beta
# ──────────────────────────────────────────────────────────────
def beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
    """β = cov(asset, market) / var(market). Aligns on common index."""
    aligned = pd.concat([asset_returns, market_returns], axis=1, join="inner").dropna()
    if aligned.shape[0] < 2:
        return float("nan")
    a, m = aligned.iloc[:, 0], aligned.iloc[:, 1]
    var_m = m.var(ddof=1)
    if var_m == 0 or math.isnan(var_m):
        return float("nan")
    return float(a.cov(m) / var_m)


# ──────────────────────────────────────────────────────────────
# Max drawdown
# ──────────────────────────────────────────────────────────────
def max_drawdown(prices: pd.Series) -> float:
    """Largest peak-to-trough decline as a (negative) decimal.

    A drawdown of -0.25 means a 25% loss from the prior peak."""
    if prices.size < 2:
        return float("nan")
    running_max = prices.cummax()
    drawdowns = (prices - running_max) / running_max
    return float(drawdowns.min())


# ──────────────────────────────────────────────────────────────
# Value at Risk (historical method)
# ──────────────────────────────────────────────────────────────
def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
    """One-period VaR by the historical method.

    Returns the *loss* threshold as a positive decimal: a result of 0.03
    at 95% confidence means "on the worst 5% of days, losses were at least
    3%". Returns NaN if fewer than 20 samples are available."""
    if returns.size < 20:
        return float("nan")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be in (0, 1)")
    quantile = returns.quantile(1 - confidence)
    return float(-quantile)


# ──────────────────────────────────────────────────────────────
# Portfolio concentration (Herfindahl–Hirschman Index)
# ──────────────────────────────────────────────────────────────
def herfindahl_index(weights: Iterable[float]) -> float:
    """HHI = sum(w_i ^ 2). Normalised to [0, 1] given non-negative weights
    that sum to 1. 1.0 = fully concentrated, 1/N = perfectly diversified."""
    ws = [float(w) for w in weights]
    if not ws:
        return float("nan")
    total = sum(ws)
    if total <= 0:
        return float("nan")
    normalised = [w / total for w in ws]
    return float(sum(w * w for w in normalised))


# ──────────────────────────────────────────────────────────────
# Composite helper
# ──────────────────────────────────────────────────────────────
def cagr(prices: pd.Series, periods_per_year: int = DEFAULT_PERIODS_PER_YEAR) -> float:
    """Compound annual growth rate over the full price series."""
    if prices.size < 2:
        return float("nan")
    start, end = float(prices.iloc[0]), float(prices.iloc[-1])
    if start <= 0:
        return float("nan")
    periods = prices.size - 1
    if periods <= 0:
        return float("nan")
    years = periods / periods_per_year
    if years <= 0:
        return float("nan")
    return float((end / start) ** (1 / years) - 1)
