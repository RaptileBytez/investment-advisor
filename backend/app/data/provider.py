"""Abstract `DataProvider` interface and the data records it returns.

Concrete providers live in `app/data/providers/` and are selected at runtime
by `app/data/registry.py`. Keeping the interface narrow makes it cheap to add
new providers (Alpaca, IBKR, Finnhub …) later.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar

import pandas as pd


@dataclass(frozen=True)
class TickerInfo:
    ticker: str
    name: str
    exchange: str
    region: str          # ISO-3166 alpha-2
    currency: str        # ISO-4217


@dataclass(frozen=True)
class Quote:
    ticker: str
    price: float
    currency: str
    timestamp: datetime
    previous_close: float | None = None

    @property
    def change(self) -> float | None:
        if self.previous_close is None or self.previous_close == 0:
            return None
        return self.price - self.previous_close

    @property
    def change_pct(self) -> float | None:
        if self.previous_close is None or self.previous_close == 0:
            return None
        return (self.price - self.previous_close) / self.previous_close


@dataclass(frozen=True)
class Fundamentals:
    """Snapshot of fundamental ratios. Any field may be None when the upstream
    provider does not expose it."""

    ticker: str
    currency: str
    market_cap: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    debt_to_equity: float | None = None
    dividend_yield: float | None = None      # as decimal, e.g. 0.025 = 2.5%
    free_cash_flow_yield: float | None = None
    eps: float | None = None
    sector: str | None = None
    industry: str | None = None
    extras: dict = field(default_factory=dict)


class DataProvider(ABC):
    """Pluggable market-data source.

    Implementations should be cheap to instantiate (no network on __init__);
    they are constructed once per process via `registry.get_provider()`.
    """

    name: ClassVar[str] = "abstract"

    @abstractmethod
    def search(self, query: str, *, region: str | None = None, limit: int = 10) -> list[TickerInfo]:
        """Search for tickers matching `query`. Optionally filter by region."""

    @abstractmethod
    def get_quote(self, ticker: str) -> Quote:
        """Most recent price + previous-close for a ticker."""

    @abstractmethod
    def get_history(
        self,
        ticker: str,
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """OHLCV DataFrame indexed by date.

        Columns: Open, High, Low, Close, Volume. `period` follows yfinance
        conventions ("1d", "5d", "1mo", "1y", "5y", "max"). `interval`
        likewise ("1d", "1h", "5m" …)."""

    @abstractmethod
    def get_fundamentals(self, ticker: str) -> Fundamentals:
        """Latest available fundamental ratios for a ticker."""

    def get_quotes_batch(self, tickers: list[str]) -> dict[str, Quote]:
        """Bulk-fetch quotes for many tickers.

        Default implementation falls back to per-ticker `get_quote()` — fine
        for tests with `FakeProvider`. Real providers should override with a
        true batch call (e.g. `yf.download(...)`) so the market-discovery
        sweep over hundreds of tickers stays cheap.

        Tickers that fail individually are dropped from the result rather
        than failing the entire batch.
        """
        out: dict[str, Quote] = {}
        for ticker in tickers:
            try:
                out[ticker.upper()] = self.get_quote(ticker)
            except ProviderError:
                continue
        return out

    def get_histories_batch(
        self,
        tickers: list[str],
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> dict[str, pd.DataFrame]:
        """Bulk-fetch OHLCV histories for many tickers.

        Same fallback contract as `get_quotes_batch`. Real providers override.
        """
        out: dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            try:
                out[ticker.upper()] = self.get_history(ticker, period=period, interval=interval)
            except ProviderError:
                continue
        return out


class ProviderError(RuntimeError):
    """Raised when the upstream provider fails or returns unusable data."""
