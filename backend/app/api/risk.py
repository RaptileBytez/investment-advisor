"""Standalone risk endpoint — risk metrics for a ticker without running
the full recommendation engine. Useful for the Stock Detail page."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_data_provider
from app.api.schemas import RiskSummaryOut
from app.data.provider import DataProvider, ProviderError
from app.recommendation.engine import RecommendationEngine

router = APIRouter()


@router.get("/{ticker}", response_model=RiskSummaryOut)
def risk_for(
    ticker: str,
    period: str = "5y",
    provider: DataProvider = Depends(get_data_provider),
):
    engine = RecommendationEngine(provider)
    try:
        history = engine._fetch_history(ticker, period=period)
    except ProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    summary = engine._risk_summary(ticker, history)
    if summary is None:
        raise HTTPException(status_code=422, detail="insufficient history for risk metrics")
    return RiskSummaryOut(
        volatility=_finite(summary.volatility),
        sharpe=_finite(summary.sharpe),
        beta=_finite(summary.beta),
        max_drawdown=_finite(summary.max_drawdown),
        value_at_risk_95=_finite(summary.value_at_risk_95),
        benchmark=summary.benchmark,
        risk_free_rate=summary.risk_free_rate,
    )


def _finite(x: float) -> float:
    return x if x == x and x not in (float("inf"), float("-inf")) else 0.0
