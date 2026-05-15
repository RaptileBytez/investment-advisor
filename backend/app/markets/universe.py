"""Loads the bundled index constituent JSON files into a typed universe.

The universe is the input to scoring/movers/top-picks — a beginner has no
ticker to type, so the app drives discovery from these curated lists.

Constituent files live next to this module under `universe/*.json`. They
are loaded once at import time (small payload, never changes at runtime)
and deduplicated by ticker so overlapping indices (Dow ⊂ S&P) don't
inflate downstream batch fetches.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.data.exchanges import info_for

log = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "universe"


@dataclass(frozen=True)
class UniverseEntry:
    ticker: str
    name: str
    sector: str
    region: str           # ISO-3166 alpha-2, derived from suffix
    exchange: str         # human-readable exchange
    currency: str         # ISO-4217
    index: str            # source index, e.g. "DAX 40"


def _load_one(path: Path) -> list[UniverseEntry]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("universe file %s unreadable: %s", path.name, exc)
        return []
    index_name = payload.get("index", path.stem)
    entries: list[UniverseEntry] = []
    for raw in payload.get("constituents", []):
        ticker = raw.get("ticker")
        if not ticker:
            continue
        ex = info_for(ticker)
        entries.append(
            UniverseEntry(
                ticker=ticker.upper(),
                name=raw.get("name", ticker),
                sector=raw.get("sector", ""),
                region=ex.region,
                exchange=ex.exchange,
                currency=ex.currency,
                index=index_name,
            )
        )
    return entries


def _load_all() -> list[UniverseEntry]:
    if not _DATA_DIR.exists():
        log.warning("universe directory missing: %s", _DATA_DIR)
        return []
    by_ticker: dict[str, UniverseEntry] = {}
    for path in sorted(_DATA_DIR.glob("*.json")):
        for entry in _load_one(path):
            # First occurrence wins (alphabetical: cac40, dax40, dow30, ftse100, nikkei, sp500).
            # The S&P 500 list will subsume any Dow tickers because Dow loads first;
            # that's intentional — keeps the "Dow 30" label on shared names rather
            # than relabelling them as S&P 500.
            by_ticker.setdefault(entry.ticker, entry)
    return list(by_ticker.values())


_UNIVERSE: list[UniverseEntry] = _load_all()
_REGIONS: frozenset[str] = frozenset(e.region for e in _UNIVERSE)


def load_universe(region: str | None = None) -> list[UniverseEntry]:
    """Return the universe, optionally filtered to a single ISO region code."""
    if region is None or region.lower() == "all":
        return list(_UNIVERSE)
    upper = region.upper()
    return [e for e in _UNIVERSE if e.region == upper]


def available_regions() -> list[str]:
    """ISO region codes present in the loaded universe, sorted."""
    return sorted(_REGIONS)


def reload_universe() -> None:
    """Re-read JSON files. Test-only — production never calls this."""
    global _UNIVERSE, _REGIONS
    _UNIVERSE = _load_all()
    _REGIONS = frozenset(e.region for e in _UNIVERSE)
