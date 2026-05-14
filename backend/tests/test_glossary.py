"""Glossary loader + API: i18n fallback, frontmatter parsing, rendering."""

from __future__ import annotations

from app.glossary import loader


def test_loader_finds_english_entries():
    entries = loader.load_all("en")
    # Spot-check a few core entries that must always exist.
    expected = {
        "volatility", "sharpe-ratio", "beta", "max-drawdown", "value-at-risk",
        "cagr", "risk-free-rate", "price-to-earnings", "dividend-yield", "rsi",
        "buy-and-hold", "dollar-cost-averaging", "value-investing",
        "momentum-investing", "diversification",
    }
    assert expected.issubset(entries.keys())


def test_loader_parses_frontmatter():
    entry = loader.get("sharpe-ratio", lang="en")
    assert entry is not None
    assert entry.title == "Sharpe Ratio"
    assert "Risk-adjusted return" in entry.short
    assert "volatility" in entry.related


def test_loader_falls_back_to_english_for_missing_language():
    # Spanish isn't shipped; loader should serve EN with language_fallback=True.
    entry = loader.get("volatility", lang="es")
    assert entry is not None
    assert entry.language == "en"
    assert entry.language_fallback is True


def test_loader_serves_native_german():
    entry = loader.get("volatility", lang="de")
    assert entry is not None
    assert entry.language == "de"
    assert entry.language_fallback is False
    assert "Volatilität" in entry.title


def test_loader_renders_markdown_to_html():
    entry = loader.get("sharpe-ratio", lang="en")
    html = loader.render_html(entry)
    assert "<h" in html or "<p>" in html


def test_loader_renders_gfm_tables():
    """The Sharpe-ratio entry contains a markdown table; CommonMark alone
    wouldn't render it. The custom MarkdownIt config must enable tables."""
    entry = loader.get("sharpe-ratio", lang="en")
    html = loader.render_html(entry)
    assert "<table>" in html
    assert "<th>" in html


def test_loader_preserves_inline_math_for_client_render():
    """LaTeX `$...$` and `$$...$$` must round-trip unchanged so KaTeX can
    render them on the client. CommonMark passes `$` through as text."""
    entry = loader.get("sharpe-ratio", lang="en")
    html = loader.render_html(entry)
    assert "$$" in html
    assert "\\frac" in html


def test_glossary_list_api(wired_client):
    """The list endpoint returns every seeded entry for the requested lang."""
    client, _, _ = wired_client
    resp = client.get("/api/glossary?lang=en")
    assert resp.status_code == 200
    keys = {e["key"] for e in resp.json()}
    assert "sharpe-ratio" in keys


def test_glossary_term_api_returns_html(wired_client):
    client, _, _ = wired_client
    resp = client.get("/api/glossary/sharpe-ratio?lang=de")
    assert resp.status_code == 200
    body = resp.json()
    assert body["language"] == "de"
    assert body["language_fallback"] is False
    assert "<" in body["body_html"]
    assert "Sharpe" in body["title"]


def test_glossary_api_falls_back_to_english(wired_client):
    """When a translation is missing, the API serves English with the flag set."""
    client, _, _ = wired_client
    resp = client.get("/api/glossary/sharpe-ratio?lang=fr")
    assert resp.status_code == 200
    body = resp.json()
    # 'fr' is not in supported_languages → resolver defaults to settings.locale ('en').
    assert body["language"] == "en"
