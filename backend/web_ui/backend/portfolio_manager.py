"""
Portfolio File Manager - Complete implementation for managing portfolio data in JSON files.
Handles positions, trades, and portfolio calculations with Pydantic models.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field, field_validator
import uuid

logger = logging.getLogger(__name__)


class Position(BaseModel):
    """Pydantic model for a portfolio position."""
    
    symbol: str = Field(..., description="Stock symbol")
    quantity: float = Field(..., description="Number of shares held")
    average_price: float = Field(..., description="Average cost basis per share")
    current_price: float = Field(default=0.0, description="Current market price per share")
    last_price_update: Optional[str] = Field(default=None, description="Timestamp of last price update")
    
    @field_validator('symbol')
    @classmethod
    def symbol_must_be_uppercase(cls, v):
        return v.upper().strip()
    
    @field_validator('quantity', 'average_price', 'current_price')
    @classmethod
    def must_be_positive_or_zero(cls, v):
        if v < 0:
            raise ValueError('Value must be positive or zero')
        return v
    
    @property
    def market_value(self) -> float:
        """Calculate current market value of the position."""
        return round(self.quantity * self.current_price, 2)
    
    @property
    def cost_basis(self) -> float:
        """Calculate total cost basis of the position."""
        return round(self.quantity * self.average_price, 2)
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized profit/loss."""
        return round(self.market_value - self.cost_basis, 2)
    
    @property
    def unrealized_pnl_percent(self) -> float:
        """Calculate unrealized P&L as percentage."""
        if self.cost_basis == 0:
            return 0.0
        return round((self.unrealized_pnl / self.cost_basis) * 100, 2)


class Trade(BaseModel):
    """Pydantic model for a trade transaction."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique trade ID")
    symbol: str = Field(..., description="Stock symbol")
    action: str = Field(..., description="Trade action: 'buy' or 'sell'")
    quantity: float = Field(..., description="Number of shares traded")
    price: float = Field(..., description="Price per share")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Trade timestamp")
    fees: float = Field(default=0.0, description="Trading fees")
    notes: Optional[str] = Field(default=None, description="Optional trade notes")
    
    @field_validator('symbol')
    @classmethod
    def symbol_must_be_uppercase(cls, v):
        return v.upper().strip()
    
    @field_validator('action')
    @classmethod
    def action_must_be_valid(cls, v):
        if v.lower() not in ['buy', 'sell']:
            raise ValueError('Action must be "buy" or "sell"')
        return v.lower()
    
    @field_validator('quantity', 'price')
    @classmethod
    def must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity and price must be positive')
        return v
    
    @field_validator('fees')
    @classmethod
    def fees_must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Fees must be non-negative')
        return v
    
    @property
    def gross_value(self) -> float:
        """Calculate gross trade value (before fees)."""
        return round(self.quantity * self.price, 2)
    
    @property
    def net_value(self) -> float:
        """Calculate net trade value (after fees)."""
        return round(self.gross_value + self.fees, 2)


class PortfolioData(BaseModel):
    """Pydantic model for complete portfolio data."""
    
    cash_balance: float = Field(..., description="Available cash balance")
    positions: Dict[str, Position] = Field(default_factory=dict, description="Current positions by symbol")
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Last update timestamp")
    initial_balance: float = Field(default=100000.0, description="Initial portfolio balance")
    
    @field_validator('cash_balance', 'initial_balance')
    @classmethod
    def must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError('Balance must be non-negative')
        return v
    
    @property
    def total_market_value(self) -> float:
        """Calculate total market value of all positions."""
        return round(sum(pos.market_value for pos in self.positions.values()), 2)
    
    @property
    def total_cost_basis(self) -> float:
        """Calculate total cost basis of all positions."""
        return round(sum(pos.cost_basis for pos in self.positions.values()), 2)
    
    @property
    def total_value(self) -> float:
        """Calculate total portfolio value (cash + positions)."""
        return round(self.cash_balance + self.total_market_value, 2)
    
    @property
    def total_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L."""
        return round(sum(pos.unrealized_pnl for pos in self.positions.values()), 2)
    
    @property
    def total_pnl(self) -> float:
        """Calculate total P&L vs initial balance."""
        return round(self.total_value - self.initial_balance, 2)
    
    @property
    def total_pnl_percent(self) -> float:
        """Calculate total P&L percentage."""
        if self.initial_balance == 0:
            return 0.0
        return round((self.total_pnl / self.initial_balance) * 100, 2)


