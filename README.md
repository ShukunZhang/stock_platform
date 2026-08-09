# Stock Platform

LangGraph-powered stock analysis with a real-time React dashboard. Ask natural-language questions (“Should I buy AAPL?”), watch a multi-specialist analysis pipeline stream over WebSocket, and optionally enable a self-driving loop that re-analyzes watchlist symbols on a schedule.

```
stock_platform/
├── backend/     # FastAPI + LangGraph agents + self-driving loop + portfolio
└── frontend/    # Vite + React dashboard (StockAgent UI)
```

---

## What this project can do

| Capability | Description |
|---|---|
| **Natural-language stock Q&A** | Chat asks the LangGraph pipeline for a buy / sell / hold call with confidence, rationale, key factors, and risk notes |
| **Multi-specialist agent fleet** | Orchestrator, Market Data, Fundamentals, Technical, Sentiment, Risk, Verifier — live status streamed to the UI |
| **Live & fallback market data** | Quotes, history, fundamentals, and technicals via **FMP → Alpha Vantage → `[MOCK]`** |
| **Verification loop** | Draft recommendations are graded; failed drafts retry with feedback (configurable retries) |
| **Self-driving mode** | Interval price tracking with optional full re-analysis per tick |
| **Watchlist & quotes** | Persist tickers, refresh quotes, analyze or track symbols from the UI |
| **User profile** | Display name, watchlist, chat history, per-agent strategy text |
| **Paper portfolio** | Buy/sell trades, positions, P&L metrics stored as local JSON |
| **Real-time WebSocket** | Agent status, recommendations, self-driving ticks, portfolio updates |
| **Graceful offline/dev mode** | Missing LLM or market keys fall back to tagged `[MOCK]` results so local UI still works |

---

## Agent fleet (features)

The runtime is a **single compiled LangGraph** (`StockAnalysisGraph`). Specialists are functional IDs used for status reporting and tool routing — not separate AgentScope/ReAct agent classes.

```
Query → Orchestrator (LLM + tools)
      ⇄ Tools (Market Data / Fundamentals / Technical)
      → Verifier (pass/fail rubric)
      ↺ retry Orchestrator on fail (up to N attempts)
      → Finalize (Risk + Sentiment status + final recommendation)
```

### 1. Orchestrator

- **Role:** Plan analysis, call market tools, draft and synthesize the final recommendation.
- **Model:** DeepSeek (`deepseek-chat` via OpenAI-compatible API).
- **Tools:** All market tools (`get_stock_price`, `get_price_history`, `get_fundamentals_snapshot`, `get_technical_snapshot`).
- **Output:** buy / sell / hold, confidence (0–1), rationale, key factors, risk assessment, symbols.
- **Failure mode:** On LLM errors, emits a tagged `[MOCK]` draft so the pipeline continues.

### 2. Market Data

- **Role:** Live quotes and OHLCV history.
- **Tools:**
  - `get_stock_price(symbol)` — latest price, change, volume, market cap
  - `get_price_history(symbol, period, interval)` — bars for 5d / 1mo / 3mo / 6mo / 1y
- **Providers:** FMP → Alpha Vantage → mock quotes for common tickers (AAPL, MSFT, NVDA, …)

### 3. Fundamentals

- **Role:** Valuation and financial health snapshot.
- **Tool:** `get_fundamentals_snapshot(symbol)` — PE, PB, ROE, sector/industry, debt, dividend, etc.
- **Providers:** FMP profile + key metrics → Alpha Vantage OVERVIEW → mock fundamentals

### 4. Technical

- **Role:** Derived indicators from recent closes.
- **Tool:** `get_technical_snapshot(symbol)` — SMA20, SMA50, EMA12, RSI14, trend hint (bullish / bearish / neutral)
- **Data:** Built from `fetch_history` (same provider cascade)

### 5. Sentiment

- **Role:** UI/status persona for news tone and catalysts.
- **Tools:** None in the current graph (status emitted at finalize: sentiment inferred from draft context).
- **Note:** `MARKETAUX_API_KEY` is exposed in system status but not wired to a tool yet.
- **Profile strategy:** Configurable default text for how sentiment should be weighed (stored; not injected into LLM prompts today).

### 6. Risk

- **Role:** Surface downside / stance checks in the final package.
- **Tools:** None as a separate LLM node — finalize reads `risk_assessment` from the draft and emits risk agent status.
- **Profile strategy:** Capital preservation / drawdown / concentration guidance text.

### 7. Verifier

- **Role:** Rubric grade of the draft before finalize.
- **Checks:** Concrete evidence, clear buy/sell/hold, confidence + coherent rationale, no invented data; `[MOCK]` drafts can still pass if structure is valid.
- **Behavior:** Fail → feedback → orchestrator retry until `MAX_VERIFICATION_RETRIES` (default 2). On verifier LLM failure, force-pass so the pipeline does not stall.

### 8. Self-Driving (event loop)

- **Role:** Cron-style loop independent of chat.
- **Actions:** Fetch quotes for configured symbols; optionally run full graph in `mode="self_driving"`; broadcast `self_driving_tick` / `self_driving_status` and tagged agent updates.
- **Controls:** Enable/disable, symbols, interval (minutes), analyze-on-tick, force one tick now.

---

## User-facing UI features

Single-page dashboard tabs (`frontend/`):

