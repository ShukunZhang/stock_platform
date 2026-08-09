"""Unit tests for AnalysisRunner and StockAnalysisGraph with mocked LLMs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from tradingagents.graph.workflow import (
    StockAnalysisGraph,
    get_analysis_graph,
    reset_analysis_graph,
    _extract_json_blob,
)
from tradingagents.runner import AnalysisRunner


pytestmark = pytest.mark.unit


def _fake_llm_factory(response: AIMessage):
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.ainvoke = AsyncMock(return_value=response)
    return llm


@pytest.fixture(autouse=True)
def _reset_graph():
    reset_analysis_graph()
    yield
    reset_analysis_graph()


class TestAnalysisRunner:
    @pytest.mark.asyncio
    async def test_initialize(self):
        runner = AnalysisRunner()
        assert runner.initialized is False
        await runner.initialize()
        assert runner.initialized is True
        assert runner.name == "langgraph_manager"

    @pytest.mark.asyncio
    async def test_analyze_streaming_with_callback(self, monkeypatch):
        events = []

        class FakeGraph:
            async def arun(self, query, *, mode, symbols, status_callback):
                await status_callback({"type": "agent_status", "data": {"agent_name": "x"}})
                return {
                    "final": {"recommendation": "buy", "confidence": 0.9},
                    "traces": [],
                    "symbols": symbols or ["AAPL"],
                }

        monkeypatch.setattr(
            "tradingagents.runner.get_analysis_graph", lambda: FakeGraph()
        )
        runner = AnalysisRunner()

        async def cb(payload):
            events.append(payload)

        updates = [
            u
            async for u in runner.analyze_streaming(
                "buy AAPL?", status_callback=cb
            )
        ]
        assert events[0]["type"] == "agent_status"
        assert updates[-1]["type"] == "query_completed"
        assert updates[-1]["data"]["recommendation"] == "buy"


class TestStockAnalysisGraph:
    @pytest.mark.asyncio
    async def test_arun_happy_path_no_tools(self, monkeypatch):
        draft = {
            "recommendation": "buy",
            "confidence": 0.77,
            "rationale": "Price and PE support buy",
            "key_factors": ["momentum"],
            "risk_assessment": "Volatility risk",
            "symbols": ["AAPL"],
        }
        agent_msg = AIMessage(content=str(draft).replace("'", '"'))
        # ensure valid JSON string
        import json

        agent_msg = AIMessage(content=json.dumps(draft))
        verify_msg = AIMessage(content='{"passed": true, "feedback": "ok"}')

        call_count = {"n": 0}

        def get_llm(temperature=None):
            # first construction: agent llm; second: verifier
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _fake_llm_factory(agent_msg)
            return _fake_llm_factory(verify_msg)

        monkeypatch.setattr("tradingagents.graph.workflow.get_llm", get_llm)

        statuses = []

        async def cb(payload):
            statuses.append(payload)

        graph = StockAnalysisGraph()
        result = await graph.arun("Should I buy AAPL?", status_callback=cb)
        assert result["final"]["recommendation"] == "buy"
        assert result["final"]["confidence"] == 0.77
        assert result["final"]["verified"] is True
        assert any(s.get("type") == "final_recommendation" for s in statuses)
        agent_names = {
            s["data"]["agent_name"]
            for s in statuses
            if s.get("type") == "agent_status"
        }
        assert "orchestrator" in agent_names
        assert "verifier" in agent_names
        assert "risk" in agent_names
        assert "sentiment" in agent_names

    @pytest.mark.asyncio
    async def test_arun_llm_failure_uses_mock_fallback(self, monkeypatch):
        def get_llm(temperature=None):
            llm = MagicMock()
            llm.bind_tools.return_value = llm
            llm.ainvoke = AsyncMock(side_effect=RuntimeError("no key"))
            return llm

        monkeypatch.setattr("tradingagents.graph.workflow.get_llm", get_llm)
        graph = StockAnalysisGraph()
        # agent fails → mock draft; verifier also fails → forced pass
        result = await graph.arun("Analyze MSFT")
        assert result["final"]["recommendation"] in {"buy", "sell", "hold"}
        # mocked may be true from draft; if verifier force-pass still finalize
        assert "MSFT" in result["symbols"] or "AAPL" in result["symbols"]

    @pytest.mark.asyncio
    async def test_verification_retry_then_finalize(self, monkeypatch):
        import json

        drafts = [
            AIMessage(
                content=json.dumps(
                    {
                        "recommendation": "hold",
                        "confidence": 0.5,
                        "rationale": "thin",
                        "key_factors": [],
                        "risk_assessment": "n/a",
                    }
                )
            ),
            AIMessage(
                content=json.dumps(
                    {
                        "recommendation": "buy",
                        "confidence": 0.8,
                        "rationale": "Improved evidence with price 100",
                        "key_factors": ["price"],
                        "risk_assessment": "moderate",
                    }
                )
            ),
        ]
        verifies = [
            AIMessage(content='{"passed": false, "feedback": "need evidence"}'),
            AIMessage(content='{"passed": true, "feedback": "ok"}'),
        ]

        class SeqLLM:
            def __init__(self, responses):
                self.responses = list(responses)
                self.bind_tools = MagicMock(return_value=self)

            async def ainvoke(self, _messages):
                return self.responses.pop(0)

        agent_llm = SeqLLM(drafts)
        verifier_llm = SeqLLM(verifies)

        def get_llm(temperature=None):
            if temperature == 0:
                return verifier_llm
            return agent_llm

        monkeypatch.setattr("tradingagents.graph.workflow.get_llm", get_llm)
        monkeypatch.setattr(
            "tradingagents.graph.workflow.settings",
            MagicMock(max_verification_retries=3),
        )

        graph = StockAnalysisGraph()
        # StockAnalysisGraph.__init__ already bound tools on agent llm via get_llm()
        # Re-assign after init because bind_tools returned same SeqLLM
        graph.llm = agent_llm
        graph.verifier_llm = verifier_llm
        result = await graph.arun("AAPL analysis")
        assert result["final"]["recommendation"] == "buy"
        assert result["final"]["verified"] is True

    def test_get_analysis_graph_singleton(self, monkeypatch):
        def get_llm(temperature=None):
            return _fake_llm_factory(AIMessage(content="{}"))

        monkeypatch.setattr("tradingagents.graph.workflow.get_llm", get_llm)
        reset_analysis_graph()
        g1 = get_analysis_graph()
        g2 = get_analysis_graph()
        assert g1 is g2


class TestFinalizeParsingViaExtract:
    def test_extract_supports_finalize_fields(self):
        blob = _extract_json_blob(
            '{"recommendation":"SELL","confidence":"0.6","riskAssessment":"high"}'
        )
        assert blob["recommendation"] == "SELL"
        assert blob["riskAssessment"] == "high"
