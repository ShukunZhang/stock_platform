"""Unit tests for LangChain market tools wrappers."""

from __future__ import annotations

import json

import pytest

from tradingagents.tools.market import (
    MARKET_TOOLS,
    get_fundamentals_snapshot,
    get_price_history,
    get_stock_price,
    get_technical_snapshot,
)


pytestmark = pytest.mark.unit


class TestMarketTools:
    def test_market_tools_registry(self):
        names = {t.name for t in MARKET_TOOLS}
        assert names == {
            "get_stock_price",
            "get_price_history",
            "get_fundamentals_snapshot",
            "get_technical_snapshot",
        }

    def test_get_stock_price_returns_json(self, clear_market_keys):
        raw = get_stock_price.invoke({"symbol": "AAPL"})
        data = json.loads(raw)
        assert data["symbol"] == "AAPL"
        assert "price" in data

    def test_get_price_history_period_limits(self, clear_market_keys, monkeypatch):
        captured = {}

        def fake_history(symbol, limit=30):
            captured["limit"] = limit
            return {"symbol": symbol, "bars": [], "mock": True}

        monkeypatch.setattr(
            "tradingagents.tools.market.fetch_history", fake_history
        )
        get_price_history.invoke({"symbol": "AAPL", "period": "5d"})
        assert captured["limit"] == 5

        get_price_history.invoke({"symbol": "AAPL", "period": "3mo"})
        assert captured["limit"] == 66

        get_price_history.invoke({"symbol": "AAPL", "period": "6mo"})
        assert captured["limit"] == 132

        get_price_history.invoke({"symbol": "AAPL", "period": "1y"})
        assert captured["limit"] == 252

        get_price_history.invoke({"symbol": "AAPL", "period": "1mo"})
        assert captured["limit"] == 30

    def test_get_fundamentals_snapshot_returns_json(self, clear_market_keys):
        raw = get_fundamentals_snapshot.invoke({"symbol": "MSFT"})
        data = json.loads(raw)
        assert data["symbol"] == "MSFT"

    def test_get_technical_snapshot_returns_json(self, clear_market_keys):
        raw = get_technical_snapshot.invoke({"symbol": "NVDA"})
        data = json.loads(raw)
        assert data["symbol"] == "NVDA"
        assert "rsi14" in data
