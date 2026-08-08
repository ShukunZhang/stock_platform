# Stock Analysis Web UI Backend

FastAPI-based backend for the Stock Analysis Web UI with real-time WebSocket communication and agent coordination.

## Overview

This backend provides:
- RESTful API endpoints for portfolio management
- WebSocket connections for real-time agent communication
- Integration with the existing trading agents system
- CORS support for frontend integration
- Comprehensive error handling and logging

## Architecture

```
web_ui/backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration settings
├── websocket_manager.py   # WebSocket connection management
├── portfolio_manager.py   # Portfolio file operations (placeholder)
├── manager_agent.py       # Agent coordination (placeholder)
├── error_handlers.py      # Error handling utilities
├── run.py                 # Startup script
├── test_backend.py        # Basic infrastructure tests
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Current Implementation Status

### ✅ Task 1 - Completed
- [x] FastAPI application with proper directory structure
- [x] CORS middleware configuration
- [x] WebSocket endpoint for real-time communication
- [x] Basic error handling and logging
- [x] Configuration management
- [x] Health check and status endpoints

### 🔄 Upcoming Tasks
- [ ] Task 2: Portfolio file management system (full implementation)
- [ ] Task 3: Manager agent with DeepSeek LLM integration
- [ ] Task 4: WebSocket manager enhancements
- [ ] Task 5: Integration with existing agent system

## Installation

1. Install dependencies:
```bash
cd web_ui/backend
pip install -r requirements.txt
```

2. Set up environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running the Backend

### Development Mode
```bash
# From project root
python -m web_ui.backend.run

# Or directly
cd web_ui/backend
python run.py
```

### Production Mode
```bash
# Set environment variables
export WEBUI_DEBUG=false
export WEBUI_RELOAD=false

python -m web_ui.backend.run
```

## API Endpoints

### REST Endpoints

- `GET /health` - Health check
- `GET /api/status` - System status
- `GET /api/portfolio` - Get portfolio data
- `POST /api/portfolio/trade` - Execute trade (placeholder)

### WebSocket Endpoint

- `WS /ws` - Real-time communication

#### WebSocket Message Types

**Client to Server:**
```json
{
  "type": "stock_query",
  "content": "Should I buy AAPL?"
}
```

```json
{
  "type": "portfolio_request"
}
```

**Server to Client:**
```json
{
  "type": "query_started",
  "message": "Analyzing your query...",
  "query": "Should I buy AAPL?",
  "timestamp": "2024-01-01T12:00:00"
}
```

```json
{
  "type": "final_recommendation",
  "data": {
    "recommendation": "buy",
    "confidence": 0.8,
    "rationale": "Analysis details..."
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

## Configuration

Configuration is managed through environment variables with the `WEBUI_` prefix:

```bash
WEBUI_HOST=0.0.0.0
WEBUI_PORT=8000
WEBUI_DEBUG=false
WEBUI_LOG_LEVEL=INFO
WEBUI_CORS_ORIGINS=["http://localhost:3000"]
```

See `config.py` for all available settings.

## Testing

Run the basic infrastructure tests:

```bash
cd web_ui/backend
python -m pytest test_backend.py -v
```

## Logging

Logs are written to:
- Console (stdout)
- File: `web_ui/logs/backend.log`

Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Error Handling

The backend includes comprehensive error handling:
- Custom exception classes for different error types
- Standardized error response format
- Automatic error logging with context
- WebSocket error recovery

## WebSocket Connection Management

Features:
- Automatic client ID assignment
- Connection metadata tracking
- Message broadcasting
- Stale connection cleanup
- Connection health monitoring

## Development Notes

### Current Placeholders

The following components are placeholder implementations that will be fully developed in subsequent tasks:

1. **PortfolioFileManager** (Task 2)
   - Currently returns mock data
   - Will implement JSON file operations
   - Will include trade execution logic

2. **ManagerAgent** (Task 3)
   - Currently returns placeholder responses
   - Will integrate with DeepSeek LLM
   - Will coordinate with existing agent system

### Integration Points

The backend is designed to integrate with:
- Existing `tradingagents` package
- DeepSeek LLM API
- Local portfolio JSON files
- React frontend (Task 6+)

## Next Steps

1. Implement full portfolio management (Task 2)
2. Integrate DeepSeek LLM and agent coordination (Task 3)
3. Enhance WebSocket functionality (Task 4)
4. Connect to existing agent system (Task 5)
5. Build React frontend (Tasks 6+)

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Change port in config or environment
   export WEBUI_PORT=8001
   ```

2. **CORS errors**
   ```bash
   # Add your frontend URL to CORS origins
   export WEBUI_CORS_ORIGINS='["http://localhost:3000", "http://your-frontend-url"]'
   ```

3. **WebSocket connection issues**
   - Check firewall settings
   - Verify WebSocket URL in frontend
   - Check browser console for errors

### Logs

Check logs for detailed error information:
```bash
tail -f web_ui/logs/backend.log
```