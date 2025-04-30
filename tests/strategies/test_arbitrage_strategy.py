"""Unit tests for the arbitrage strategy."""

import unittest
from unittest.mock import MagicMock, patch, call

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
            "fee_pct": 0.001,
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        }
        
        # Create mock components
        mock_exchange = MagicMock()
        mock_data_cache = MagicMock()
        mock_execution_handler = MagicMock()
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(mock_exchange, mock_data_cache, mock_execution_handler)
        
        # Check that the components are set correctly
        self.assertEqual(strategy.exchange, mock_exchange)
        self.assertEqual(strategy.data_cache, mock_data_cache)
        self.assertEqual(strategy.execution_handler, mock_execution_handler)
        
        # Check that the configuration is set correctly
        self.assertEqual(strategy.min_profit_threshold, 0.002)
        self.assertEqual(strategy.max_trade_amount, 200)
        self.assertEqual(strategy.fee_pct, 0.001)
        self.assertEqual(strategy.symbols, ["BTC/USDT", "ETH/USDT", "ETH/BTC"])
        self.assertEqual(strategy.price_cache, {})
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_on_tick_updates_price_cache(self, mock_config_manager):
        """Test that on_tick updates the price cache correctly."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
            "fee_pct": 0.001,
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
        
        # Check that the price cache was updated correctly
        self.assertEqual(strategy.price_cache["BTC/USDT"]["bid"], 50000)
        self.assertEqual(strategy.price_cache["BTC/USDT"]["ask"], 50100)
        
        # Check that the logger was called correctly
        strategy.logger.debug.assert_any_call("Received tick: {'symbol': 'BTC/USDT', 'bid': 50000, 'ask': 50100}")
        strategy.logger.debug.assert_any_call("Processing tick for BTC/USDT")
        
        # Process a tick for a symbol not in the strategy's symbols
        market_data = {"symbol": "LTC/USDT", "bid": 100, "ask": 101}
        strategy.on_tick(market_data)
        
        # Check that the price cache was not updated for this symbol
        self.assertNotIn("LTC/USDT", strategy.price_cache)
        
        # Check that the logger was called correctly
        strategy.logger.debug.assert_called_with("Received tick: {'symbol': 'LTC/USDT', 'bid': 100, 'ask': 101}")
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_has_all_required_prices(self, mock_config_manager):
        """Test the _has_all_required_prices method."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
            "fee_pct": 0.001,
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        }
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(MagicMock(), MagicMock())
        
        # Initially, the price cache is empty
        self.assertFalse(strategy._has_all_required_prices())
        
        # Add prices for one symbol
        strategy.price_cache["BTC/USDT"] = {"bid": 50000, "ask": 50100}
        self.assertFalse(strategy._has_all_required_prices())
        
        # Add prices for two symbols
        strategy.price_cache["ETH/USDT"] = {"bid": 3000, "ask": 3010}
        self.assertFalse(strategy._has_all_required_prices())
        
        # Add prices for all three symbols
        strategy.price_cache["ETH/BTC"] = {"bid": 0.06, "ask": 0.061}
        self.assertTrue(strategy._has_all_required_prices())
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_check_triangular_arbitrage_profitable(self, mock_config_manager):
        """Test the _check_triangular_arbitrage method with profitable opportunity."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,  # 0.1%
            "max_trade_amount": 100,
            "fee_pct": 0.001,  # 0.1%
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        }
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        mock_execution_handler = MagicMock()
        strategy.initialize(MagicMock(), MagicMock(), mock_execution_handler)
        
        # Mock the logger
        strategy.logger = MagicMock()
        
        # Set up prices that create a profitable arbitrage opportunity
        # Path: USDT -> BTC -> ETH -> USDT
        # 100 USDT -> 0.01 BTC -> 0.17 ETH -> 102 USDT (2% profit before fees)
        strategy.price_cache = {
            "BTC/USDT": {"bid": 9900, "ask": 10000},  # Buy BTC at 10000 USDT, sell at 9900 USDT
            "ETH/BTC": {"bid": 0.058, "ask": 0.059},  # Buy ETH at 0.059 BTC, sell at 0.058 BTC
            "ETH/USDT": {"bid": 600, "ask": 590}      # Buy ETH at 590 USDT, sell at 600 USDT
        }
        
        # Mock the execution handler to return a valid order ID
        mock_execution_handler.handle_signal.return_value = "test_order_id"
        
        # Check for arbitrage opportunities
        strategy._check_triangular_arbitrage()
        
        # Verify that the logger was called with the expected message for a profitable opportunity
        strategy.logger.info.assert_any_call(
            unittest.mock.ANY  # We don't need to check the exact message, just that info was logged
        )
        
        # Verify that the execution handler was called with the correct signals
        self.assertEqual(mock_execution_handler.handle_signal.call_count, 3)
        
        # Verify the first signal (Buy BTC/USDT)
        first_signal = mock_execution_handler.handle_signal.call_args_list[0][0][0]
        self.assertEqual(first_signal["strategy_id"], "test_arbitrage")
        self.assertEqual(first_signal["symbol"], "BTC/USDT")
        self.assertEqual(first_signal["side"], "buy")
        self.assertEqual(first_signal["order_type"], "MARKET")
        self.assertEqual(first_signal["params"]["arbitrage_leg"], 1)
        self.assertEqual(first_signal["params"]["arbitrage_path"], "USDT->BTC->ETH->USDT")
        
        # Verify the second signal (Buy ETH/BTC)
        second_signal = mock_execution_handler.handle_signal.call_args_list[1][0][0]
        self.assertEqual(second_signal["strategy_id"], "test_arbitrage")
        self.assertEqual(second_signal["symbol"], "ETH/BTC")
        self.assertEqual(second_signal["side"], "buy")
        self.assertEqual(second_signal["order_type"], "MARKET")
        self.assertEqual(second_signal["params"]["arbitrage_leg"], 2)
        self.assertEqual(second_signal["params"]["arbitrage_path"], "USDT->BTC->ETH->USDT")
        
        # Verify the third signal (Sell ETH/USDT)
        third_signal = mock_execution_handler.handle_signal.call_args_list[2][0][0]
        self.assertEqual(third_signal["strategy_id"], "test_arbitrage")
        self.assertEqual(third_signal["symbol"], "ETH/USDT")
        self.assertEqual(third_signal["side"], "sell")
        self.assertEqual(third_signal["order_type"], "MARKET")
        self.assertEqual(third_signal["params"]["arbitrage_leg"], 3)
        self.assertEqual(third_signal["params"]["arbitrage_path"], "USDT->BTC->ETH->USDT")
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_check_triangular_arbitrage_not_profitable(self, mock_config_manager):
        """Test the _check_triangular_arbitrage method with no profitable opportunity."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,  # 0.1%
            "max_trade_amount": 100,
            "fee_pct": 0.001,  # 0.1%
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        }
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(MagicMock(), MagicMock())
        
        # Mock the logger
        strategy.logger = MagicMock()
        
        # Set up prices that do not create a profitable arbitrage opportunity
        strategy.price_cache = {
            "BTC/USDT": {"bid": 9900, "ask": 10000},  # Buy BTC at 10000 USDT, sell at 9900 USDT
            "ETH/BTC": {"bid": 0.058, "ask": 0.059},  # Buy ETH at 0.059 BTC, sell at 0.058 BTC
            "ETH/USDT": {"bid": 580, "ask": 590}      # Buy ETH at 590 USDT, sell at 580 USDT
        }
        
        # Check for arbitrage opportunities
        strategy._check_triangular_arbitrage()
        
        # Verify that the logger was not called with an info message about a profitable opportunity
        for call_args in strategy.logger.info.call_args_list:
            self.assertNotIn("Triangular arbitrage opportunity detected", call_args[0][0])
            
    @patch("src.strategies.base_strategy.config_manager")
    def test_on_tick_with_complete_data(self, mock_config_manager):
        """Test on_tick with complete data for all symbols."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
            "fee_pct": 0.001,
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
        }
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(MagicMock(), MagicMock())
        
        # Mock the logger and _check_triangular_arbitrage method
        strategy.logger = MagicMock()
        strategy._check_triangular_arbitrage = MagicMock()
        
        # Add prices for two symbols
        strategy.price_cache = {
            "BTC/USDT": {"bid": 50000, "ask": 50100},
            "ETH/USDT": {"bid": 3000, "ask": 3010},
        }
        
        # Process a tick for the third symbol
        market_data = {"symbol": "ETH/BTC", "bid": 0.06, "ask": 0.061}
        strategy.on_tick(market_data)
        
        # Check that _check_triangular_arbitrage was called
        strategy._check_triangular_arbitrage.assert_called_once()
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_on_trade(self, mock_config_manager):
        """Test on_trade method."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
            "fee_pct": 0.001,
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
            "threshold": 0.001,
        }
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(MagicMock(), MagicMock())
        
        # Mock the logger and _check_triangular_arbitrage_from_trades method
        strategy.logger = MagicMock()
        strategy._check_triangular_arbitrage_from_trades = MagicMock()
        
        # Process a trade for a symbol in the strategy's symbols
        trade_data = {"symbol": "BTC/USDT", "price": 50000, "amount": 1.0, "side": "buy"}
        strategy.on_trade(trade_data)
        
        # Check that the latest price was updated correctly
        self.assertEqual(strategy.latest_prices["BTC/USDT"], 50000)
        
        # Check that the logger was called correctly
        strategy.logger.debug.assert_called_with("Updated latest price for BTC/USDT: 50000")
        
        # Process trades for all symbols to trigger arbitrage check
        strategy.on_trade({"symbol": "ETH/USDT", "price": 3000, "amount": 1.0, "side": "buy"})
        strategy.on_trade({"symbol": "ETH/BTC", "price": 0.06, "amount": 1.0, "side": "buy"})
        
        # Check that _check_triangular_arbitrage_from_trades was called
        strategy._check_triangular_arbitrage_from_trades.assert_called_once()
        
        # Process a trade for a symbol not in the strategy's symbols
        strategy._check_triangular_arbitrage_from_trades.reset_mock()
        strategy.on_trade({"symbol": "LTC/USDT", "price": 100, "amount": 1.0, "side": "buy"})
        
        # Check that _check_triangular_arbitrage_from_trades was not called
        strategy._check_triangular_arbitrage_from_trades.assert_not_called()
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_check_triangular_arbitrage_from_trades(self, mock_config_manager):
        """Test _check_triangular_arbitrage_from_trades method."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
            "fee_pct": 0.001,
            "symbols": ["BTC/USDT", "ETH/USDT", "ETH/BTC"],
            "threshold": 0.001,
        }
        
        # Initialize the strategy
        strategy = SimpleArbitrageStrategy("test_arbitrage")
        strategy.initialize(MagicMock(), MagicMock())
        
        # Mock the logger
        strategy.logger = MagicMock()
        
        # Set up prices that create a profitable arbitrage opportunity
        # Path: USDT -> BTC -> ETH -> USDT
        # 1 USDT -> 0.0001 BTC -> 0.0017 ETH -> 1.02 USDT (2% profit)
        strategy.latest_prices = {
            "BTC/USDT": 10000,  # 1 BTC = 10000 USDT
            "ETH/BTC": 0.06,    # 1 ETH = 0.06 BTC
            "ETH/USDT": 600     # 1 ETH = 600 USDT
        }
        
        # Check for arbitrage opportunities
        strategy._check_triangular_arbitrage_from_trades()
        
        # Verify that the logger was called with the expected message for a profitable opportunity
        strategy.logger.info.assert_any_call(
            "Arbitrage Opportunity (Path 2): USDT->BTC->ETH->USDT, Profit: 0.0000%"
        )
        
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