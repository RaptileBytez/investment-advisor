"""Smoke test: the app starts and `/health` returns ok."""

from __future__ import annotations

from app import __version__


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
