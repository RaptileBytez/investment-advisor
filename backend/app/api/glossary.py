"""Glossary endpoints — financial-term explanations with i18n fallback."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import GlossaryEntryOut, GlossarySummaryOut
from app.core.config import get_settings
from app.glossary.loader import get as get_entry
from app.glossary.loader import load_all, render_html

router = APIRouter()


def _resolve_lang(lang: str | None) -> str:
    if not lang:
        return get_settings().locale
    lang = lang.lower().split("-")[0]
    supported = {x.lower() for x in get_settings().supported_languages}
    return lang if lang in supported else "en"


@router.get("", response_model=list[GlossarySummaryOut])
def list_terms(lang: str | None = Query(None)):
    resolved = _resolve_lang(lang)
    entries = load_all(resolved).values()
    return [
        GlossarySummaryOut(
            key=e.key,
            title=e.title,
            short=e.short,
            language=e.language,
            language_fallback=e.language_fallback,
        )
        for e in entries
    ]


@router.get("/{key}", response_model=GlossaryEntryOut)
def get_term(key: str, lang: str | None = Query(None)):
    resolved = _resolve_lang(lang)
    entry = get_entry(key, lang=resolved)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"glossary entry '{key}' not found")
    return GlossaryEntryOut(
        key=entry.key,
        title=entry.title,
        short=entry.short,
        body_html=render_html(entry),
        related=list(entry.related),
        language=entry.language,
        language_fallback=entry.language_fallback,
    )
