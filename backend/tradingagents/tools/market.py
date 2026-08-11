"""Market data tools used by the LangGraph agent loop (FMP / Alpha Vantage / Yahoo)."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from tradingagents.tools.market_providers import (
    fetch_fundamentals,
    fetch_history,
    fetch_quote,
    fetch_technicals,
)


@tool
def get_stock_price(symbol: str) -> str:
    """Get the latest price and basic quote for a stock ticker symbol (e.g. AAPL)."""
    return json.dumps(fetch_quote(symbol))


@tool
def get_price_history(symbol: str, period: str = "1mo", interval: str = "1d") -> str:
    """Get OHLCV history for a ticker. period examples: 5d, 1mo, 3mo, 6mo, 1y."""
    limit = 30
    p = (period or "1mo").lower()
    if p in {"5d", "1w"}:
        limit = 5
    elif p in {"3mo"}:
        limit = 66
    elif p in {"6mo"}:
        limit = 132
    elif p in {"1y"}:
        limit = 252
    _ = interval  # reserved for future intraday providers
    return json.dumps(fetch_history(symbol, limit=limit))


@tool
def get_fundamentals_snapshot(symbol: str) -> str:
    """Get a compact fundamentals snapshot for a ticker."""
    return json.dumps(fetch_fundamentals(symbol))


@tool
def get_technical_snapshot(symbol: str) -> str:
    """Compute simple technical indicators from recent closes."""
    return json.dumps(fetch_technicals(symbol))


MARKET_TOOLS = [
    get_stock_price,
    get_price_history,
    get_fundamentals_snapshot,
    get_technical_snapshot,
]
