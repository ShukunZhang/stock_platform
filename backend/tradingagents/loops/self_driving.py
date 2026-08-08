"""Self-driving event loop (loop engineering level 3).

When enabled, periodically fetches prices and runs the LangGraph analysis
workflow for watched symbols — without requiring a manual user query.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from tradingagents.config import settings
from tradingagents.graph.workflow import get_analysis_graph
from tradingagents.tools.market_providers import fetch_quote

logger = logging.getLogger(__name__)

BroadcastFn = Callable[[dict[str, Any]], Awaitable[None]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SelfDrivingConfig:
    enabled: bool = False
    symbols: list[str] = field(default_factory=lambda: ["AAPL"])
    interval_minutes: int = 5
    analyze_on_tick: bool = True


@dataclass
class SelfDrivingStatus:
    enabled: bool
    symbols: list[str]
    interval_minutes: int
    analyze_on_tick: bool
    running: bool
    last_tick_at: Optional[str]
    next_tick_at: Optional[str]
    last_prices: dict[str, Any]
    tick_count: int
    last_error: Optional[str]


class SelfDrivingLoop:
    """Cron-style event loop that wakes the agent on a user-defined interval."""

    def __init__(self, broadcast: Optional[BroadcastFn] = None) -> None:
        self._broadcast = broadcast
        self._config = SelfDrivingConfig(
            interval_minutes=settings.default_track_interval_minutes
        )
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._lock = asyncio.Lock()
        self._last_tick_at: str | None = None
        self._next_tick_at: str | None = None
        self._last_prices: dict[str, Any] = {}
        self._tick_count = 0
        self._last_error: str | None = None

    def set_broadcast(self, broadcast: BroadcastFn) -> None:
        self._broadcast = broadcast

    def get_status(self) -> dict[str, Any]:
        status = SelfDrivingStatus(
            enabled=self._config.enabled,
            symbols=list(self._config.symbols),
            interval_minutes=self._config.interval_minutes,
            analyze_on_tick=self._config.analyze_on_tick,
            running=self._task is not None and not self._task.done(),
            last_tick_at=self._last_tick_at,
            next_tick_at=self._next_tick_at,
            last_prices=dict(self._last_prices),
            tick_count=self._tick_count,
            last_error=self._last_error,
        )
        return asdict(status)

    async def update_config(
        self,
        *,
        enabled: Optional[bool] = None,
        symbols: Optional[list[str]] = None,
        interval_minutes: Optional[int] = None,
        analyze_on_tick: Optional[bool] = None,
    ) -> dict[str, Any]:
        async with self._lock:
            if symbols is not None:
                cleaned = [s.strip().upper() for s in symbols if s and s.strip()]
                if cleaned:
                    self._config.symbols = cleaned
            if interval_minutes is not None:
                self._config.interval_minutes = max(1, int(interval_minutes))
            if analyze_on_tick is not None:
                self._config.analyze_on_tick = bool(analyze_on_tick)
            if enabled is not None:
                self._config.enabled = bool(enabled)

            if self._config.enabled:
                await self._ensure_running_locked()
            else:
                await self._stop_locked()

        status = self.get_status()
        await self._emit(
            {
                "type": "self_driving_status",
                "message": "Self-driving "
                + ("enabled" if status["enabled"] else "disabled"),
                "data": status,
            }
        )
        return status

    async def start(self) -> dict[str, Any]:
        return await self.update_config(enabled=True)

    async def stop(self) -> dict[str, Any]:
        return await self.update_config(enabled=False)

    async def run_once(self) -> dict[str, Any]:
        return await self._tick()

    async def _ensure_running_locked(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="self-driving-loop")

    async def _stop_locked(self) -> None:
        self._config.enabled = False
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._next_tick_at = None

    async def _run_loop(self) -> None:
        logger.info(
            "Self-driving loop started symbols=%s interval=%sm",
            self._config.symbols,
            self._config.interval_minutes,
        )
        try:
            while self._config.enabled and not self._stop_event.is_set():
                try:
                    await self._tick()
                except Exception as exc:  # noqa: BLE001
                    self._last_error = str(exc)
                    logger.exception("Self-driving tick failed")
                    await self._emit(
                        {
                            "type": "error",
                            "message": f"Self-driving tick failed: {exc}",
                            "data": {"source": "self_driving"},
                        }
                    )

                wait_seconds = max(60, int(self._config.interval_minutes) * 60)
                self._next_tick_at = datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + wait_seconds,
                    tz=timezone.utc,
                ).isoformat()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=wait_seconds
                    )
                    break
                except asyncio.TimeoutError:
                    continue
        finally:
            logger.info("Self-driving loop stopped")
            self._next_tick_at = None

    async def _tick(self) -> dict[str, Any]:
        symbols = list(self._config.symbols)
        prices: dict[str, Any] = {}
        for symbol in symbols:
            prices[symbol] = fetch_quote(symbol)

        self._last_prices = prices
        self._last_tick_at = _now()
        self._tick_count += 1
        self._last_error = None

        await self._emit(
            {
                "type": "self_driving_tick",
                "message": f"Tracked {', '.join(symbols)}",
                "data": {
                    "prices": prices,
                    "tick_count": self._tick_count,
                    "timestamp": self._last_tick_at,
                },
            }
        )

        analysis: dict[str, Any] | None = None
        if self._config.analyze_on_tick:
            query = (
                "Self-driving monitor tick. Review the latest prices for "
                f"{', '.join(symbols)} and recommend buy, sell, or hold for each. "
                "Be concise and cite the latest price numbers."
            )

            async def _cb(payload: dict[str, Any]) -> None:
                # Tag updates so UI can distinguish autonomous runs
                data = dict(payload.get("data") or {})
                data["self_driving"] = True
                await self._emit({**payload, "data": data})

            graph = get_analysis_graph()
            analysis = await graph.arun(
                query,
                mode="self_driving",
                symbols=symbols,
                status_callback=_cb,
            )

        return {
            "prices": prices,
            "analysis": analysis,
            "timestamp": self._last_tick_at,
            "tick_count": self._tick_count,
        }

    async def _emit(self, message: dict[str, Any]) -> None:
        if not self._broadcast:
            return
        payload = {
            "timestamp": _now(),
            **message,
        }
        await self._broadcast(payload)


self_driving_loop = SelfDrivingLoop()
