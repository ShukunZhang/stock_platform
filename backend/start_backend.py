#!/usr/bin/env python3
"""Backend startup script that properly sets up the Python path."""

import sys
from pathlib import Path

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

if __name__ == "__main__":
    import uvicorn

    print("Starting LangGraph Stock Analysis Backend...")
    print(f"Working directory: {current_dir}")

    uvicorn.run(
        "web_ui.backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
