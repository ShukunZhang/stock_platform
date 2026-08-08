# Backend — LangGraph Stock Analysis

FastAPI server with LangGraph agent loops and self-driving price tracking.

## Setup

```powershell
python -m pip install -r requirements.txt
copy .env.example .env
python start_backend.py
```

## Layout

```
backend/
├── tradingagents/     # graph, tools, loops, llm
├── web_ui/backend/    # FastAPI app
├── start_backend.py
└── requirements.txt
```

## Env

See `.env.example` for `DEEPSEEK_API_KEY`, `FMP_API_KEY`, `ALPHA_VANTAGE_API_KEY`.
