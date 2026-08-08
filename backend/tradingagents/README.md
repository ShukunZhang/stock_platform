# AgentScope Multi-Agent Stock Analysis System (Kiro-StockAgent)

A comprehensive financial analysis platform that leverages AgentScope's multi-agent framework to provide intelligent stock analysis and trading recommendations using MCP (Model Context Protocol) tools.

## Overview

The system operates primarily in paper trading mode with optional live trading capabilities, ensuring safe experimentation while providing production-ready functionality. Each agent is implemented as an AgentScope ReActAgent with access to specific MCP tools for data retrieval and analysis.

## Architecture

The system consists of several specialized agents:

### Analysis Agents
- **MarketDataAgent**: Real-time and historical market data
- **FundamentalsAgent**: Financial statement analysis and valuation
- **SentimentAgent**: News and social media sentiment analysis
- **TechnicalAgent**: Technical indicators and pattern recognition
- **AlphaMLAgent**: Machine learning predictions
- **LLMResearchAgent**: Structured research with role-based prompts

### Orchestration Agents
- **PortfolioManager**: Signal aggregation and portfolio optimization
- **RiskManager**: Risk validation and constraint enforcement
- **ExecutionAgent**: Trade execution with advanced algorithms

### Supporting Components
- **Backtester**: Historical strategy simulation
- **OpsMonitor**: System monitoring and alerting

## Project Structure

```
tradingagents/
├── agents/                 # Agent implementations
├── mcp_clients/           # MCP client infrastructure
├── common/                # Shared models, interfaces, and utilities
│   ├── models.py         # Pydantic data models
│   ├── interfaces.py     # Base interfaces and abstract classes
│   ├── config.py         # Configuration management
│   └── utils.py          # Utility functions
├── tests/                 # Test suite
└── scripts/              # CLI and utility scripts
```

## Configuration

The system uses environment variables and configuration files for setup:

1. Copy `.env.example` to `.env` and configure your settings
2. Set `ENABLE_LIVE_TRADING=true` only when ready for live trading
3. Configure MCP service endpoints and API keys as needed

## Safety Features

- **Paper Trading Default**: System defaults to paper trading mode
- **Live Trading Safeguards**: Requires explicit environment variables and user confirmation
- **Risk Management**: Built-in risk limits and validation
- **Circuit Breakers**: Fault tolerance for external service failures

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Run in paper trading mode:
   ```bash
   python -m scripts.cli analyze AAPL
   ```

## Development

The project follows these principles:
- Type safety with Pydantic models
- Async/await for concurrent operations
- Comprehensive error handling and logging
- Modular architecture with clear interfaces
- Extensive testing coverage

## License

MIT License - see LICENSE file for details.