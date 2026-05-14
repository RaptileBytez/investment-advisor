"""Pure-function tests for yfinance_provider helpers (no network)."""

from __future__ import annotations

import math

import pytest

from app.data.providers.yfinance_provider import _normalise_dividend_yield, _safe_float


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # yfinance ≥0.2.61 reports as percentage — divide by 100.
        (1.83, 0.0183),
        (4.5, 0.045),
        (12.0, 0.12),
        # Already-decimal values pass through unchanged.
        (0.0183, 0.0183),
        (0.045, 0.045),
        (0.0, 0.0),
        # Edge: exactly 1.0 is ambiguous; we treat as decimal (100 % yield is
        # effectively impossible).
        (1.0, 1.0),
    ],
)
def test_normalise_dividend_yield(raw, expected):
    result = _normalise_dividend_yield(raw)
    assert result is not None
    assert math.isclose(result, expected, rel_tol=1e-9)


def test_normalise_dividend_yield_handles_none():
    assert _normalise_dividend_yield(None) is None


def test_normalise_dividend_yield_handles_nan():
    assert _normalise_dividend_yield(float("nan")) is None


def test_safe_float_passes_through_numbers():
    assert _safe_float(3.14) == 3.14
    assert _safe_float("2.71") == 2.71


def test_safe_float_returns_none_on_nan_or_invalid():
    assert _safe_float(float("nan")) is None
    assert _safe_float("not-a-number") is None
    assert _safe_float(None) is None
