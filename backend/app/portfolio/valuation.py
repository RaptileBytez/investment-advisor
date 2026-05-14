"""Portfolio valuation in a base currency.

Pulls current prices from the data provider, applies FX conversion to the
user's base currency, and surfaces position-level + portfolio-level metrics
(concentration, currency exposure)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.data.provider import DataProvider, ProviderError
from app.db.models import Holding
from app.portfolio.fx import fx_rate
from app.risk.metrics import herfindahl_index

log = logging.getLogger(__name__)


@dataclass
class PositionValuation:
    ticker: str
    quantity: float
    avg_cost: float           # native currency
    currency: str             # native currency
    current_price: float      # native currency
    market_value: float       # in base currency
    cost_basis: float         # in base currency
    unrealized_pl: float      # in base currency
    unrealized_pl_pct: float  # decimal
    weight: float             # of total portfolio


@dataclass
class PortfolioValuation:
    base_currency: str
    total_value: float
    total_cost_basis: float
    total_unrealized_pl: float
    total_unrealized_pl_pct: float
    concentration_hhi: float
    currency_exposure: dict[str, float] = field(default_factory=dict)
    positions: list[PositionValuation] = field(default_factory=list)


def value_portfolio(
    holdings: list[Holding],
    *,
    provider: DataProvider,
    base_currency: str,
) -> PortfolioValuation:
    """Compute the full valuation. Positions for which a quote cannot be
    fetched are skipped (logged at info) so a transient outage on one ticker
    doesn't black out the entire view."""

    base_currency = base_currency.upper()
    raw_positions: list[tuple[Holding, float, float, float]] = []
    # (holding, current_price_native, fx_to_base, market_value_base)

    for h in holdings:
        if h.quantity <= 0:
            continue
        try:
            quote = provider.get_quote(h.ticker)
        except ProviderError as exc:
            log.info("skipping %s in valuation: %s", h.ticker, exc)
            continue
        try:
            rate = fx_rate(provider, h.currency, base_currency)
        except ProviderError as exc:
            log.info("skipping %s in valuation (FX): %s", h.ticker, exc)
            continue
        market_value_base = h.quantity * quote.price * rate
        raw_positions.append((h, quote.price, rate, market_value_base))

    total_value = sum(p[3] for p in raw_positions)
    total_cost_basis = sum(p[0].quantity * p[0].avg_cost * p[2] for p in raw_positions)
    positions: list[PositionValuation] = []
    currency_totals: dict[str, float] = {}

    for h, price, rate, market_value_base in raw_positions:
        cost_basis_base = h.quantity * h.avg_cost * rate
        pl = market_value_base - cost_basis_base
        pl_pct = (pl / cost_basis_base) if cost_basis_base > 0 else 0.0
        weight = (market_value_base / total_value) if total_value > 0 else 0.0
        positions.append(
            PositionValuation(
                ticker=h.ticker,
                quantity=h.quantity,
                avg_cost=h.avg_cost,
                currency=h.currency,
                current_price=price,
                market_value=market_value_base,
                cost_basis=cost_basis_base,
                unrealized_pl=pl,
                unrealized_pl_pct=pl_pct,
                weight=weight,
            )
        )
        currency_totals[h.currency] = currency_totals.get(h.currency, 0.0) + market_value_base

    currency_exposure = (
        {c: v / total_value for c, v in currency_totals.items()} if total_value > 0 else {}
    )
    concentration = herfindahl_index([p.weight for p in positions]) if positions else float("nan")
    total_pl = total_value - total_cost_basis
    total_pl_pct = (total_pl / total_cost_basis) if total_cost_basis > 0 else 0.0

    return PortfolioValuation(
        base_currency=base_currency,
        total_value=total_value,
        total_cost_basis=total_cost_basis,
        total_unrealized_pl=total_pl,
        total_unrealized_pl_pct=total_pl_pct,
        concentration_hhi=concentration,
        currency_exposure=currency_exposure,
        positions=positions,
    )
