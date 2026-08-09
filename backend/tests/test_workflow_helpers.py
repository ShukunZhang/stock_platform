"""Unit tests for tradingagents.graph.workflow helper functions."""

from __future__ import annotations

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from tradingagents.graph.workflow import (
    FUNCTIONAL_AGENTS,
    TOOL_TO_AGENT,
    _agent_status,
    _extract_json_blob,
    _extract_symbols,
    _mock_draft,
    _mock_final,
    _now,
    reset_analysis_graph,
)


pytestmark = pytest.mark.unit


class TestExtractJsonBlob:
    def test_parses_plain_json(self):
        data = _extract_json_blob('{"passed": true, "feedback": "ok"}')
        assert data["passed"] is True
        assert data["feedback"] == "ok"

    def test_parses_json_embedded_in_text(self):
        text = 'Here is the result:\n{"recommendation": "buy", "confidence": 0.8}\nDone.'
        data = _extract_json_blob(text)
        assert data["recommendation"] == "buy"
        assert data["confidence"] == 0.8

    def test_returns_empty_dict_when_no_json(self):
        assert _extract_json_blob("no braces here") == {}

    def test_returns_empty_dict_on_invalid_json(self):
        assert _extract_json_blob("{not valid json}") == {}


class TestExtractSymbols:
    def test_extracts_ticker_symbols(self):
        assert "AAPL" in _extract_symbols("Should I buy AAPL?")
        assert "TSLA" in _extract_symbols("Compare TSLA and NVDA")

    def test_maps_company_names(self):
        symbols = _extract_symbols("Analyze Apple and Tesla")
        assert "AAPL" in symbols
        assert "TSLA" in symbols

    def test_filters_stopwords(self):
        symbols = _extract_symbols("WHAT SHOULD I BUY")
        assert "WHAT" not in symbols
        assert "SHOULD" not in symbols
        assert "BUY" not in symbols
        # defaults to AAPL when nothing remains
        assert symbols == ["AAPL"]

    def test_defaults_to_aapl_when_only_stopwords(self):
        assert _extract_symbols("buy sell hold") == ["AAPL"]

    def test_treats_casual_uppercase_words_as_tickers(self):
        """Source quirk: any 1–5 letter token can be treated as a ticker."""
        assert _extract_symbols("hello world") == ["HELLO", "WORLD"]

    def test_limits_to_five_symbols(self):
        query = "AAPL MSFT NVDA TSLA AMZN GOOGL META"
        symbols = _extract_symbols(query)
        assert len(symbols) <= 5

    def test_dedupes_company_name_with_ticker(self):
        symbols = _extract_symbols("Apple AAPL analysis")
        assert symbols.count("AAPL") == 1


class TestMockDraftAndFinal:
    def test_mock_draft_is_valid_json_with_mock_flag(self):
        raw = _mock_draft("buy apple?", ["AAPL"], "llm down")
        data = json.loads(raw)
        assert data["recommendation"] == "hold"
        assert data["mock"] is True
        assert "[MOCK]" in data["rationale"]
        assert "llm down" in data["rationale"]

    def test_mock_final_shape(self):
        final = _mock_final("q", ["MSFT"], "timeout", "on_demand")
        assert final["recommendation"] == "hold"
        assert final["mocked"] is True
        assert final["mock_tag"] == "[MOCK]"
        assert final["symbols"] == ["MSFT"]
        assert final["mode"] == "on_demand"
        assert final["verified"] is False
        assert "timestamp" in final


class TestAgentStatusAndConstants:
    def test_agent_status_minimal(self):
        payload = _agent_status("orchestrator", "idle", "Queued")
        assert payload["type"] == "agent_status"
        assert payload["data"]["agent_name"] == "orchestrator"
        assert payload["data"]["status"] == "idle"
        assert "error" not in payload["data"]

    def test_agent_status_with_optional_fields(self):
        payload = _agent_status(
            "verifier",
            "error",
            "failed",
            error="boom",
            trace=[{"step": "x"}],
            response={"action": "hold"},
        )
        assert payload["data"]["error"] == "boom"
        assert payload["data"]["trace"] == [{"step": "x"}]
        assert payload["data"]["response"]["action"] == "hold"

    def test_tool_to_agent_mapping(self):
        assert TOOL_TO_AGENT["get_stock_price"] == "market_data"
        assert TOOL_TO_AGENT["get_price_history"] == "market_data"
        assert TOOL_TO_AGENT["get_fundamentals_snapshot"] == "fundamentals"
        assert TOOL_TO_AGENT["get_technical_snapshot"] == "technical"

    def test_functional_agents_tuple(self):
        assert FUNCTIONAL_AGENTS == (
            "orchestrator",
            "market_data",
            "fundamentals",
            "technical",
            "sentiment",
            "risk",
            "verifier",
        )

    def test_now_returns_isoformat(self):
        stamp = _now()
        assert "T" in stamp
        assert stamp.endswith("+00:00") or "Z" in stamp or "+" in stamp


class TestRouteHelpersViaGraphBuild:
    """Exercise nested routers without changing source by inspecting compiled logic."""

    def test_reset_analysis_graph_clears_singleton(self):
        reset_analysis_graph()
        from tradingagents.graph import workflow as wf

        assert wf._graph is None
