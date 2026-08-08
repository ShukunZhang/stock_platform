"""Persistent user profile: chat history, watchlist, agent strategies."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_STRATEGIES: dict[str, str] = {
    "orchestrator": "Route each query to the right specialists, then synthesize a clear buy/sell/hold.",
    "market_data": "Prioritize latest price, volume, and short-term momentum from live quotes.",
    "fundamentals": "Focus on valuation multiples, growth, margins, and balance-sheet quality.",
    "technical": "Use SMA/EMA/RSI and trend structure; avoid overtrading choppy ranges.",
    "sentiment": "Weigh news tone lightly unless there is a clear catalyst or risk event.",
    "risk": "Prefer capital preservation; flag high drawdown and concentration risk.",
    "verifier": "Reject drafts that lack evidence, confidence, or a clear recommendation.",
}

DEFAULT_WATCHLIST = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL"]


class UserProfileStore:
    def __init__(self, data_dir: str | Path = "data/user_profiles") -> None:
        self.root = Path(data_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, user_id: str) -> Path:
        safe = "".join(c for c in user_id if c.isalnum() or c in ("-", "_")) or "default"
        return self.root / f"{safe}.json"

    def _default(self, user_id: str) -> dict[str, Any]:
        return {
            "user_id": user_id,
            "display_name": "Trader",
            "watchlist": list(DEFAULT_WATCHLIST),
            "chat_history": [],
            "agent_strategies": dict(DEFAULT_STRATEGIES),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get(self, user_id: str = "default") -> dict[str, Any]:
        path = self._path(user_id)
        with self._lock:
            if not path.exists():
                profile = self._default(user_id)
                path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
                return profile
            profile = json.loads(path.read_text(encoding="utf-8"))
            # ensure keys exist for older files
            profile.setdefault("watchlist", list(DEFAULT_WATCHLIST))
            profile.setdefault("chat_history", [])
            strategies = profile.setdefault("agent_strategies", {})
            for key, value in DEFAULT_STRATEGIES.items():
                strategies.setdefault(key, value)
            profile.setdefault("display_name", "Trader")
            return profile

    def save(self, profile: dict[str, Any], user_id: str = "default") -> dict[str, Any]:
        path = self._path(user_id)
        with self._lock:
            profile = dict(profile)
            profile["user_id"] = user_id
            profile["updated_at"] = datetime.now(timezone.utc).isoformat()
            # cap chat history
            history = profile.get("chat_history") or []
            if len(history) > 200:
                profile["chat_history"] = history[-200:]
            path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
            return profile

    def update(self, patch: dict[str, Any], user_id: str = "default") -> dict[str, Any]:
        profile = self.get(user_id)
        if "display_name" in patch and patch["display_name"]:
            profile["display_name"] = str(patch["display_name"])[:80]
        if "watchlist" in patch and isinstance(patch["watchlist"], list):
            cleaned = []
            for item in patch["watchlist"]:
                sym = str(item).upper().strip()
                if sym and sym not in cleaned:
                    cleaned.append(sym)
            profile["watchlist"] = cleaned[:30]
        if "chat_history" in patch and isinstance(patch["chat_history"], list):
            profile["chat_history"] = patch["chat_history"][-200:]
        if "agent_strategies" in patch and isinstance(patch["agent_strategies"], dict):
            strategies = profile.setdefault("agent_strategies", {})
            for key, value in patch["agent_strategies"].items():
                if key in DEFAULT_STRATEGIES and isinstance(value, str):
                    strategies[key] = value[:2000]
        return self.save(profile, user_id)

    def append_chat(self, messages: list[dict[str, Any]], user_id: str = "default") -> dict[str, Any]:
        profile = self.get(user_id)
        history = profile.get("chat_history") or []
        history.extend(messages)
        profile["chat_history"] = history[-200:]
        return self.save(profile, user_id)


user_profile_store = UserProfileStore()
