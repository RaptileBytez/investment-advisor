"""Portfolio endpoints: holdings, transactions, valuation, watchlist, prefs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, get_data_provider, get_portfolio_service
from app.api.schemas import (
    HoldingOut,
    PortfolioValuationOut,
    PositionValuationOut,
    TradeIn,
    TransactionOut,
    UserOut,
    UserPreferencesIn,
    WatchlistItemOut,
)
from app.data.provider import DataProvider
from app.db.models import RiskTolerance, TradeSide, User
from app.portfolio.service import PortfolioError, PortfolioService
from app.portfolio.valuation import value_portfolio

router = APIRouter()


# ── User / preferences ────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(_user_to_dict(user))


@router.put("/me", response_model=UserOut)
def update_preferences(
    body: UserPreferencesIn,
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    if body.base_currency is not None:
        user.base_currency = body.base_currency.upper()
    if body.locale is not None:
        user.locale = body.locale
    if body.risk_tolerance is not None:
        try:
            user.risk_tolerance = RiskTolerance(body.risk_tolerance.lower())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    service.db.commit()
    service.db.refresh(user)
    return UserOut.model_validate(_user_to_dict(user))


# ── Holdings & transactions ───────────────────────────────────
@router.get("/holdings", response_model=list[HoldingOut])
def list_holdings(
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return [HoldingOut.model_validate(h) for h in service.get_holdings(user.id)]


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(
    ticker: str | None = None,
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    txs = service.get_transactions(user.id, ticker=ticker)
    return [TransactionOut.model_validate(_tx_to_dict(t)) for t in txs]


@router.post("/trades", response_model=TransactionOut, status_code=201)
def record_trade(
    body: TradeIn,
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    try:
        side = TradeSide(body.side.lower())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid side: {body.side}") from exc
    try:
        tx = service.record_trade(
            user_id=user.id,
            ticker=body.ticker,
            side=side,
            quantity=body.quantity,
            price=body.price,
            executed_at=body.executed_at,
            fees=body.fees,
            currency=body.currency,
            note=body.note,
        )
    except PortfolioError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TransactionOut.model_validate(_tx_to_dict(tx))


# ── Valuation ─────────────────────────────────────────────────
@router.get("/valuation", response_model=PortfolioValuationOut)
def valuation(
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
    provider: DataProvider = Depends(get_data_provider),
):
    val = value_portfolio(
        service.get_holdings(user.id),
        provider=provider,
        base_currency=user.base_currency,
    )
    return PortfolioValuationOut(
        base_currency=val.base_currency,
        total_value=val.total_value,
        total_cost_basis=val.total_cost_basis,
        total_unrealized_pl=val.total_unrealized_pl,
        total_unrealized_pl_pct=val.total_unrealized_pl_pct,
        concentration_hhi=val.concentration_hhi if val.concentration_hhi == val.concentration_hhi else 0.0,
        currency_exposure=val.currency_exposure,
        positions=[
            PositionValuationOut(
                ticker=p.ticker,
                quantity=p.quantity,
                avg_cost=p.avg_cost,
                currency=p.currency,
                current_price=p.current_price,
                market_value=p.market_value,
                cost_basis=p.cost_basis,
                unrealized_pl=p.unrealized_pl,
                unrealized_pl_pct=p.unrealized_pl_pct,
                weight=p.weight,
            )
            for p in val.positions
        ],
    )


# ── Watchlist ─────────────────────────────────────────────────
@router.get("/watchlist", response_model=list[WatchlistItemOut])
def list_watchlist(
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    return [WatchlistItemOut.model_validate(item) for item in service.get_watchlist(user.id)]


@router.post("/watchlist/{ticker}", response_model=WatchlistItemOut, status_code=201)
def add_watch(
    ticker: str,
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    item = service.add_to_watchlist(user.id, ticker)
    return WatchlistItemOut.model_validate(item)


@router.delete("/watchlist/{ticker}", status_code=204)
def remove_watch(
    ticker: str,
    user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service),
):
    if not service.remove_from_watchlist(user.id, ticker):
        raise HTTPException(status_code=404, detail="ticker not in watchlist")


# ── Helpers ───────────────────────────────────────────────────
def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "base_currency": user.base_currency,
        "locale": user.locale,
        "risk_tolerance": user.risk_tolerance.value,
    }


def _tx_to_dict(tx) -> dict:
    return {
        "id": tx.id,
        "ticker": tx.ticker,
        "side": tx.side.value,
        "quantity": tx.quantity,
        "price": tx.price,
        "fees": tx.fees,
        "currency": tx.currency,
        "executed_at": tx.executed_at,
        "note": tx.note,
    }
