"""LangGraph state for stock analysis loops."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class AnalysisState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    symbols: list[str]
    mode: Literal["on_demand", "self_driving"]
    draft_recommendation: str
    verification_feedback: str
    verification_passed: bool
    attempt: int
    max_attempts: int
    traces: Annotated[list[dict[str, Any]], operator.add]
    final_result: dict[str, Any]
