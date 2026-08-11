"""
Stock Analysis Web UI — FastAPI backend.

Uses LangGraph agent + verification loops, plus an optional self-driving
event loop for interval price tracking.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from tradingagents.loops.self_driving import self_driving_loop
from tradingagents.runner import analysis_runner
from tradingagents.tools.market_providers import (
    fetch_quote,
    fetch_quotes,
    format_market_cap,
    format_volume,
)
from web_ui.backend.config import settings, setup_directories
from web_ui.backend.error_handlers import log_error, setup_error_handlers
from web_ui.backend.portfolio_manager import PortfolioFileManager
from web_ui.backend.user_profile import user_profile_store
from web_ui.backend.websocket_manager import MessageType, WebSocketManager

setup_directories()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format,
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="LangGraph stock analysis API with self-driving price tracking",
    version="2.0.0",
    debug=settings.debug,
)
setup_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

websocket_manager = WebSocketManager(
    max_connections=settings.websocket_max_connections,
    ping_interval=settings.websocket_ping_interval,
)
portfolio_manager = PortfolioFileManager()
shutdown_event: asyncio.Event | None = None


class SelfDrivingUpdate(BaseModel):
    enabled: Optional[bool] = None
    symbols: Optional[List[str]] = None
    interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    analyze_on_tick: Optional[bool] = None


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    watchlist: Optional[List[str]] = None
    chat_history: Optional[List[Dict[str, Any]]] = None
    agent_strategies: Optional[Dict[str, str]] = None


class ChatAppend(BaseModel):
    messages: List[Dict[str, Any]]


async def broadcast_message(message: dict[str, Any]) -> None:
    await websocket_manager.broadcast(message)


@app.on_event("startup")
async def startup_event() -> None:
    global shutdown_event
    shutdown_event = asyncio.Event()
    logger.info("Starting LangGraph stock analysis backend...")

    await analysis_runner.initialize()
    portfolio_manager.initialize()
    self_driving_loop.set_broadcast(broadcast_message)

    def _signal_handler(signum: int, _frame: Any) -> None:
        logger.info("Received signal %s", signum)
        if shutdown_event:
            shutdown_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    logger.info("Backend startup completed")


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await self_driving_loop.stop()
    await websocket_manager.disconnect_all()
    logger.info("Backend shutdown completed")


@app.get("/health")
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "self_driving": self_driving_loop.get_status(),
    }


@app.get("/api/status")
async def get_system_status() -> dict[str, Any]:
    return {
        "status": "operational",
        "engine": "langgraph",
        "connected_clients": websocket_manager.get_connection_count(),
        "self_driving": self_driving_loop.get_status(),
        "portfolio_status": portfolio_manager.get_status(),
        "environment": {
            "deepseek_api_key": bool(os.getenv("DEEPSEEK_API_KEY")),
            "fmp_api_key": bool(os.getenv("FMP_API_KEY")),
            "alpha_vantage_api_key": bool(os.getenv("ALPHA_VANTAGE_API_KEY")),
            "marketaux_api_key": bool(os.getenv("MARKETAUX_API_KEY")),
            "yahoo_fallback": True,
        },
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/profile")
async def get_profile(user_id: str = "default") -> dict[str, Any]:
    return user_profile_store.get(user_id)


@app.put("/api/profile")
async def put_profile(body: ProfileUpdate, user_id: str = "default") -> dict[str, Any]:
    return user_profile_store.update(body.model_dump(exclude_none=True), user_id=user_id)


@app.post("/api/profile/chat")
async def append_chat(body: ChatAppend, user_id: str = "default") -> dict[str, Any]:
    return user_profile_store.append_chat(body.messages, user_id=user_id)


@app.get("/api/quotes")
async def get_quotes(symbols: str = "") -> dict[str, Any]:
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        profile = user_profile_store.get("default")
        symbol_list = list(profile.get("watchlist") or [])
    quotes = fetch_quotes(symbol_list)
    # UI-friendly enriched payload
    items = []
    for sym, q in quotes.items():
        items.append(
            {
                **q,
                "ticker": sym,
                "vol": format_volume(q.get("volume")),
                "mktcap": format_market_cap(q.get("market_cap")),
                "pct": q.get("change_percent"),
            }
        )
    return {"quotes": quotes, "items": items, "count": len(items)}


@app.get("/api/quote/{symbol}")
async def get_one_quote(symbol: str) -> dict[str, Any]:
    q = fetch_quote(symbol)
    return {
        **q,
        "ticker": q.get("symbol"),
        "vol": format_volume(q.get("volume")),
        "mktcap": format_market_cap(q.get("market_cap")),
        "pct": q.get("change_percent"),
    }


@app.get("/api/self-driving")
async def get_self_driving() -> dict[str, Any]:
    return self_driving_loop.get_status()


@app.post("/api/self-driving")
async def update_self_driving(body: SelfDrivingUpdate) -> dict[str, Any]:
    return await self_driving_loop.update_config(
        enabled=body.enabled,
        symbols=body.symbols,
        interval_minutes=body.interval_minutes,
        analyze_on_tick=body.analyze_on_tick,
    )


@app.post("/api/self-driving/tick")
async def force_self_driving_tick() -> dict[str, Any]:
    return await self_driving_loop.run_once()


@app.get("/api/portfolio")
async def get_portfolio() -> dict[str, Any]:
    try:
        return portfolio_manager.get_portfolio_data()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/portfolio/trade")
async def execute_trade(trade_data: Dict[str, Any]) -> dict[str, Any]:
    try:
        result = portfolio_manager.execute_trade(trade_data)
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        await websocket_manager.broadcast(
            {
                "type": MessageType.PORTFOLIO_UPDATE,
                "data": result["updated_portfolio"],
                "message": (
                    f"Trade executed: {trade_data['action']} "
                    f"{trade_data['quantity']} shares of {trade_data['symbol']}"
                ),
            }
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    user_agent = websocket.headers.get("user-agent")
    client_ip = websocket.client.host if websocket.client else None
    client_id = await websocket_manager.connect(websocket, user_agent, client_ip)

    await websocket_manager.send_personal_message(
        {
            "type": MessageType.CONNECTION_ESTABLISHED,
            "message": "Connected to LangGraph stock analysis backend",
            "data": {
                "client_id": client_id,
                "engine": "langgraph",
                "self_driving": self_driving_loop.get_status(),
            },
        },
        client_id,
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = __import__("json").loads(raw)
            except Exception:  # noqa: BLE001
                await websocket_manager.send_error(
                    "Invalid JSON message",
                    error_code="BAD_JSON",
                    client_id=client_id,
                )
                continue

            msg_type = message.get("type")
            if msg_type == "stock_query":
                await handle_stock_query(message.get("content", ""), client_id)
            elif msg_type == "portfolio_request":
                await handle_portfolio_request(client_id)
            elif msg_type == "self_driving_update":
                data = message.get("data") or {}
                status = await self_driving_loop.update_config(
                    enabled=data.get("enabled"),
                    symbols=data.get("symbols"),
                    interval_minutes=data.get("interval_minutes"),
                    analyze_on_tick=data.get("analyze_on_tick"),
                )
                await websocket_manager.send_personal_message(
                    {
                        "type": "self_driving_status",
                        "message": "Self-driving config updated",
                        "data": status,
                    },
                    client_id,
                )
            elif msg_type == "self_driving_status":
                await websocket_manager.send_personal_message(
                    {
                        "type": "self_driving_status",
                        "data": self_driving_loop.get_status(),
                    },
                    client_id,
                )
            elif msg_type == "ping":
                await websocket_manager.send_personal_message(
                    {"type": "pong", "timestamp": datetime.now().isoformat()},
                    client_id,
                )
            else:
                handled = await websocket_manager.handle_message(message, client_id)
                if not handled:
                    await websocket_manager.send_error(
                        f"Unknown message type: {msg_type}",
                        error_code="UNKNOWN_TYPE",
                        client_id=client_id,
                    )
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
    except Exception as exc:  # noqa: BLE001
        log_error(exc, f"WebSocket client {client_id}")
        websocket_manager.disconnect(client_id)


async def handle_stock_query(query: str, client_id: str) -> None:
    if not query or not str(query).strip():
        await websocket_manager.send_personal_message(
            {
                "type": "agent_status",
                "data": {
                    "agent_name": "orchestrator",
                    "status": "error",
                    "message": "Query content is required",
                    "error": "EMPTY_QUERY",
                },
            },
            client_id,
        )
        return

    # Status belongs on agents panel — not chat
    await websocket_manager.send_personal_message(
        {
            "type": "agent_status",
            "data": {
                "agent_name": "orchestrator",
                "status": "processing",
                "message": f"Analyzing: {query}",
            },
        },
        client_id,
    )
    await websocket_manager.send_personal_message(
        {
            "type": "query_started",
            "data": {"query": query},
        },
        client_id,
    )

    async def status_callback(payload: dict[str, Any]) -> None:
        if client_id not in websocket_manager.active_connections:
            return
        await websocket_manager.send_personal_message(payload, client_id)

    try:
        async for update in analysis_runner.analyze_streaming(
            query, status_callback=status_callback
        ):
            if client_id not in websocket_manager.active_connections:
                break
            if update.get("type") == "query_completed":
                await websocket_manager.send_personal_message(
                    {
                        "type": MessageType.QUERY_COMPLETED,
                        "data": update.get("data"),
                    },
                    client_id,
                )
    except Exception as exc:  # noqa: BLE001
        # Recover with mock so testing is not blocked; surface error on agent status
        log_error(exc, f"stock_query for {client_id}")
        reason = str(exc)
        await websocket_manager.send_personal_message(
            {
                "type": "agent_status",
                "data": {
                    "agent_name": "orchestrator",
                    "status": "error",
                    "message": f"[MOCK] Live call failed → fallback ({reason})",
                    "error": reason,
                },
            },
            client_id,
        )
        await websocket_manager.send_personal_message(
            {
                "type": "final_recommendation",
                "data": {
                    "recommendation": "hold",
                    "confidence": 0.4,
                    "rationale": (
                        f"[MOCK] Analysis recovered after error: {reason}. "
                        "This is a fallback result for local testing only."
                    ),
                    "keyFactors": ["[MOCK] Live pipeline failed"],
                    "riskAssessment": "[MOCK] Do not use for real trading.",
                    "positionSize": 0,
                    "timeframe": "near-term",
                    "symbols": [],
                    "verified": False,
                    "mode": "on_demand",
                    "mocked": True,
                    "mock_tag": "[MOCK]",
                    "mock_reason": reason,
                },
            },
            client_id,
        )
        await websocket_manager.send_personal_message(
            {
                "type": MessageType.QUERY_COMPLETED,
                "data": {"mocked": True, "mock_reason": reason},
            },
            client_id,
        )


async def handle_portfolio_request(client_id: str) -> None:
    try:
        portfolio_data = portfolio_manager.get_portfolio_data()
        await websocket_manager.send_personal_message(
            {
                "type": MessageType.PORTFOLIO_UPDATE,
                "data": portfolio_data,
                "message": "Portfolio data retrieved successfully",
            },
            client_id,
        )
    except Exception as exc:  # noqa: BLE001
        await websocket_manager.send_error(
            f"Error retrieving portfolio data: {exc}",
            error_code="PORTFOLIO_REQUEST_ERROR",
            client_id=client_id,
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web_ui.backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
