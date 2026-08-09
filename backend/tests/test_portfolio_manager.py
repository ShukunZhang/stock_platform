"""Unit tests for portfolio models and PortfolioFileManager."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from web_ui.backend.portfolio_manager import (
    PortfolioData,
    PortfolioFileManager,
    Position,
    Trade,
    TradeHistory,
)


pytestmark = pytest.mark.unit


class TestPositionModel:
    def test_symbol_uppercased(self):
        pos = Position(symbol="aapl", quantity=10, average_price=100, current_price=110)
        assert pos.symbol == "AAPL"

    def test_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            Position(symbol="AAPL", quantity=-1, average_price=10)

    def test_pnl_calculations(self):
        pos = Position(symbol="AAPL", quantity=10, average_price=100, current_price=110)
        assert pos.market_value == 1100.0
        assert pos.cost_basis == 1000.0
        assert pos.unrealized_pnl == 100.0
        assert pos.unrealized_pnl_percent == 10.0

    def test_zero_cost_basis_pnl_percent(self):
        pos = Position(symbol="AAPL", quantity=0, average_price=0, current_price=10)
        assert pos.unrealized_pnl_percent == 0.0


class TestTradeModel:
    def test_validates_action_and_positive_qty_price(self):
        trade = Trade(symbol="msft", action="BUY", quantity=5, price=10, fees=1)
        assert trade.symbol == "MSFT"
        assert trade.action == "buy"
        assert trade.gross_value == 50.0
        assert trade.net_value == 51.0  # current implementation: gross + fees

    def test_rejects_invalid_action(self):
        with pytest.raises(ValidationError):
            Trade(symbol="AAPL", action="hold", quantity=1, price=1)

    def test_rejects_non_positive_quantity(self):
        with pytest.raises(ValidationError):
            Trade(symbol="AAPL", action="buy", quantity=0, price=1)


class TestPortfolioDataAndTradeHistory:
    def test_portfolio_totals(self):
        portfolio = PortfolioData(
            cash_balance=90000,
            initial_balance=100000,
            positions={
                "AAPL": Position(
                    symbol="AAPL", quantity=10, average_price=100, current_price=110
                )
            },
        )
        assert portfolio.total_market_value == 1100.0
        assert portfolio.total_value == 91100.0
        assert portfolio.total_unrealized_pnl == 100.0
        assert portfolio.total_pnl == -8900.0

    def test_trade_history_helpers(self):
        history = TradeHistory()
        t1 = Trade(symbol="AAPL", action="buy", quantity=1, price=10)
        t2 = Trade(symbol="MSFT", action="buy", quantity=1, price=20)
        history.add_trade(t1)
        history.add_trade(t2)
        assert history.last_trade_id == 2
        assert len(history.get_trades_for_symbol("aapl")) == 1
        assert len(history.get_recent_trades(1)) == 1


class TestPortfolioFileManager:
    @pytest.fixture
    def manager(self, tmp_data_dir) -> PortfolioFileManager:
        mgr = PortfolioFileManager(data_dir=str(tmp_data_dir / "portfolio"))
        mgr.initialize()
        return mgr

    def test_initialize_creates_files(self, manager: PortfolioFileManager):
        status = manager.get_status()
        assert status["initialized"] is True
        assert status["portfolio_file_exists"] is True
        assert status["trades_file_exists"] is True
        assert status["total_positions"] == 0

    def test_get_portfolio_data_defaults(self, manager: PortfolioFileManager):
        data = manager.get_portfolio_data()
        assert data["status"] == "active"
        assert data["cash_balance"] == 100000.0
        assert data["positions"] == []

    def test_buy_and_sell_trade(self, manager: PortfolioFileManager):
        buy = manager.execute_trade(
            {"symbol": "AAPL", "action": "buy", "quantity": 10, "price": 100, "fees": 0}
        )
        assert buy["success"] is True
        data = manager.get_portfolio_data()
        assert data["cash_balance"] == 99000.0
        assert len(data["positions"]) == 1

        pos = manager.get_position("AAPL")
        assert pos is not None
        assert pos["quantity"] == 10

        sell = manager.execute_trade(
            {"symbol": "AAPL", "action": "sell", "quantity": 10, "price": 110, "fees": 0}
        )
        assert sell["success"] is True
        assert manager.get_position("AAPL") is None
        final = manager.get_portfolio_data()
        assert final["cash_balance"] == 100100.0

    def test_insufficient_cash(self, manager: PortfolioFileManager):
        result = manager.execute_trade(
            {
                "symbol": "AAPL",
                "action": "buy",
                "quantity": 1_000_000,
                "price": 1000,
                "fees": 0,
            }
        )
        assert result["success"] is False
        assert "Insufficient cash" in result["error"]

    def test_sell_without_position(self, manager: PortfolioFileManager):
        result = manager.execute_trade(
            {"symbol": "AAPL", "action": "sell", "quantity": 1, "price": 100}
        )
        assert result["success"] is False
        assert "No position" in result["error"]

    def test_sell_insufficient_quantity(self, manager: PortfolioFileManager):
        manager.execute_trade(
            {"symbol": "AAPL", "action": "buy", "quantity": 2, "price": 100}
        )
        result = manager.execute_trade(
            {"symbol": "AAPL", "action": "sell", "quantity": 5, "price": 100}
        )
        assert result["success"] is False
        assert "Insufficient quantity" in result["error"]

    def test_buy_adds_to_existing_position_average(self, manager: PortfolioFileManager):
        manager.execute_trade(
            {"symbol": "AAPL", "action": "buy", "quantity": 10, "price": 100, "fees": 0}
        )
        manager.execute_trade(
            {"symbol": "AAPL", "action": "buy", "quantity": 10, "price": 120, "fees": 0}
        )
        pos = manager.get_position("AAPL")
        assert pos["quantity"] == 20
        assert pos["average_price"] == 110.0

    def test_get_trade_history(self, manager: PortfolioFileManager):
        manager.execute_trade(
            {"symbol": "MSFT", "action": "buy", "quantity": 1, "price": 10}
        )
        history = manager.get_trade_history(symbol="MSFT")
        assert len(history) == 1
        assert history[0]["symbol"] == "MSFT"
