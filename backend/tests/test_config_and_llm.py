"""Unit tests for Settings and get_llm."""

from __future__ import annotations

import pytest

from tradingagents.config import Settings
from tradingagents.llm import get_llm


pytestmark = pytest.mark.unit


class TestSettings:
    def test_from_env_defaults(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
        monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
        monkeypatch.delenv("LLM_TEMPERATURE", raising=False)
        monkeypatch.delenv("MAX_VERIFICATION_RETRIES", raising=False)
        monkeypatch.delenv("DEFAULT_TRACK_INTERVAL_MINUTES", raising=False)

        s = Settings.from_env()
        assert s.deepseek_api_key == ""
        assert s.deepseek_base_url == "https://api.deepseek.com"
        assert s.deepseek_model == "deepseek-chat"
        assert s.temperature == 0.1
        assert s.max_verification_retries == 2
        assert s.default_track_interval_minutes == 5

    def test_from_env_custom_values(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
        monkeypatch.setenv("MAX_VERIFICATION_RETRIES", "4")
        monkeypatch.setenv("DEFAULT_TRACK_INTERVAL_MINUTES", "15")
        s = Settings.from_env()
        assert s.deepseek_api_key == "secret"
        assert s.deepseek_model == "deepseek-reasoner"
        assert s.temperature == 0.5
        assert s.max_verification_retries == 4
        assert s.default_track_interval_minutes == 15


class TestGetLlm:
    def test_raises_without_api_key(self, monkeypatch):
        monkeypatch.setattr(
            "tradingagents.llm.settings",
            Settings(
                deepseek_api_key="",
                deepseek_base_url="https://api.deepseek.com",
                deepseek_model="deepseek-chat",
                temperature=0.1,
                max_verification_retries=2,
                default_track_interval_minutes=5,
            ),
        )
        with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
            get_llm()

    def test_builds_chat_openai_with_key(self, monkeypatch):
        monkeypatch.setattr(
            "tradingagents.llm.settings",
            Settings(
                deepseek_api_key="k",
                deepseek_base_url="https://api.deepseek.com",
                deepseek_model="deepseek-chat",
                temperature=0.1,
                max_verification_retries=2,
                default_track_interval_minutes=5,
            ),
        )
        llm = get_llm(temperature=0)
        assert llm.temperature == 0
        model = getattr(llm, "model_name", None) or getattr(llm, "model", None)
        assert model == "deepseek-chat"
