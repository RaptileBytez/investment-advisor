"""Market-data endpoints: search, quote, history, fundamentals."""

from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_data_provider
from app.api.schemas import (
    FundamentalsOut,
    HistoryBar,
    HistoryOut,
    QuoteOut,
    TickerInfoOut,
)
from app.data.provider import DataProvider, ProviderError

router = APIRouter()


@router.get("/search", response_model=list[TickerInfoOut])
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    region: str | None = Query(None, description="ISO-3166 region code"),
    limit: int = Query(10, ge=1, le=50),
    provider: DataProvider = Depends(get_data_provider),
):
    try:
        results = provider.search(q, region=region, limit=limit)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return [
        TickerInfoOut(
            ticker=r.ticker,
            name=r.name,
            exchange=r.exchange,
            region=r.region,
            currency=r.currency,
        )
        for r in results
    ]


@router.get("/quote/{ticker}", response_model=QuoteOut)
def quote(ticker: str, provider: DataProvider = Depends(get_data_provider)):
    try:
        q = provider.get_quote(ticker)
    except ProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return QuoteOut(
        ticker=q.ticker,
        price=q.price,
        currency=q.currency,
        timestamp=q.timestamp,
        previous_close=q.previous_close,
        change=q.change,
        change_pct=q.change_pct,
    )


@router.get("/history/{ticker}", response_model=HistoryOut)
def history(
    ticker: str,
    period: str = Query("1y", description="yfinance period (1mo, 1y, 5y, max …)"),
    interval: str = Query("1d", description="yfinance interval (1d, 1h, 1wk …)"),
    provider: DataProvider = Depends(get_data_provider),
):
    try:
        df: pd.DataFrame = provider.get_history(ticker, period=period, interval=interval)
    except ProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    bars: list[HistoryBar] = []
    for idx, row in df.iterrows():
        d = idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)[:10])
        bars.append(
            HistoryBar(
                date=d,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )
    return HistoryOut(ticker=ticker.upper(), period=period, interval=interval, bars=bars)


@router.get("/fundamentals/{ticker}", response_model=FundamentalsOut)
def fundamentals(ticker: str, provider: DataProvider = Depends(get_data_provider)):
    try:
        f = provider.get_fundamentals(ticker)
    except ProviderError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FundamentalsOut(
        ticker=f.ticker,
        currency=f.currency,
        market_cap=f.market_cap,
        trailing_pe=f.trailing_pe,
        forward_pe=f.forward_pe,
        price_to_book=f.price_to_book,
        debt_to_equity=f.debt_to_equity,
        dividend_yield=f.dividend_yield,
        free_cash_flow_yield=f.free_cash_flow_yield,
        eps=f.eps,
        sector=f.sector,
        industry=f.industry,
    )