| Tab | Features |
|---|---|
| **Chat** | Natural-language analysis, quick prompts, streaming agent thinking, recommendation cards |
| **Watchlist** | Add/remove tickers, live quotes, analyze / track |
| **Self-drive** | Loop enable, symbols, interval, analyze-on-tick, force tick, last prices |
| **Agents** | Live fleet cards + activity logs for all specialists |
| **Profile** | Display name, watchlist, chat history, per-agent strategy text |
| **Settings** | Backend REST/WebSocket connection info |

---

## Backend API

Base URL (local): `http://localhost:8000` — OpenAPI at `/docs`.

### REST

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness + self-driving status |
| `GET` | `/api/status` | Engine, WS clients, portfolio, API key presence flags |
| `GET` / `PUT` | `/api/profile` | Load / patch user profile |
| `POST` | `/api/profile/chat` | Append chat messages |
| `GET` | `/api/quotes` | Quotes for CSV symbols or profile watchlist |
| `GET` | `/api/quote/{symbol}` | Single enriched quote |
| `GET` / `POST` | `/api/self-driving` | Status / update config |
| `POST` | `/api/self-driving/tick` | Force one self-driving tick |
| `GET` | `/api/portfolio` | Portfolio + metrics |
| `POST` | `/api/portfolio/trade` | Execute paper buy/sell |

### WebSocket `WS /ws`

**Inbound:** `stock_query`, `portfolio_request`, `self_driving_update`, `self_driving_status`, `ping`

**Outbound:** `connection_established`, `query_started`, `agent_status`, `final_recommendation`, `query_completed`, `self_driving_status`, `self_driving_tick`, `portfolio_update`, `error`, `pong`

---

## Architecture

```
Frontend (Vite/React)
    │  REST + WebSocket
    ▼
FastAPI (web_ui/backend)
    ├── AnalysisRunner → StockAnalysisGraph (LangGraph)
    │       ├── agent ⇄ tools
    │       ├── verify (retry)
    │       └── finalize
    ├── SelfDrivingLoop
    ├── UserProfileStore
    ├── PortfolioFileManager
    └── Market providers (FMP / Alpha Vantage / mock)
```

**Backend layout**

```
backend/
├── tradingagents/
│   ├── graph/          # state + StockAnalysisGraph workflow
│   ├── tools/          # LangChain tools + market_providers
│   ├── loops/          # SelfDrivingLoop
│   ├── llm.py          # DeepSeek ChatOpenAI factory
│   ├── config.py
│   └── runner.py
├── web_ui/backend/     # FastAPI app, WS, portfolio, profile
├── tests/              # Unit tests (pytest)
├── start_backend.py
└── requirements.txt
```

---

## Quick start

### Prerequisites

- Python 3.11+ recommended
- Node.js 22+ (frontend)
- Optional API keys: DeepSeek (LLM), FMP and/or Alpha Vantage (market data)

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env   # set DEEPSEEK_API_KEY, FMP_API_KEY, etc.
python start_backend.py
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

### Frontend

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

- UI: http://localhost:8443  

### Environment variables

| Variable | Purpose |
|---|---|
| `DEEPSEEK_API_KEY` | Required for live LLM analysis |
| `DEEPSEEK_BASE_URL` | Default `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | Default `deepseek-chat` |
| `LLM_TEMPERATURE` | Default `0.1` |
| `MAX_VERIFICATION_RETRIES` | Default `2` |
| `DEFAULT_TRACK_INTERVAL_MINUTES` | Self-driving default interval |
| `FMP_API_KEY` | Preferred market data |
| `ALPHA_VANTAGE_API_KEY` | Fallback market data |
| `MARKETAUX_API_KEY` | Reserved / status flag (unused by tools today) |
| `CORS_ORIGINS` | Allowed frontend origins |
| `PORT` | Backend port (default `8000`) |
| `VITE_API_URL` / `VITE_WS_URL` | Frontend → backend URLs |

Without market keys, providers return `[MOCK]` data. Without DeepSeek, LLM calls fail closed into mock recommendations so the UI remains usable for local demos.

---

## Testing

Backend uses **pytest** + **pytest-asyncio**.

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -v
```

Markers: `unit`, `integration`, `slow`, `network`.

Unit tests cover workflow helpers, market providers/tools, self-driving loop, user profile, portfolio models/manager, error handlers, config/LLM factory, WebSocket message helpers, and runner facade — **without modifying application source**.

---

## Deploy notes

- Backend: `render.yaml` → `pip install -r requirements.txt` + `python start_backend.py`
- Frontend: Vercel SPA (`frontend/vercel.json` rewrites to `index.html`)
- Set `CORS_ORIGINS` to your hosted frontend URL(s)

---

## Important accuracy notes

- The older `backend/tradingagents/README.md` describes an AgentScope / MCP multi-agent design (AlphaML, ExecutionAgent, etc.). **That design is not what this tree implements.** The live system is LangGraph + FastAPI as documented above.
- Per-agent strategy text in the user profile is **persisted for the UI** but is **not currently injected** into orchestrator/verifier prompts.
- Sentiment has no dedicated news tool yet; risk/sentiment appear as finalize-time status personas.
- Portfolio price updates for P&L use placeholder prices for a fixed ticker set, not the live market providers.

---

## License

See repository license file if present; otherwise treat as project-private unless otherwise stated.
