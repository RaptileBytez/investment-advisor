"""Pydantic schemas for API request/response bodies."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────────────────────
# Market data
# ──────────────────────────────────────────────────────────────
class TickerInfoOut(BaseModel):
    ticker: str
    name: str
    exchange: str
    region: str
    currency: str


class QuoteOut(BaseModel):
    ticker: str
    price: float
    currency: str
    timestamp: datetime
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None


class HistoryBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class HistoryOut(BaseModel):
    ticker: str
    period: str
    interval: str
    bars: list[HistoryBar]


class FundamentalsOut(BaseModel):
    ticker: str
    currency: str
    market_cap: float | None = None
    trailing_pe: float | None = None
    forward_pe: float | None = None
    price_to_book: float | None = None
    debt_to_equity: float | None = None
    dividend_yield: float | None = None
    free_cash_flow_yield: float | None = None
    eps: float | None = None
    sector: str | None = None
    industry: str | None = None


# ──────────────────────────────────────────────────────────────
# Strategies / Recommendation
# ──────────────────────────────────────────────────────────────
class StrategyResultOut(BaseModel):
    strategy: str
    ticker: str
    verdict: str
    score: float
    rationale: str
    key_inputs: dict = Field(default_factory=dict)


class RiskSummaryOut(BaseModel):
    volatility: float
    sharpe: float
    beta: float
    max_drawdown: float
    value_at_risk_95: float
    benchmark: str
    risk_free_rate: float


class VerdictOut(BaseModel):
    ticker: str
    action: str
    confidence: float
    rationale: str
    risk_summary: RiskSummaryOut | None = None
    strategy_results: list[StrategyResultOut] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    ticker: str
    strategies: list[str] | None = None
    strategy_weights: dict[str, float] | None = None
    risk_tolerance: str | None = None     # "conservative" | "balanced" | "aggressive"
    history_period: str = "5y"
    lang: str | None = None               # "en" | "de"; defaults to user.locale


# ──────────────────────────────────────────────────────────────
# Portfolio
# ──────────────────────────────────────────────────────────────
class TradeIn(BaseModel):
    ticker: str
    side: str                              # "buy" | "sell"
    quantity: float
    price: float
    executed_at: datetime
    fees: float = 0.0
    currency: str | None = None
    note: str | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticker: str
    side: str
    quantity: float
    price: float
    fees: float
    currency: str
    executed_at: datetime
    note: str | None = None


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    quantity: float
    avg_cost: float
    currency: str


class PositionValuationOut(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    currency: str
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_pl_pct: float
    weight: float


class PortfolioValuationOut(BaseModel):
    base_currency: str
    total_value: float
    total_cost_basis: float
    total_unrealized_pl: float
    total_unrealized_pl_pct: float
    concentration_hhi: float
    currency_exposure: dict[str, float]
    positions: list[PositionValuationOut]


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    added_at: datetime


# ──────────────────────────────────────────────────────────────
# User / preferences
# ──────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    base_currency: str
    locale: str
    risk_tolerance: str


class UserPreferencesIn(BaseModel):
    base_currency: str | None = None
    locale: str | None = None
    risk_tolerance: str | None = None


# ──────────────────────────────────────────────────────────────
# Markets discovery
# ──────────────────────────────────────────────────────────────
class IndexSnapshotOut(BaseModel):
    ticker: str
    name: str
    region: str
    price: float
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None
    currency: str


class MoverOut(BaseModel):
    ticker: str
    name: str
    exchange: str
    region: str
    currency: str
    price: float
    previous_close: float | None = None
    change: float | None = None
    change_pct: float | None = None


class TopPickOut(BaseModel):
    ticker: str
    name: str
    exchange: str
    region: str
    currency: str
    price: float
    change_pct: float | None = None
    action: str
    confidence: float
    rationale: str
    score: float


# ──────────────────────────────────────────────────────────────
# Glossary
# ──────────────────────────────────────────────────────────────
class GlossaryEntryOut(BaseModel):
    key: str
    title: str
    short: str
    body_html: str
    related: list[str] = Field(default_factory=list)
    language: str
    language_fallback: bool = False        # True if served from EN when requested lang missing


class GlossarySummaryOut(BaseModel):
    key: str
    title: str
    short: str
    language: str
    language_fallback: bool = False
