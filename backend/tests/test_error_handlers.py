"""Unit tests for web_ui.backend.error_handlers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from web_ui.backend.error_handlers import (
    AgentException,
    PortfolioException,
    WebSocketException,
    WebUIException,
    create_error_response,
    log_error,
    setup_error_handlers,
)


pytestmark = pytest.mark.unit


class TestExceptionClasses:
    def test_webui_exception_defaults(self):
        exc = WebUIException("boom")
        assert exc.message == "boom"
        assert exc.error_code == "WEBUI_ERROR"
        assert exc.details == {}

    def test_agent_exception(self):
        exc = AgentException("fail", agent_name="orchestrator", details={"x": 1})
        assert exc.error_code == "AGENT_ERROR"
        assert exc.agent_name == "orchestrator"
        assert exc.details == {"x": 1}

    def test_portfolio_and_websocket_exceptions(self):
        p = PortfolioException("bad trade")
        assert p.error_code == "PORTFOLIO_ERROR"
        w = WebSocketException("ws down", client_id="c1")
        assert w.error_code == "WEBSOCKET_ERROR"
        assert w.client_id == "c1"


class TestCreateErrorResponse:
    def test_generic_error(self):
        resp = create_error_response(ValueError("x"), status_code=400)
        assert resp["error"] is True
        assert resp["status_code"] == 400
        assert resp["message"] == "x"
        assert resp["type"] == "ValueError"
        assert "timestamp" in resp

    def test_webui_error_includes_code_and_agent(self):
        resp = create_error_response(
            AgentException("bad", agent_name="risk"), status_code=400
        )
        assert resp["error_code"] == "AGENT_ERROR"
        assert resp["agent_name"] == "risk"

    def test_websocket_error_includes_client_id(self):
        resp = create_error_response(
            WebSocketException("bad", client_id="abc"), status_code=500
        )
        assert resp["client_id"] == "abc"

    def test_include_traceback(self):
        try:
            raise RuntimeError("tb")
        except RuntimeError as exc:
            resp = create_error_response(exc, include_traceback=True)
        assert "traceback" in resp


class TestLogAndHandlers:
    def test_log_error_does_not_raise(self, caplog):
        log_error(WebUIException("x"), context="unit", extra_data={"k": "v"})

    def test_setup_error_handlers_registers(self):
        app = FastAPI()

        @app.get("/boom")
        async def boom():
            raise AgentException("agent failed", agent_name="verifier")

        @app.get("/http")
        async def http_err():
            raise HTTPException(status_code=404, detail="missing")

        setup_error_handlers(app)
        client = TestClient(app, raise_server_exceptions=False)

        r1 = client.get("/boom")
        assert r1.status_code == 400
        assert r1.json()["error_code"] == "AGENT_ERROR"

        r2 = client.get("/http")
        assert r2.status_code == 404
        assert r2.json()["error"] is True
