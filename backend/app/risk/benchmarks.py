"""Region-aware benchmarks and risk-free rates.

Beta and Sharpe ratio are meaningless without anchoring to the right market
and risk-free instrument:
- SAP.DE compared to the S&P 500 produces a misleading beta.
- A USD T-bill is the wrong risk-free rate for a portfolio quoted in EUR.

This module produces a `RegionRiskConfig` for any ticker (via its suffix)
and exposes a function that fetches a live short-rate where one is available,
falling back to a static default per region. Defaults are intentionally
conservative; users can override per region at config time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.data.exchanges import info_for
from app.data.provider import DataProvider, ProviderError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegionRiskConfig:
    region: str                            # ISO-3166 alpha-2 (or "EU")
    benchmark_ticker: str                  # yfinance index ticker
    benchmark_name: str                    # human-readable
    risk_free_rate_ticker: str | None      # yfinance ticker if a live rate exists
    risk_free_rate_fallback: float         # decimal, used when live fetch fails


# Conservative defaults. Override in deployment via environment if you need
# precise figures (live fetch is preferred where supported).
REGION_CONFIGS: dict[str, RegionRiskConfig] = {
    # US — 13-week T-bill (^IRX is quoted in %, we divide by 100).
    "US": RegionRiskConfig("US", "^GSPC",  "S&P 500",       "^IRX", 0.04),
    # Eurozone — fall back to ECB €STR proxy (no reliable yfinance ticker).
    "DE": RegionRiskConfig("DE", "^GDAXI", "DAX",            None,   0.03),
    "FR": RegionRiskConfig("FR", "^FCHI",  "CAC 40",         None,   0.03),
    "NL": RegionRiskConfig("NL", "^AEX",   "AEX",            None,   0.03),
    "IT": RegionRiskConfig("IT", "FTSEMIB.MI", "FTSE MIB",   None,   0.03),
    "ES": RegionRiskConfig("ES", "^IBEX",  "IBEX 35",        None,   0.03),
    "BE": RegionRiskConfig("BE", "^BFX",   "BEL 20",         None,   0.03),
    "PT": RegionRiskConfig("PT", "^PSI20", "PSI 20",         None,   0.03),
    "AT": RegionRiskConfig("AT", "^ATX",   "ATX",            None,   0.03),
    "FI": RegionRiskConfig("FI", "^OMXH25","OMX Helsinki 25",None,   0.03),
    # Nordics outside the euro.
    "SE": RegionRiskConfig("SE", "^OMX",   "OMX Stockholm 30",None,  0.035),
    "NO": RegionRiskConfig("NO", "^OSEAX", "Oslo All-Share", None,   0.045),
    "DK": RegionRiskConfig("DK", "^OMXC25","OMX Copenhagen 25",None, 0.03),
    # UK — BoE base rate is the typical proxy.
    "GB": RegionRiskConfig("GB", "^FTSE",  "FTSE 100",       None,   0.04),
    # Switzerland — SNB policy rate.
    "CH": RegionRiskConfig("CH", "^SSMI",  "SMI",            None,   0.01),
    # APAC.
    "JP": RegionRiskConfig("JP", "^N225",  "Nikkei 225",     None,   0.005),
    "HK": RegionRiskConfig("HK", "^HSI",   "Hang Seng",      None,   0.04),
    "AU": RegionRiskConfig("AU", "^AXJO",  "ASX 200",        None,   0.04),
    "NZ": RegionRiskConfig("NZ", "^NZ50",  "NZX 50",         None,   0.04),
    "CN": RegionRiskConfig("CN", "000001.SS","SSE Composite",None,   0.02),
    # Americas.
    "CA": RegionRiskConfig("CA", "^GSPTSE","TSX Composite",  None,   0.035),
}

DEFAULT_CONFIG = REGION_CONFIGS["US"]


def get_config_for_ticker(ticker: str) -> RegionRiskConfig:
    return REGION_CONFIGS.get(info_for(ticker).region, DEFAULT_CONFIG)


def get_config_for_region(region: str) -> RegionRiskConfig:
    return REGION_CONFIGS.get(region.upper(), DEFAULT_CONFIG)


def get_risk_free_rate(region: str, provider: DataProvider) -> float:
    """Resolve a current risk-free rate for the region.

    Falls back to the configured static rate if no live ticker is mapped or
    the provider raises. Returned value is a decimal (0.04 = 4%)."""
    cfg = get_config_for_region(region)
    if cfg.risk_free_rate_ticker:
        try:
            quote = provider.get_quote(cfg.risk_free_rate_ticker)
            return quote.price / 100.0
        except ProviderError as exc:
            log.info("risk-free rate live fetch failed for %s: %s", region, exc)
    return cfg.risk_free_rate_fallback
