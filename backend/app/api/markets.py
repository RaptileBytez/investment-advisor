"""Market-discovery endpoints — indices ribbon, top movers, Top Picks.

These power the `/markets` page in the frontend. Heavy paths
(`top-picks`) lean on the 1-hour TTL cache inside `markets.service`;
indices and movers reuse the existing 60-second quote cache.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_data_provider
from app.api.schemas import IndexSnapshotOut, MoverOut, TopPickOut
from app.data.provider import DataProvider, ProviderError
from app.db.models import User
from app.markets import service

router = APIRouter()


def _normalise_lang(raw: str | None, fallback: str) -> str:
    code = (raw or fallback or "en").lower().split("-")[0]
    return code if code in {"en", "de"} else "en"


@router.get("/indices", response_model=list[IndexSnapshotOut])
def indices(
    provider: DataProvider = Depends(get_data_provider),
):
    try:
        snaps = service.indices_snapshot(provider)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        IndexSnapshotOut(
            ticker=s.ticker,
            name=s.name,
            region=s.region,
            price=s.price,
            previous_close=s.previous_close,
            change=s.change,
            change_pct=s.change_pct,
            currency=s.currency,
        )
        for s in snaps
    ]


@router.get("/movers", response_model=list[MoverOut])
def movers(
    region: str | None = Query(None, description="ISO region code (e.g. US, DE). Omit for all."),
    kind: str = Query("gainers", pattern="^(gainers|losers)$"),
    limit: int = Query(10, ge=1, le=50),
    provider: DataProvider = Depends(get_data_provider),
):
    try:
        ms = service.top_movers(provider, region=region, kind=kind, limit=limit)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return [
        MoverOut(
            ticker=m.ticker,
            name=m.name,
            exchange=m.exchange,
            region=m.region,
            currency=m.currency,
            price=m.price,
            previous_close=m.previous_close,
            change=m.change,
            change_pct=m.change_pct,
        )
        for m in ms
    ]


@router.get("/top-picks", response_model=list[TopPickOut])
def top_picks(
    region: str | None = Query(None),
    limit: int = Query(10, ge=1, le=30),
    lang: str | None = Query(None, description="UI language for rationale (en, de). Defaults to user's locale."),
    user: User = Depends(get_current_user),
    provider: DataProvider = Depends(get_data_provider),
):
    resolved_lang = _normalise_lang(lang, user.locale)
    try:
        picks = service.top_picks(
            provider,
            region=region,
            risk_tolerance=user.risk_tolerance,
            lang=resolved_lang,
            limit=limit,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        TopPickOut(
            ticker=p.ticker,
            name=p.name,
            exchange=p.exchange,
            region=p.region,
            currency=p.currency,
            price=p.price,
            change_pct=p.change_pct,
            action=p.action,
            confidence=p.confidence,
            rationale=p.rationale,
            score=p.score,
        )
        for p in picks
    ]
