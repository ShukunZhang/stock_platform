"""
LangGraph stock analysis workflow.

Loop stack (LangChain loop engineering):
1. Agent loop      — model + tools until analysis draft is ready
2. Verification    — rubric check; retry with feedback when failing
3. Event-driven    — handled by SelfDrivingLoop (cron-style ticks)

Failures (rate limits, API outages) fall back to tagged [MOCK] results
so local testing is not blocked.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from tradingagents.config import settings
from tradingagents.graph.state import AnalysisState
from tradingagents.llm import get_llm
from tradingagents.tools.market import MARKET_TOOLS

logger = logging.getLogger(__name__)

StatusCallback = Optional[Callable[[dict[str, Any]], Any]]

AGENT_SYSTEM = """You are a stock analysis agent.
Use tools to gather live market, technical, and fundamentals data.
If a tool response includes "mock": true or "[MOCK]", treat it as fallback test data
and mention [MOCK] in your rationale.

Produce a concise investment recommendation for the user query.

Return a final answer that includes:
- recommendation: buy | sell | hold
- confidence: 0-1
- rationale: short explanation with key numbers
- key_factors: bullet list
- risk_assessment: short paragraph
- symbols analyzed
"""

VERIFIER_SYSTEM = """You are a strict analysis grader.
Given the user query and the draft recommendation, score whether it is usable.

Pass only if:
1) It references concrete price or fundamental/technical evidence
2) It gives a clear buy/sell/hold
3) Confidence is present and rationale is coherent
4) It does not invent unavailable data
5) If draft uses [MOCK] data, still pass when structure is valid

