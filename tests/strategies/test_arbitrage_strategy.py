"""Unit tests for the arbitrage strategy."""

import unittest
from unittest.mock import MagicMock, patch

from src.strategies.arbitrage_strategy import SimpleArbitrageStrategy


class TestArbitrageStrategy(unittest.TestCase):
    """Test cases for the arbitrage strategy."""
    
    @patch("src.strategies.base_strategy.config_manager")
    def test_initialize(self, mock_config_manager):
        """Test initializing the strategy."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.002,
            "max_trade_amount": 200,
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        }
        
        # Create mock components
        mock_exchange = MagicMock()
        mock_data_cache = MagicMock()
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(mock_exchange, mock_data_cache)
        
        # Check that the components are set correctly
        self.assertEqual(strategy.exchange, mock_exchange)
        self.assertEqual(strategy.data_cache, mock_data_cache)
        
        # Check that the configuration is set correctly
        self.assertEqual(strategy.min_profit_threshold, 0.002)
        self.assertEqual(strategy.max_trade_amount, 200)
        self.assertEqual(strategy.symbols, ["BTC/USDT", "ETH/USDT", "ETH/BTC"])
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_on_tick(self, mock_config_manager):
        """Test processing a market data tick."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        }
        
        # Create mock components
        mock_exchange = MagicMock()
        mock_data_cache = MagicMock()
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(mock_exchange, mock_data_cache)
        
        # Mock the logger
        strategy.logger = MagicMock()
        
        # Process a tick for a symbol in the strategy's symbols
        market_data = {"symbol": "BTC/USDT", "bid": 50000, "ask": 50100}
        strategy.on_tick(market_data)
        
        # Check that the logger was called correctly
        strategy.logger.debug.assert_any_call("Received tick: {'symbol': 'BTC/USDT', 'bid': 50000, 'ask': 50100}")
        strategy.logger.debug.assert_any_call("Processing tick for BTC/USDT")
        strategy.logger.info.assert_called_with("Checking for arbitrage opportunities for BTC/USDT")
        
        # Process a tick for a symbol not in the strategy's symbols
        market_data = {"symbol": "LTC/USDT", "bid": 100, "ask": 101}
        strategy.on_tick(market_data)
        
        # Check that the logger was called correctly
        strategy.logger.debug.assert_called_with("Received tick: {'symbol': 'LTC/USDT', 'bid': 100, 'ask': 101}")
        # No additional calls to logger.info since the symbol is not in the strategy's symbols
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_on_order_update(self, mock_config_manager):
        """Test processing an order update."""
        # Mock the config manager
        mock_config_manager.get.return_value = {}
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        
        # Mock the logger
        strategy.logger = MagicMock()
        
        # Process an order update
        order_update = {"order_id": "123", "status": "FILLED", "symbol": "BTC/USDT"}
        strategy.on_order_update(order_update)
        
        # Check that the logger was called correctly
        strategy.logger.debug.assert_called_with("Received order update: {'order_id': '123', 'status': 'FILLED', 'symbol': 'BTC/USDT'}")
        strategy.logger.info.assert_called_with("Order 123 status updated to FILLED")
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_on_error(self, mock_config_manager):
        """Test processing an error."""
        # Mock the config manager
        mock_config_manager.get.return_value = {}
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        
        # Mock the logger
        strategy.logger = MagicMock()
        
        # Process an error
        error_data = {"type": "CONNECTION_ERROR", "message": "Connection lost"}
        strategy.on_error(error_data)
        
        # Check that the logger was called correctly
        strategy.logger.error.assert_any_call("Error occurred: {'type': 'CONNECTION_ERROR', 'message': 'Connection lost'}")
        strategy.logger.error.assert_called_with("Error type: CONNECTION_ERROR, message: Connection lost")


if __name__ == "__main__":
    unittest.main()