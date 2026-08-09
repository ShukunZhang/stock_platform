"""Unit tests for web_ui.backend.config helpers."""

from __future__ import annotations

import pytest

from web_ui.backend.config import _normalize_origin, _parse_cors_origins


pytestmark = pytest.mark.unit


class TestCorsHelpers:
    def test_normalize_origin_strips_trailing_slash(self):
        assert _normalize_origin(" https://app.example.com/ ") == "https://app.example.com"

    def test_parse_comma_separated(self):
        origins = _parse_cors_origins("http://localhost:8443, https://x.app/")
        assert origins == ["http://localhost:8443", "https://x.app"]

    def test_parse_json_array(self):
        origins = _parse_cors_origins('["http://a.com/", "http://b.com"]')
        assert origins == ["http://a.com", "http://b.com"]

    def test_parse_empty(self):
        assert _parse_cors_origins("") == []

    def test_parse_invalid_json_falls_back_to_csv(self):
        origins = _parse_cors_origins("[not-json, http://ok.com]")
        # leading [ without valid JSON → CSV split path
        assert origins == ["[not-json", "http://ok.com]"]
