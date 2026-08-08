# Stock Platform

LangGraph stock analysis with a React Web UI.

```
stock_platform/
├── backend/     # FastAPI + LangGraph agents + self-driving loop
└── frontend/    # Vite + React dashboard
```

## Backend

```powershell
cd backend
python -m pip install -r requirements.txt
copy .env.example .env   # set DEEPSEEK_API_KEY, FMP_API_KEY, etc.
python start_backend.py
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

## Frontend

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

- UI: http://localhost:8443  

## Features

- Functional specialist agents (Orchestrator, Market Data, Fundamentals, Technical, Sentiment, Risk, Verifier)
- Self-driving price tracking loop (user interval)
- User profile: chat history, watchlist, per-agent strategies
- Market data via FMP → Alpha Vantage → `[MOCK]` fallback
