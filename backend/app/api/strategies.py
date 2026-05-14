"""Strategy and recommendation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, get_data_provider
from app.api.schemas import EvaluateRequest, StrategyResultOut, VerdictOut
from app.data.provider import DataProvider, ProviderError
from app.db.models import RiskTolerance, User
from app.recommendation.engine import RecommendationEngine
from app.strategies import registry

router = APIRouter()


@router.get("", response_model=list[str])
def list_strategies():
    return registry.available()


@router.post("/evaluate", response_model=VerdictOut)
def evaluate(
    body: EvaluateRequest,
    user: User = Depends(get_current_user),
    provider: DataProvider = Depends(get_data_provider),
):
    if body.risk_tolerance:
        try:
            tolerance = RiskTolerance(body.risk_tolerance.lower())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        tolerance = user.risk_tolerance

    lang = (body.lang or user.locale or "en").lower().split("-")[0]
    if lang not in {"en", "de"}:
        lang = "en"

    engine = RecommendationEngine(provider)
    try:
        verdict = engine.evaluate(
            body.ticker,
            strategies=body.strategies,
            strategy_weights=body.strategy_weights,
            risk_tolerance=tolerance,
            history_period=body.history_period,
            lang=lang,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _verdict_to_schema(verdict)


def _verdict_to_schema(v) -> VerdictOut:
    from app.api.schemas import RiskSummaryOut

    risk = None
    if v.risk_summary is not None:
        rs = v.risk_summary
        risk = RiskSummaryOut(
            volatility=_finite(rs.volatility),
            sharpe=_finite(rs.sharpe),
            beta=_finite(rs.beta),
            max_drawdown=_finite(rs.max_drawdown),
            value_at_risk_95=_finite(rs.value_at_risk_95),
            benchmark=rs.benchmark,
            risk_free_rate=rs.risk_free_rate,
        )
    return VerdictOut(
        ticker=v.ticker,
        action=v.action.value,
        confidence=v.confidence,
        rationale=v.rationale,
        risk_summary=risk,
        strategy_results=[
            StrategyResultOut(
                strategy=r.strategy,
                ticker=r.ticker,
                verdict=r.verdict.value,
                score=r.score,
                rationale=r.rationale,
                key_inputs=r.key_inputs,
            )
            for r in v.strategy_results
        ],
    )


def _finite(x: float) -> float:
    """JSON cannot represent NaN/Inf — coerce to 0 for the wire."""
    return x if x == x and x not in (float("inf"), float("-inf")) else 0.0
