"""Unit tests for health_check helpers (network mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from web_ui.backend import health_check


pytestmark = pytest.mark.unit


class TestCheckHealth:
    def test_healthy_200(self, monkeypatch):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"status": "healthy", "timestamp": "t"}
        monkeypatch.setattr(health_check.requests, "get", lambda *a, **k: resp)
        assert health_check.check_health() is True

    def test_non_200(self, monkeypatch):
        resp = MagicMock()
        resp.status_code = 503
        monkeypatch.setattr(health_check.requests, "get", lambda *a, **k: resp)
        assert health_check.check_health() is False

    def test_connection_error(self, monkeypatch):
        def boom(*a, **k):
            raise health_check.requests.exceptions.ConnectionError()

        monkeypatch.setattr(health_check.requests, "get", boom)
        assert health_check.check_health() is False
