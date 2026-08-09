"""Unit tests for SelfDrivingLoop."""

from __future__ import annotations

import pytest

from tradingagents.loops.self_driving import SelfDrivingConfig, SelfDrivingLoop, SelfDrivingStatus


pytestmark = pytest.mark.unit


@pytest.fixture
def loop() -> SelfDrivingLoop:
    return SelfDrivingLoop()


class TestSelfDrivingConfigAndStatus:
    def test_default_config(self):
        cfg = SelfDrivingConfig()
        assert cfg.enabled is False
        assert cfg.symbols == ["AAPL"]
        assert cfg.analyze_on_tick is True

    def test_get_status_shape(self, loop: SelfDrivingLoop):
        status = loop.get_status()
        assert status["enabled"] is False
        assert status["running"] is False
        assert status["tick_count"] == 0
        assert status["last_error"] is None
        assert isinstance(status["symbols"], list)
        assert isinstance(status["last_prices"], dict)


class TestSelfDrivingUpdateConfig:
    @pytest.mark.asyncio
    async def test_update_symbols_and_interval(self, loop: SelfDrivingLoop):
        status = await loop.update_config(
            enabled=False,
            symbols=[" aapl ", "msft", ""],
            interval_minutes=10,
            analyze_on_tick=False,
        )
        assert status["symbols"] == ["AAPL", "MSFT"]
        assert status["interval_minutes"] == 10
        assert status["analyze_on_tick"] is False
        assert status["enabled"] is False

    @pytest.mark.asyncio
    async def test_interval_clamped_to_at_least_one(self, loop: SelfDrivingLoop):
        status = await loop.update_config(interval_minutes=0)
        assert status["interval_minutes"] == 1

    @pytest.mark.asyncio
    async def test_empty_symbols_list_keeps_previous(self, loop: SelfDrivingLoop):
        await loop.update_config(symbols=["NVDA"])
        status = await loop.update_config(symbols=["", "  "])
        assert status["symbols"] == ["NVDA"]

    @pytest.mark.asyncio
    async def test_broadcast_on_update(self):
        messages = []

        async def broadcast(msg):
            messages.append(msg)

        loop = SelfDrivingLoop(broadcast=broadcast)
        await loop.update_config(enabled=False, symbols=["AAPL"])
        assert messages
        assert messages[-1]["type"] == "self_driving_status"
        assert "timestamp" in messages[-1]

    @pytest.mark.asyncio
    async def test_stop_via_update(self, loop: SelfDrivingLoop):
        status = await loop.stop()
        assert status["enabled"] is False
        assert status["running"] is False


class TestSelfDrivingTick:
    @pytest.mark.asyncio
    async def test_run_once_prices_only(self, clear_market_keys, monkeypatch):
        loop = SelfDrivingLoop()
        await loop.update_config(
            enabled=False,
            symbols=["AAPL"],
            analyze_on_tick=False,
        )
        result = await loop.run_once()
        assert "AAPL" in result["prices"]
        assert result["analysis"] is None
        assert result["tick_count"] == 1
        assert loop.get_status()["tick_count"] == 1

    @pytest.mark.asyncio
    async def test_run_once_with_analysis(self, clear_market_keys, monkeypatch):
        class FakeGraph:
            async def arun(self, query, *, mode, symbols, status_callback):
                await status_callback(
                    {"type": "agent_status", "data": {"agent_name": "orchestrator"}}
                )
                return {"final": {"recommendation": "hold"}, "traces": [], "symbols": symbols}

        monkeypatch.setattr(
            "tradingagents.loops.self_driving.get_analysis_graph",
            lambda: FakeGraph(),
        )
        messages = []

        async def broadcast(msg):
            messages.append(msg)

        loop = SelfDrivingLoop(broadcast=broadcast)
        await loop.update_config(
            enabled=False,
            symbols=["AAPL"],
            analyze_on_tick=True,
        )
        result = await loop.run_once()
        assert result["analysis"]["final"]["recommendation"] == "hold"
        # agent_status from analysis should be tagged self_driving
        tagged = [
            m
            for m in messages
            if m.get("type") == "agent_status"
            and (m.get("data") or {}).get("self_driving") is True
        ]
        assert tagged