class TradeHistory(BaseModel):
    """Pydantic model for trade history data."""
    
    trades: List[Trade] = Field(default_factory=list, description="List of all trades")
    last_trade_id: int = Field(default=0, description="Counter for trade IDs")
    
    def add_trade(self, trade: Trade) -> None:
        """Add a trade to the history."""
        self.trades.append(trade)
        self.last_trade_id += 1
    
    def get_trades_for_symbol(self, symbol: str) -> List[Trade]:
        """Get all trades for a specific symbol."""
        return [trade for trade in self.trades if trade.symbol.upper() == symbol.upper()]
    
    def get_recent_trades(self, limit: int = 50) -> List[Trade]:
        """Get the most recent trades."""
        return sorted(self.trades, key=lambda t: t.timestamp, reverse=True)[:limit]


class PortfolioFileManager:
    """
    Complete Portfolio File Manager for managing portfolio data in JSON files.
    Handles positions, trades, and portfolio calculations with full validation.
    """
    
    def __init__(self, data_dir: str = "web_ui/data"):
        """
        Initialize the portfolio file manager.
        
        Args:
            data_dir: Directory to store portfolio data files
        """
        self.data_dir = data_dir
        self.portfolio_file = os.path.join(data_dir, "portfolio.json")
        self.trades_file = os.path.join(data_dir, "trades.json")
        self.initialized = False
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        logger.info(f"PortfolioFileManager initialized with data_dir: {data_dir}")
    
    def initialize(self) -> None:
        """Initialize the portfolio manager and create default files if needed."""
        try:
            self._initialize_files()
            self.initialized = True
            logger.info("PortfolioFileManager successfully initialized")
        except Exception as e:
            logger.error(f"Failed to initialize PortfolioFileManager: {e}")
            raise
    
    def _initialize_files(self) -> None:
        """Initialize portfolio and trades files with default data if they don't exist."""
        
        # Initialize portfolio file
        if not os.path.exists(self.portfolio_file):
            default_portfolio = PortfolioData(
                cash_balance=100000.0,
                initial_balance=100000.0
            )
            self._save_portfolio_data(default_portfolio)
            logger.info(f"Created default portfolio file: {self.portfolio_file}")
        
        # Initialize trades file
        if not os.path.exists(self.trades_file):
            default_trades = TradeHistory()
            self._save_trade_history(default_trades)
            logger.info(f"Created default trades file: {self.trades_file}")
    
    def _load_portfolio_data(self) -> PortfolioData:
        """Load portfolio data from JSON file."""
        try:
            with open(self.portfolio_file, 'r') as f:
                data = json.load(f)
            
            # Convert positions dict to Position objects
            if 'positions' in data:
                positions = {}
                for symbol, pos_data in data['positions'].items():
                    positions[symbol] = Position(**pos_data)
                data['positions'] = positions
            
            return PortfolioData(**data)
        except Exception as e:
            logger.error(f"Failed to load portfolio data: {e}")
            raise
    
    def _save_portfolio_data(self, portfolio: PortfolioData) -> None:
        """Save portfolio data to JSON file."""
        try:
            # Convert to dict for JSON serialization
            data = portfolio.model_dump()
            
            # Convert Position objects to dicts
            if 'positions' in data:
                positions_dict = {}
                for symbol, position in data['positions'].items():
                    if isinstance(position, Position):
                        positions_dict[symbol] = position.model_dump()
                    else:
                        positions_dict[symbol] = position
                data['positions'] = positions_dict
            
            with open(self.portfolio_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Portfolio data saved to {self.portfolio_file}")
        except Exception as e:
            logger.error(f"Failed to save portfolio data: {e}")
            raise
    
    def _load_trade_history(self) -> TradeHistory:
        """Load trade history from JSON file."""
        try:
            with open(self.trades_file, 'r') as f:
                data = json.load(f)
            
            # Convert trade dicts to Trade objects
            if 'trades' in data:
                trades = [Trade(**trade_data) for trade_data in data['trades']]
                data['trades'] = trades
            
            return TradeHistory(**data)
        except Exception as e:
            logger.error(f"Failed to load trade history: {e}")
            raise
    
    def _save_trade_history(self, trade_history: TradeHistory) -> None:
        """Save trade history to JSON file."""
        try:
            data = trade_history.model_dump()
            
            with open(self.trades_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug(f"Trade history saved to {self.trades_file}")
        except Exception as e:
            logger.error(f"Failed to save trade history: {e}")
            raise
    
    def get_portfolio_data(self) -> Dict[str, Any]:
        """
        Get current portfolio data with calculated metrics.
        
        Returns:
            Dict containing complete portfolio information
        """
        try:
            if not self.initialized:
                self.initialize()
            
            portfolio = self._load_portfolio_data()
            trade_history = self._load_trade_history()
            
            # Update current prices (placeholder - would integrate with market data)
            self._update_current_prices(portfolio)
            
            # Convert positions to dict format for API response
            positions_list = []
            for symbol, position in portfolio.positions.items():
                pos_dict = position.model_dump()
                pos_dict.update({
                    'market_value': position.market_value,
                    'cost_basis': position.cost_basis,
                    'unrealized_pnl': position.unrealized_pnl,
                    'unrealized_pnl_percent': position.unrealized_pnl_percent
                })
                positions_list.append(pos_dict)
            
            # Get recent trades
            recent_trades = trade_history.get_recent_trades(50)
            trades_list = [trade.model_dump() for trade in recent_trades]
            
            # Calculate daily P&L (placeholder - would need historical data)
            daily_pnl = 0.0
            daily_pnl_percent = 0.0
            
            return {
                "total_value": portfolio.total_value,
                "cash_balance": portfolio.cash_balance,
                "market_value": portfolio.total_market_value,
                "cost_basis": portfolio.total_cost_basis,
                "daily_pnl": daily_pnl,
                "daily_pnl_percent": daily_pnl_percent,
                "total_pnl": portfolio.total_pnl,
                "total_pnl_percent": portfolio.total_pnl_percent,
                "unrealized_pnl": portfolio.total_unrealized_pnl,
                "positions": positions_list,
                "trade_history": trades_list,
                "last_updated": portfolio.last_updated,
                "initial_balance": portfolio.initial_balance,
                "status": "active"
            }
        except Exception as e:
            logger.error(f"Failed to get portfolio data: {e}")
            return {
                "error": f"Failed to load portfolio data: {str(e)}",
                "status": "error"
            }
    
    def execute_trade(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trade and update portfolio.
        
        Args:
            trade_data: Dictionary containing trade information
            
        Returns:
            Dict containing trade result and updated portfolio data
        """
        try:
            if not self.initialized:
                self.initialize()
            
            # Validate and create trade object
            trade = Trade(**trade_data)
            
            # Load current data
            portfolio = self._load_portfolio_data()
            trade_history = self._load_trade_history()
            
            # Execute the trade
            result = self._process_trade(portfolio, trade)
            
            if result.get("success"):
                # Save updated data
                portfolio.last_updated = datetime.now().isoformat()
                self._save_portfolio_data(portfolio)
                
                trade_history.add_trade(trade)
                self._save_trade_history(trade_history)
                
                logger.info(f"Trade executed successfully: {trade.action} {trade.quantity} {trade.symbol} @ {trade.price}")
                
                return {
                    "success": True,
                    "trade": trade.model_dump(),
                    "message": f"Successfully {trade.action} {trade.quantity} shares of {trade.symbol}",
                    "updated_portfolio": self.get_portfolio_data()
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return {
                "success": False,
                "error": f"Trade execution failed: {str(e)}"
            }
    
    def _process_trade(self, portfolio: PortfolioData, trade: Trade) -> Dict[str, Any]:
        """Process a trade and update portfolio positions."""
        
        symbol = trade.symbol
        action = trade.action
        quantity = trade.quantity
        price = trade.price
        fees = trade.fees
        
        if action == "buy":
            # Calculate total cost including fees
            total_cost = (quantity * price) + fees
            
            # Check if sufficient cash
            if portfolio.cash_balance < total_cost:
                return {
                    "success": False,
                    "error": f"Insufficient cash balance. Required: ${total_cost:.2f}, Available: ${portfolio.cash_balance:.2f}"
                }
            
            # Deduct cash
            portfolio.cash_balance -= total_cost
            
            # Update or create position
            if symbol in portfolio.positions:
                existing_pos = portfolio.positions[symbol]
                total_quantity = existing_pos.quantity + quantity
                total_cost_basis = (existing_pos.quantity * existing_pos.average_price) + (quantity * price) + fees
                new_average_price = total_cost_basis / total_quantity
                
                portfolio.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=total_quantity,
                    average_price=new_average_price,
                    current_price=existing_pos.current_price
                )
            else:
                # Include fees in average price for new position
                average_price_with_fees = ((quantity * price) + fees) / quantity
                portfolio.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    average_price=average_price_with_fees,
                    current_price=price  # Use trade price as initial current price
                )
        
        elif action == "sell":
            # Check if position exists
            if symbol not in portfolio.positions:
                return {
                    "success": False,
                    "error": f"No position in {symbol} to sell"
                }
            
            existing_pos = portfolio.positions[symbol]
            
            # Check if sufficient quantity
            if existing_pos.quantity < quantity:
                return {
                    "success": False,
                    "error": f"Insufficient quantity in {symbol}. Available: {existing_pos.quantity}, Requested: {quantity}"
                }
            
            # Calculate proceeds after fees
            gross_proceeds = quantity * price
            net_proceeds = gross_proceeds - fees
            
            # Add cash
            portfolio.cash_balance += net_proceeds
            
            # Update position
            remaining_quantity = existing_pos.quantity - quantity
            if remaining_quantity == 0:
                # Remove position entirely
                del portfolio.positions[symbol]
            else:
                # Update quantity, keep same average price
                portfolio.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=remaining_quantity,
                    average_price=existing_pos.average_price,
                    current_price=existing_pos.current_price
                )
        
        return {"success": True}
    
    def _update_current_prices(self, portfolio: PortfolioData) -> None:
        """Update current prices for all positions (placeholder implementation)."""
        # This would integrate with market data service in a real implementation
        placeholder_prices = {
            "AAPL": 150.0,
            "GOOGL": 2800.0,
            "MSFT": 300.0,
            "TSLA": 800.0,
            "NVDA": 500.0,
            "AMZN": 3200.0,
            "META": 350.0,
            "NFLX": 450.0
        }
        
        for symbol, position in portfolio.positions.items():
            if symbol in placeholder_prices:
                position.current_price = placeholder_prices[symbol]
                position.last_price_update = datetime.now().isoformat()
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get a specific position by symbol."""
        try:
            portfolio = self._load_portfolio_data()
            
            if symbol.upper() in portfolio.positions:
                position = portfolio.positions[symbol.upper()]
                pos_dict = position.model_dump()
                pos_dict.update({
                    'market_value': position.market_value,
                    'cost_basis': position.cost_basis,
                    'unrealized_pnl': position.unrealized_pnl,
                    'unrealized_pnl_percent': position.unrealized_pnl_percent
                })
                return pos_dict
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to get position for {symbol}: {e}")
            return None
    
    def get_trade_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get trade history, optionally filtered by symbol."""
        try:
            trade_history = self._load_trade_history()
            
            if symbol:
                trades = trade_history.get_trades_for_symbol(symbol)
            else:
                trades = trade_history.get_recent_trades(limit)
            
            return [trade.model_dump() for trade in trades]
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get portfolio manager status and health check."""
        try:
            portfolio = self._load_portfolio_data()
            trade_history = self._load_trade_history()
            
            return {
                "initialized": self.initialized,
                "status": "active",
                "portfolio_file_exists": os.path.exists(self.portfolio_file),
                "trades_file_exists": os.path.exists(self.trades_file),
                "total_positions": len(portfolio.positions),
                "total_trades": len(trade_history.trades),
                "last_updated": portfolio.last_updated,
                "data_directory": self.data_dir
            }
        except Exception as e:
            return {
                "initialized": self.initialized,
                "status": "error",
                "error": str(e),
                "data_directory": self.data_dir
            }