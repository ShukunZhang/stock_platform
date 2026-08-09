"""Unit tests for UserProfileStore."""

from __future__ import annotations

import pytest

from web_ui.backend.user_profile import (
    DEFAULT_STRATEGIES,
    DEFAULT_WATCHLIST,
    UserProfileStore,
)


pytestmark = pytest.mark.unit


@pytest.fixture
def store(tmp_data_dir) -> UserProfileStore:
    return UserProfileStore(data_dir=tmp_data_dir / "profiles")


class TestUserProfileStore:
    def test_get_creates_default_profile(self, store: UserProfileStore):
        profile = store.get("alice")
        assert profile["user_id"] == "alice"
        assert profile["display_name"] == "Trader"
        assert profile["watchlist"] == DEFAULT_WATCHLIST
        assert profile["agent_strategies"]["orchestrator"] == DEFAULT_STRATEGIES["orchestrator"]
        assert profile["chat_history"] == []

    def test_path_sanitizes_user_id(self, store: UserProfileStore):
        path = store._path("evil/../user!")
        assert path.name == "eviluser.json"
        assert "/" not in path.name

    def test_update_display_name_and_watchlist(self, store: UserProfileStore):
        updated = store.update(
            {
                "display_name": "Ada",
                "watchlist": ["aapl", "AAPL", " msft ", ""],
            },
            user_id="u1",
        )
        assert updated["display_name"] == "Ada"
        assert updated["watchlist"] == ["AAPL", "MSFT"]

    def test_watchlist_capped_at_30(self, store: UserProfileStore):
        tickers = [f"T{i:02d}" for i in range(40)]
        updated = store.update({"watchlist": tickers}, user_id="u2")
        assert len(updated["watchlist"]) == 30

    def test_update_agent_strategies_only_known_keys(self, store: UserProfileStore):
        updated = store.update(
            {
                "agent_strategies": {
                    "risk": "Be cautious",
                    "unknown_agent": "ignored",
                    "verifier": 123,  # invalid type ignored
                }
            },
            user_id="u3",
        )
        assert updated["agent_strategies"]["risk"] == "Be cautious"
        assert "unknown_agent" not in updated["agent_strategies"]
        assert updated["agent_strategies"]["verifier"] == DEFAULT_STRATEGIES["verifier"]

    def test_append_chat_and_cap(self, store: UserProfileStore):
        msgs = [{"role": "user", "text": f"m{i}"} for i in range(210)]
        profile = store.append_chat(msgs, user_id="u4")
        assert len(profile["chat_history"]) == 200
        assert profile["chat_history"][0]["text"] == "m10"
        assert profile["chat_history"][-1]["text"] == "m209"

    def test_save_persists_and_reload(self, store: UserProfileStore):
        profile = store.get("persist")
        profile["display_name"] = "Bob"
        store.save(profile, "persist")
        reloaded = store.get("persist")
        assert reloaded["display_name"] == "Bob"
