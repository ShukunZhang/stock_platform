"""Unit tests for tradingagents.tools.market_providers."""

from __future__ import annotations

import pytest

from tradingagents.tools import market_providers as mp


pytestmark = pytest.mark.unit


class TestHelpers:
    def test_sym_upper_and_strip(self):
        assert mp._sym(" aapl ") == "AAPL"

    def test_base_mock_known_ticker(self):
        base = mp._base_mock("AAPL")
        assert base["price"] == 211.56
        assert base["name"] == "Apple Inc"

    def test_base_mock_unknown_ticker_is_deterministic(self):
        a = mp._base_mock("ZZZZ")
        b = mp._base_mock("zzzz")
        assert a["price"] == b["price"]
        assert a["currency"] == "USD"

    def test_to_float_valid(self):
        assert mp._to_float("12.5") == 12.5

    def test_to_float_invalid_and_empty(self):
        assert mp._to_float(None) is None
        assert mp._to_float("") is None
        assert mp._to_float("-") is None
        assert mp._to_float("None") is None
        assert mp._to_float("abc") is None


class TestFormatters:
    def test_format_market_cap_scales(self):
        assert mp.format_market_cap(3.18e12) == "3.18T"
        assert mp.format_market_cap(2.5e9) == "2.50B"
        assert mp.format_market_cap(1.5e6) == "1.50M"
        assert mp.format_market_cap(500) == "500"

    def test_format_market_cap_invalid(self):
        assert mp.format_market_cap(None) == "—"
        assert mp.format_market_cap("x") == "—"

    def test_format_volume_scales(self):
        assert mp.format_volume(2_500_000) == "2.5M"
        assert mp.format_volume(2500) == "2.5K"
        assert mp.format_volume(42) == "42"

    def test_format_volume_invalid(self):
        assert mp.format_volume(None) == "—"


class TestFetchQuoteMockPath:
    def test_fetch_quote_mock_without_keys(self, clear_market_keys):
        quote = mp.fetch_quote("aapl")
        assert quote["symbol"] == "AAPL"
        assert quote["mock"] is True
        assert quote["provider"] == "mock"
        assert quote["mock_tag"] == "[MOCK]"
        assert quote["price"] > 0
        assert "change" in quote
        assert "change_percent" in quote

    def test_fetch_quotes_skips_empty_and_keys_by_symbol(self, clear_market_keys):
        out = mp.fetch_quotes(["AAPL", "", "MSFT"])
        assert set(out.keys()) == {"AAPL", "MSFT"}
        assert out["AAPL"]["mock"] is True


class TestFetchHistoryAndFundamentalsAndTechnicals:
    def test_fetch_history_mock(self, clear_market_keys):
        hist = mp.fetch_history("NVDA", limit=10)
        assert hist["symbol"] == "NVDA"
        assert hist["mock"] is True
        assert len(hist["bars"]) == 10
        assert {"date", "open", "high", "low", "close", "volume"} <= set(hist["bars"][0])

    def test_fetch_fundamentals_mock(self, clear_market_keys):
        fund = mp.fetch_fundamentals("TSLA")
        assert fund["symbol"] == "TSLA"
        assert fund["mock"] is True
        assert fund["trailingPE"] == 28.5
        assert "[MOCK]" in fund["shortName"]

    def test_fetch_technicals_from_mock_history(self, clear_market_keys):
        tech = mp.fetch_technicals("MSFT")
        assert tech["symbol"] == "MSFT"
        assert "sma20" in tech
        assert "sma50" in tech
        assert "ema12" in tech
        assert "rsi14" in tech
        assert tech["trend_hint"] in {"bullish", "bearish", "neutral"}

    def test_fetch_technicals_insufficient_history_branch(self, clear_market_keys, monkeypatch):
        monkeypatch.setattr(
            mp,
            "fetch_history",
            lambda symbol, limit=60: {
                "symbol": symbol.upper(),
                "bars": [{"close": 100}],
                "provider": "mock",
                "mock": True,
            },
        )
        monkeypatch.setattr(
            mp,
            "fetch_quote",
            lambda symbol: {"price": 123.45, "symbol": symbol.upper()},
        )
        tech = mp.fetch_technicals("XYZ")
        assert tech["mock"] is True
        assert tech["last_close"] == 123.45
        assert tech["trend_hint"] == "neutral"
        assert "insufficient history" in tech["note"]


class TestProviderCascadeWithFmp:
    def test_fetch_quote_uses_fmp_when_available(self, monkeypatch):
        monkeypatch.setenv("FMP_API_KEY", "test-key")
        monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)

        def fake_get_json(url, params=None, timeout=12.0):
            return [
                {
                    "price": 100.0,
                    "previousClose": 98.0,
                    "name": "Test Co",
                    "volume": 1000,
                    "marketCap": 1e9,
                    "changesPercentage": 2.04,
                }
            ]

        monkeypatch.setattr(mp, "_get_json", fake_get_json)
        quote = mp.fetch_quote("TEST")
        assert quote["provider"] == "fmp"
        assert quote["mock"] is False
        assert quote["price"] == 100.0
        assert quote["change"] == 2.0
