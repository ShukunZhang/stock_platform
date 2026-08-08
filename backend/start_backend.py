#!/usr/bin/env python3
"""Backend startup script that properly sets up the Python path."""

import os
import sys
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("UVICORN_RELOAD", "false").lower() == "true"

    print("Starting LangGraph Stock Analysis Backend...")
    print(f"Working directory: {current_dir}")
    print(f"Port: {port}")

    uvicorn.run(
        "web_ui.backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
