"""Loader for glossary markdown entries.

Each entry is a markdown file with simple YAML-ish frontmatter delimited by
`---`. Storing content in markdown (not JSON) keeps long-form explanations
authorable in plain editors and makes diffs human-readable.

File layout: `glossary/entries/<lang>/<key>.md`. If a key has no file for
the requested language, the loader falls back to English and flags the
response so the UI can show a "Translated soon" notice."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from markdown_it import MarkdownIt

log = logging.getLogger(__name__)

_ENTRIES_DIR = Path(__file__).parent / "entries"
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_md_renderer = MarkdownIt("commonmark").enable("table")
# Tables are GFM, not CommonMark — but we don't want the full gfm-like
# preset because it pulls in linkify-it-py for URL auto-linking that we
# don't need. Math (`$...$` / `$$...$$`) is intentionally NOT rendered
# server-side; we keep the raw TeX in the HTML so the frontend can render
# it with KaTeX, which produces accessible MathML.


@dataclass(frozen=True)
class GlossaryEntry:
    key: str
    title: str
    short: str
    body_md: str
    related: tuple[str, ...]
    language: str
    language_fallback: bool


def _parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    head, body = match.group(1), match.group(2)
    meta: dict[str, str | list[str]] = {}
    for line in head.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            meta[k.strip()] = items
        else:
            meta[k.strip()] = v.strip('"').strip("'")
    return meta, body


def _load_entry(path: Path, requested_lang: str, language: str) -> GlossaryEntry | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        log.warning("could not read %s: %s", path, exc)
        return None
    meta, body = _parse_frontmatter(text)
    key = str(meta.get("key") or path.stem)
    return GlossaryEntry(
        key=key,
        title=str(meta.get("title") or key.replace("-", " ").title()),
        short=str(meta.get("short") or ""),
        body_md=body.strip(),
        related=tuple(meta.get("related") or []),
        language=language,
        language_fallback=(requested_lang != language),
    )


@lru_cache(maxsize=8)
def load_all(lang: str = "en") -> dict[str, GlossaryEntry]:
    """Return every entry for `lang`, falling back to EN for missing files.

    Cached per-language; restart the process to pick up new entries."""
    en_dir = _ENTRIES_DIR / "en"
    lang_dir = _ENTRIES_DIR / lang
    entries: dict[str, GlossaryEntry] = {}

    if en_dir.exists():
        for path in sorted(en_dir.glob("*.md")):
            entry = _load_entry(path, requested_lang=lang, language="en")
            if entry is not None:
                entries[entry.key] = entry

    if lang != "en" and lang_dir.exists():
        for path in sorted(lang_dir.glob("*.md")):
            entry = _load_entry(path, requested_lang=lang, language=lang)
            if entry is not None:
                entries[entry.key] = entry

    return entries


def get(key: str, lang: str = "en") -> GlossaryEntry | None:
    return load_all(lang).get(key)


def render_html(entry: GlossaryEntry) -> str:
    return _md_renderer.render(entry.body_md)