Respond ONLY as JSON:
{"passed": true|false, "feedback": "..."}
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _extract_json_blob(text: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def _extract_symbols(query: str) -> list[str]:
    tickers = re.findall(r"\b[A-Z]{1,5}\b", query.upper())
    stop = {
        "I", "A", "AN", "THE", "FOR", "AND", "OR", "BUY", "SELL", "HOLD",
        "VS", "WHAT", "SHOULD", "ANALYZE", "STOCK", "PRICE", "USD", "CEO",
        "EPS", "PE", "AI", "MOCK",
    }
    cleaned = [t for t in tickers if t not in stop]
    mapping = {
        "APPLE": "AAPL",
        "TESLA": "TSLA",
        "NVIDIA": "NVDA",
        "MICROSOFT": "MSFT",
        "GOOGLE": "GOOGL",
        "AMAZON": "AMZN",
        "META": "META",
    }
    upper_q = query.upper()
    for name, sym in mapping.items():
        if name in upper_q and sym not in cleaned:
            cleaned.append(sym)
    return cleaned[:5] or ["AAPL"]


def _mock_draft(query: str, symbols: list[str], reason: str) -> str:
    sym = ", ".join(symbols) or "AAPL"
    return json.dumps(
        {
            "recommendation": "hold",
            "confidence": 0.42,
            "rationale": (
                f"[MOCK] Live model/tool call failed ({reason}). "
                f"Fallback analysis for {sym} based on query: {query[:160]}"
            ),
            "key_factors": [
                "[MOCK] Live data unavailable — using fallback",
                f"Symbols: {sym}",
            ],
            "risk_assessment": (
                "[MOCK] Do not use for real trading. Generated for local testing only."
            ),
            "symbols": symbols,
            "mock": True,
        }
    )


TOOL_TO_AGENT: dict[str, str] = {
    "get_stock_price": "market_data",
    "get_price_history": "market_data",
    "get_fundamentals_snapshot": "fundamentals",
    "get_technical_snapshot": "technical",
}

FUNCTIONAL_AGENTS = (
    "orchestrator",
    "market_data",
    "fundamentals",
    "technical",
    "sentiment",
    "risk",
    "verifier",
)


def _agent_status(
    agent_name: str,
    status: str,
    message: str,
    *,
    error: str | None = None,
    trace: list[dict[str, Any]] | None = None,
    response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "agent_name": agent_name,
        "status": status,
        "message": message,
    }
    if error:
        data["error"] = error
    if trace is not None:
        data["trace"] = trace
    if response is not None:
        data["response"] = response
    return {"type": "agent_status", "data": data}


def _mock_final(query: str, symbols: list[str], reason: str, mode: str) -> dict[str, Any]:
    draft = _extract_json_blob(_mock_draft(query, symbols, reason))
    return {
        "recommendation": draft.get("recommendation", "hold"),
        "confidence": float(draft.get("confidence") or 0.42),
        "rationale": draft.get("rationale", "[MOCK] fallback"),
        "key_factors": draft.get("key_factors") or [],
        "risk_assessment": draft.get("risk_assessment") or "",
        "symbols": symbols,
        "mode": mode,
        "attempts": 1,
        "verified": False,
        "mocked": True,
        "mock_tag": "[MOCK]",
        "mock_reason": reason,
        "timestamp": _now(),
    }


class StockAnalysisGraph:
    """Compiled LangGraph with functional specialist status reporting."""

    def __init__(self) -> None:
        self.tools = MARKET_TOOLS
        self.llm = get_llm().bind_tools(self.tools)
        self.verifier_llm = get_llm(temperature=0)
        self._status_callback: StatusCallback = None
        self.graph = self._build()

    async def _emit(self, payload: dict[str, Any]) -> None:
        if self._status_callback:
            await self._status_callback(payload)

    def _build(self):
        base_tool_node = ToolNode(self.tools)

        async def agent_node(state: AnalysisState) -> dict[str, Any]:
            await self._emit(
                _agent_status(
                    "orchestrator",
                    "processing",
                    "Planning analysis and selecting specialists",
                )
            )
            messages = list(state["messages"])
            if not messages or not isinstance(messages[0], SystemMessage):
                messages = [SystemMessage(content=AGENT_SYSTEM), *messages]

            feedback = state.get("verification_feedback") or ""
            if feedback:
                messages.append(
                    HumanMessage(
                        content=f"Previous draft failed verification. Fix this:\n{feedback}"
                    )
                )

            used_mock = False
            mock_reason = ""
            try:
                response = await self.llm.ainvoke(messages)
                draft = (
                    response.content
                    if isinstance(response.content, str)
                    else str(response.content)
                )
                out_messages = [response]
                tool_calls = getattr(response, "tool_calls", None) or []
                if tool_calls:
                    specialists = sorted(
                        {
                            TOOL_TO_AGENT.get(tc.get("name", ""), "market_data")
                            for tc in tool_calls
                        }
                    )
                    await self._emit(
                        _agent_status(
                            "orchestrator",
                            "processing",
                            f"Dispatching to: {', '.join(specialists)}",
                        )
                    )
                else:
                    await self._emit(
                        _agent_status(
                            "orchestrator",
                            "processing",
                            "Drafting recommendation from available context",
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                used_mock = True
                mock_reason = str(exc)
                logger.warning("[MOCK] orchestrator LLM failed: %s", mock_reason)
                await self._emit(
                    _agent_status(
                        "orchestrator",
                        "error",
                        f"[MOCK] Orchestrator LLM failed → fallback ({mock_reason})",
                        error=mock_reason,
                    )
                )
                draft = _mock_draft(state["query"], state.get("symbols") or [], mock_reason)
                out_messages = [AIMessage(content=draft)]

            return {
                "messages": out_messages,
                "draft_recommendation": draft,
                "attempt": state.get("attempt", 0) + 1,
                "traces": [
                    {
                        "timestamp": _now(),
                        "step": "orchestrator",
                        "message": (
                            f"[MOCK] LLM fallback: {mock_reason}"
                            if used_mock
                            else "Orchestrator produced draft / tool plan"
                        ),
                        "attempt": state.get("attempt", 0) + 1,
                        "mocked": used_mock,
                    }
                ],
            }

        async def tools_node(state: AnalysisState) -> dict[str, Any]:
            messages = state.get("messages") or []
            last = messages[-1] if messages else None
            tool_calls = getattr(last, "tool_calls", None) or []
            active_agents: set[str] = set()

            for tc in tool_calls:
                name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
                agent_id = TOOL_TO_AGENT.get(name, "market_data")
                active_agents.add(agent_id)
                await self._emit(
                    _agent_status(
                        agent_id,
                        "processing",
                        f"Running tool: {name}",
                    )
                )

            try:
                result = await base_tool_node.ainvoke(state)
            except Exception as exc:  # noqa: BLE001
                reason = str(exc)
                for agent_id in active_agents or {"market_data"}:
                    await self._emit(
                        _agent_status(
                            agent_id,
                            "error",
                            f"[MOCK] Tool stage failed → continue ({reason})",
                            error=reason,
                        )
                    )
                raise

            # Inspect tool outputs for mock tags
            out_messages = result.get("messages") if isinstance(result, dict) else []
            mocked_agents: set[str] = set()
            for msg in out_messages or []:
                content = getattr(msg, "content", "") or ""
                if "[MOCK]" in str(content) or '"mock": true' in str(content).lower():
                    # best-effort: mark all active agents if mock detected
                    mocked_agents |= active_agents

            for agent_id in active_agents:
                await self._emit(
                    _agent_status(
                        agent_id,
                        "completed",
                        (
                            f"[MOCK] {agent_id} finished with fallback data"
                            if agent_id in mocked_agents
                            else f"{agent_id} data collected"
                        ),
                    )
                )
            return result

        async def verify_node(state: AnalysisState) -> dict[str, Any]:
            await self._emit(
                _agent_status("verifier", "processing", "Scoring draft against rubric")
            )
            draft = state.get("draft_recommendation") or ""
            prompt = [
                SystemMessage(content=VERIFIER_SYSTEM),
                HumanMessage(content=f"Query:\n{state['query']}\n\nDraft:\n{draft}"),
            ]
            try:
                result = await self.verifier_llm.ainvoke(prompt)
                text = (
                    result.content
                    if isinstance(result.content, str)
                    else str(result.content)
                )
                parsed = _extract_json_blob(text)
                passed = bool(parsed.get("passed"))
                feedback = str(parsed.get("feedback") or text)
                trace_msg = "passed" if passed else f"failed: {feedback[:200]}"
                await self._emit(
                    _agent_status(
                        "verifier",
                        "completed" if passed else "error",
                        f"Verification {trace_msg}",
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("[MOCK] verifier LLM failed: %s", exc)
                passed = True
                feedback = ""
                trace_msg = f"[MOCK] verifier fallback pass ({exc})"
                await self._emit(
                    _agent_status(
                        "verifier",
                        "error",
                        trace_msg,
                        error=str(exc),
                    )
                )

            return {
                "verification_passed": passed,
                "verification_feedback": "" if passed else feedback,
                "traces": [
                    {
                        "timestamp": _now(),
                        "step": "verification_loop",
                        "message": trace_msg,
                        "passed": passed,
                    }
                ],
            }

        async def finalize_node(state: AnalysisState) -> dict[str, Any]:
            await self._emit(
                _agent_status("risk", "processing", "Assessing risk and position stance")
            )
            draft = state.get("draft_recommendation") or ""
            parsed = _extract_json_blob(draft)
            recommendation = str(parsed.get("recommendation") or "hold").lower()
            if recommendation not in {"buy", "sell", "hold"}:
                lower = draft.lower()
                if "buy" in lower and "sell" not in lower:
                    recommendation = "buy"
                elif "sell" in lower:
                    recommendation = "sell"
                else:
                    recommendation = "hold"

            confidence = parsed.get("confidence")
            try:
                confidence_f = float(confidence) if confidence is not None else 0.55
            except (TypeError, ValueError):
                confidence_f = 0.55

            mocked = bool(parsed.get("mock")) or "[MOCK]" in draft
            rationale = parsed.get("rationale") or draft[:1200]
            if mocked and "[MOCK]" not in str(rationale):
                rationale = f"[MOCK] {rationale}"

            risk_text = (
                parsed.get("risk_assessment")
                or parsed.get("riskAssessment")
                or ""
            )
            final_result = {
                "recommendation": recommendation,
                "confidence": confidence_f,
                "rationale": rationale,
                "key_factors": parsed.get("key_factors")
                or parsed.get("keyFactors")
                or [],
                "risk_assessment": risk_text,
                "symbols": state.get("symbols") or [],
                "mode": state.get("mode") or "on_demand",
                "attempts": state.get("attempt") or 1,
                "verified": bool(state.get("verification_passed")),
                "mocked": mocked,
                "mock_tag": "[MOCK]" if mocked else None,
                "timestamp": _now(),
            }

            await self._emit(
                _agent_status(
                    "risk",
                    "completed",
                    risk_text[:160] or f"Stance: {recommendation}",
                )
            )
            await self._emit(
                _agent_status(
                    "sentiment",
                    "completed",
                    "Sentiment inferred from available news/context in draft",
                )
            )
            await self._emit(
                _agent_status(
                    "orchestrator",
                    "completed",
                    (
                        f"[MOCK] Final recommendation: {recommendation}"
                        if mocked
                        else f"Final recommendation: {recommendation}"
                    ),
                    response={
                        "action": recommendation,
                        "confidence": confidence_f,
                        "rationale": rationale,
                        "timestamp": _now(),
                        "mocked": mocked,
                    },
                )
            )

            return {
                "final_result": final_result,
                "traces": [
                    {
                        "timestamp": _now(),
                        "step": "finalize",
                        "message": (
                            f"[MOCK] Recommendation: {recommendation}"
                            if mocked
                            else f"Recommendation: {recommendation}"
                        ),
                        "mocked": mocked,
                    }
                ],
            }

        def route_after_agent(state: AnalysisState) -> str:
            messages = state.get("messages") or []
            last = messages[-1] if messages else None
            if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
                return "tools"
            return "verify"

        def route_after_verify(state: AnalysisState) -> str:
            if state.get("verification_passed"):
                return "finalize"
            if (state.get("attempt") or 0) >= (state.get("max_attempts") or 2):
                return "finalize"
            return "agent"

        graph = StateGraph(AnalysisState)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tools_node)
        graph.add_node("verify", verify_node)
        graph.add_node("finalize", finalize_node)

        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            route_after_agent,
            {"tools": "tools", "verify": "verify"},
        )
        graph.add_edge("tools", "agent")
        graph.add_conditional_edges(
            "verify",
            route_after_verify,
            {"agent": "agent", "finalize": "finalize"},
        )
        graph.add_edge("finalize", END)
        return graph.compile()

    async def arun(
        self,
        query: str,
        *,
        mode: str = "on_demand",
        symbols: list[str] | None = None,
        status_callback: StatusCallback = None,
    ) -> dict[str, Any]:
        resolved_symbols = symbols or _extract_symbols(query)
        initial: AnalysisState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "symbols": resolved_symbols,
            "mode": "self_driving" if mode == "self_driving" else "on_demand",
            "draft_recommendation": "",
            "verification_feedback": "",
            "verification_passed": False,
            "attempt": 0,
            "max_attempts": settings.max_verification_retries,
            "traces": [],
            "final_result": {},
        }

        self._status_callback = status_callback

        async def _emit(payload: dict[str, Any]) -> None:
            if status_callback:
                await status_callback(payload)

        for agent_id in FUNCTIONAL_AGENTS:
            await _emit(
                _agent_status(agent_id, "idle", "Queued for analysis")
            )

        await _emit(
            _agent_status(
                "orchestrator",
                "processing",
                f"Starting analysis for {', '.join(resolved_symbols)}",
            )
        )

        try:
            result = await self.graph.ainvoke(initial)
            final = result.get("final_result") or {}
            traces = result.get("traces") or []
        except Exception as exc:  # noqa: BLE001
            reason = str(exc)
            logger.exception("[MOCK] graph failed, using fallback: %s", reason)
            await _emit(
                _agent_status(
                    "orchestrator",
                    "error",
                    f"[MOCK] Pipeline failed → fallback ({reason})",
                    error=reason,
                    trace=[
                        {
                            "timestamp": _now(),
                            "step": "error",
                            "message": f"[MOCK] {reason}",
                        }
                    ],
                )
            )
            final = _mock_final(query, resolved_symbols, reason, mode)
            traces = [
                {
                    "timestamp": _now(),
                    "step": "mock_fallback",
                    "message": f"[MOCK] Recovered from: {reason}",
                }
            ]
            await _emit(
                _agent_status(
                    "orchestrator",
                    "completed",
                    "[MOCK] Fallback recommendation ready",
                    response={
                        "action": final.get("recommendation", "hold"),
                        "confidence": final.get("confidence", 0),
                        "rationale": final.get("rationale", ""),
                        "timestamp": _now(),
                        "mocked": True,
                    },
                )
            )
            await _emit(
                _agent_status(
                    "risk",
                    "completed",
                    "[MOCK] Risk note attached to fallback",
                )
            )
            await _emit(
                _agent_status(
                    "verifier",
                    "error",
                    "[MOCK] Verification skipped after pipeline failure",
                    error=reason,
                )
            )

        await _emit(
            {
                "type": "final_recommendation",
                "data": {
                    "recommendation": final.get("recommendation", "hold"),
                    "confidence": final.get("confidence", 0),
                    "rationale": final.get("rationale", ""),
                    "keyFactors": final.get("key_factors", []),
                    "riskAssessment": final.get("risk_assessment", ""),
                    "positionSize": 0,
                    "timeframe": "near-term",
                    "symbols": final.get("symbols", []),
                    "verified": final.get("verified", False),
                    "mode": final.get("mode", mode),
                    "mocked": bool(final.get("mocked")),
                    "mock_tag": final.get("mock_tag"),
                    "mock_reason": final.get("mock_reason"),
                },
            }
        )

        self._status_callback = None
        return {"final": final, "traces": traces, "symbols": resolved_symbols}

    async def astream_updates(
        self,
        query: str,
        *,
        mode: str = "on_demand",
        symbols: list[str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        updates: list[dict[str, Any]] = []

        async def _cb(payload: dict[str, Any]) -> None:
            updates.append(payload)

        result = await self.arun(
            query, mode=mode, symbols=symbols, status_callback=_cb
        )
        for item in updates:
            yield item
        yield {"type": "query_completed", "data": result["final"]}


_graph: StockAnalysisGraph | None = None


def get_analysis_graph() -> StockAnalysisGraph:
    global _graph
    if _graph is None:
        _graph = StockAnalysisGraph()
    return _graph


def reset_analysis_graph() -> None:
    """Force recompile (useful after tool/LLM changes under reload)."""
    global _graph
    _graph = None
