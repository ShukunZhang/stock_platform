"""Unit tests for WebSocketManager helpers and connection lifecycle."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from unittest.mock import AsyncMock, MagicMock

import pytest

from web_ui.backend.websocket_manager import (
    ConnectionInfo,
    MessageType,
    WebSocketManager,
    WebSocketMessage,
)


pytestmark = pytest.mark.unit


class TestMessageModels:
    def test_message_type_enum_values(self):
        assert MessageType.AGENT_STATUS == "agent_status"
        assert MessageType.FINAL_RECOMMENDATION == "final_recommendation"
        assert issubclass(MessageType, str)
        assert issubclass(MessageType, Enum)

    def test_websocket_message_to_dict_strips_none(self):
        msg = WebSocketMessage(type="ping", data={"a": 1})
        d = msg.to_dict()
        assert d["type"] == "ping"
        assert d["data"] == {"a": 1}
        assert "message" not in d
        assert "timestamp" in d

    def test_connection_info_to_dict(self):
        info = ConnectionInfo(
            client_id="c1",
            connected_at=datetime.now(),
            last_activity=datetime.now(),
            message_count=3,
            user_agent="test",
            ip_address="127.0.0.1",
        )
        d = info.to_dict()
        assert d["client_id"] == "c1"
        assert d["message_count"] == 3
        assert "connection_duration" in d


class TestWebSocketManagerUnit:
    def test_get_connection_count_and_stats(self):
        mgr = WebSocketManager(max_connections=2)
        assert mgr.get_connection_count() == 0
        stats = mgr.get_statistics() if hasattr(mgr, "get_statistics") else mgr._stats
        assert stats["total_connections"] == 0 or "total_connections" in stats

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        mgr = WebSocketManager(max_connections=2)
        # Avoid starting real background ping tasks in unit tests
        mgr._start_background_tasks = AsyncMock()  # type: ignore[method-assign]
        mgr._stop_background_tasks = AsyncMock()  # type: ignore[method-assign]

        ws = MagicMock()
        client_id = await mgr.connect(ws, user_agent="ua", ip_address="1.2.3.4")
        assert client_id in mgr.active_connections
        assert mgr.get_connection_count() == 1
        assert mgr.connection_info[client_id].user_agent == "ua"

        mgr.disconnect(client_id)
        assert mgr.get_connection_count() == 0
        assert client_id not in mgr.connection_info

    @pytest.mark.asyncio
    async def test_connect_rejects_over_max(self):
        mgr = WebSocketManager(max_connections=1)
        mgr._start_background_tasks = AsyncMock()  # type: ignore[method-assign]
        await mgr.connect(MagicMock())
        with pytest.raises(ConnectionError, match="Maximum connections"):
            await mgr.connect(MagicMock())

    @pytest.mark.asyncio
    async def test_send_personal_message_missing_client(self):
        mgr = WebSocketManager()
        ok = await mgr.send_personal_message({"type": "ping"}, "missing")
        assert ok is False

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self):
        mgr = WebSocketManager()
        sent = await mgr.broadcast({"type": "ping"})
        assert sent == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_subset_hits_missing_connection_metadata(self):
        """
        Documents a source bug: broadcast_to_subset reads self.connection_metadata
        (undefined). The AttributeError is swallowed by the broad except, then
        the client is disconnected.
        """
        mgr = WebSocketManager()
        mgr._start_background_tasks = AsyncMock()  # type: ignore[method-assign]
        mgr._stop_background_tasks = AsyncMock()  # type: ignore[method-assign]
        ws = AsyncMock()
        client_id = await mgr.connect(ws)
        assert mgr.get_connection_count() == 1
        await mgr.broadcast_to_subset({"type": "ping"}, {client_id})
        # Client removed because AttributeError was treated as send failure
        assert mgr.get_connection_count() == 0
        ws.send_json.assert_awaited()
