"""Public runner facade for on-demand and self-driving analysis."""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Optional

from tradingagents.graph.workflow import get_analysis_graph

StatusCallback = Optional[Callable]


class AnalysisRunner:
    """Thin facade used by the FastAPI backend."""

    def __init__(self) -> None:
        self.initialized = False
        self.name = "langgraph_manager"

    async def initialize(self) -> None:
        # Lazy-compile graph on first use so missing API keys fail at request time
        self.initialized = True

    async def analyze_streaming(
        self,
        query: str,
        *,
        mode: str = "on_demand",
        symbols: list[str] | None = None,
        status_callback: StatusCallback = None,
    ) -> AsyncIterator[dict[str, Any]]:
        graph = get_analysis_graph()
        if status_callback:
            result = await graph.arun(
                query, mode=mode, symbols=symbols, status_callback=status_callback
            )
            yield {"type": "query_completed", "data": result["final"]}
            return

        async for update in graph.astream_updates(query, mode=mode, symbols=symbols):
            yield update


analysis_runner = AnalysisRunner()
