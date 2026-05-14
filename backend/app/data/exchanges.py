"""Mapping ticker suffixes to exchanges, regions, currencies, and benchmarks.

This single source of truth is consulted by:
- the data provider (to determine native currency for a ticker),
- the risk module (to pick a region-appropriate benchmark and risk-free rate),
- the UI (to show market-hours / exchange context).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExchangeInfo:
    suffix: str            # e.g. ".DE" or "" for US
    exchange: str          # human-readable exchange name
    region: str            # ISO-3166 alpha-2 country code, or region (e.g. "US", "DE", "EU")
    currency: str          # ISO-4217 currency code
    benchmark: str         # yfinance index ticker
    benchmark_name: str    # human-readable benchmark


# Order: most specific first. The empty suffix is the fallback for US listings.
EXCHANGES: tuple[ExchangeInfo, ...] = (
    ExchangeInfo(".DE", "Xetra",               "DE", "EUR", "^GDAXI",  "DAX"),
    ExchangeInfo(".F",  "Frankfurt",           "DE", "EUR", "^GDAXI",  "DAX"),
    ExchangeInfo(".PA", "Euronext Paris",      "FR", "EUR", "^FCHI",   "CAC 40"),
    ExchangeInfo(".AS", "Euronext Amsterdam",  "NL", "EUR", "^AEX",    "AEX"),
    ExchangeInfo(".BR", "Euronext Brussels",   "BE", "EUR", "^BFX",    "BEL 20"),
    ExchangeInfo(".MI", "Borsa Italiana",      "IT", "EUR", "FTSEMIB.MI", "FTSE MIB"),
    ExchangeInfo(".MC", "BME Madrid",          "ES", "EUR", "^IBEX",   "IBEX 35"),
    ExchangeInfo(".LS", "Euronext Lisbon",     "PT", "EUR", "^PSI20",  "PSI 20"),
    ExchangeInfo(".VI", "Wiener Börse",        "AT", "EUR", "^ATX",    "ATX"),
    ExchangeInfo(".HE", "Nasdaq Helsinki",     "FI", "EUR", "^OMXH25", "OMX Helsinki 25"),
    ExchangeInfo(".ST", "Nasdaq Stockholm",    "SE", "SEK", "^OMX",    "OMX Stockholm 30"),
    ExchangeInfo(".OL", "Oslo Børs",           "NO", "NOK", "^OSEAX",  "OSE All-Share"),
    ExchangeInfo(".CO", "Nasdaq Copenhagen",   "DK", "DKK", "^OMXC25", "OMX Copenhagen 25"),
    ExchangeInfo(".L",  "London Stock Exchange","GB", "GBP", "^FTSE",  "FTSE 100"),
    ExchangeInfo(".SW", "SIX Swiss Exchange",  "CH", "CHF", "^SSMI",   "SMI"),
    ExchangeInfo(".TO", "Toronto Stock Exchange","CA", "CAD", "^GSPTSE","TSX Composite"),
    ExchangeInfo(".V",  "TSX Venture",         "CA", "CAD", "^GSPTSE", "TSX Composite"),
    ExchangeInfo(".HK", "Hong Kong",           "HK", "HKD", "^HSI",    "Hang Seng"),
    ExchangeInfo(".T",  "Tokyo",               "JP", "JPY", "^N225",   "Nikkei 225"),
    ExchangeInfo(".AX", "ASX",                 "AU", "AUD", "^AXJO",   "ASX 200"),
    ExchangeInfo(".NZ", "NZX",                 "NZ", "NZD", "^NZ50",   "NZX 50"),
    ExchangeInfo(".SS", "Shanghai",            "CN", "CNY", "000001.SS","SSE Composite"),
    ExchangeInfo(".SZ", "Shenzhen",            "CN", "CNY", "399001.SZ","SZSE Component"),
)

# Default (no suffix) — US listings.
US_EXCHANGE = ExchangeInfo("", "NYSE/Nasdaq", "US", "USD", "^GSPC", "S&P 500")


def info_for(ticker: str) -> ExchangeInfo:
    """Return the exchange info for a given ticker, defaulting to US."""
    upper = ticker.upper()
    for ex in EXCHANGES:
        if ex.suffix and upper.endswith(ex.suffix):
            return ex
    return US_EXCHANGE
