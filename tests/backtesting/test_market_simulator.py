"""Tests for the market simulator."""

import unittest
from unittest.mock import MagicMock, patch, call

from src.backtesting.market_simulator import MarketSimulator


class TestMarketSimulator(unittest.TestCase):
    """Test cases for the MarketSimulator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {}
        
        # Create market simulator with mock dependencies
        self.market_simulator = MarketSimulator(
            config=self.mock_config,
            logger=self.mock_logger,
        )
        
    def test_initialization(self):
        """Test initialization of the market simulator."""
        # Verify config was accessed
        self.mock_config.get.assert_called_with("backtesting", {})
        
        # Verify logger was used
        self.mock_logger.info.assert_called_with("Market simulator initialized")
        
        # Verify initial state
        self.assertIsNone(self.market_simulator.current_tick)
        self.assertEqual(self.market_simulator.order_id_counter, 0)
        
    def test_process_tick(self):
        """Test processing a market data tick."""
        # Reset mock to clear initialization calls
        self.mock_logger.reset_mock()
        
        # Create test tick data
        tick_data = {
            "timestamp": 1625097600000,
            "symbol": "BTC/USDT",
            "open": 35000.0,
            "high": 35500.0,
            "low": 34800.0,
            "close": 35200.0,
            "volume": 1000.0,
        }
        
        # Call the method
        self.market_simulator.process_tick(tick_data)
        
        # Verify logger was used
        self.mock_logger.debug.assert_called_with(f"Processing tick: {tick_data}")
        
        # Verify current tick was updated
        self.assertEqual(self.market_simulator.current_tick, tick_data)
        
    def test_simulate_order_fill(self):
        """Test simulating order execution."""
        # Reset mock to clear initialization calls
        self.mock_logger.reset_mock()
        
        # Create test order parameters
        order_params = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "LIMIT",
            "quantity": 1.0,
            "price": 35000.0,
        }
        
        # Call the method
        result = self.market_simulator.simulate_order_fill(order_params)
        
        # Verify logger calls - should have two calls in sequence
        expected_calls = [
            call(f"Simulating order fill: {order_params}"),
            call(f"Order sim_1 filled")
        ]
        self.mock_logger.info.assert_has_calls(expected_calls, any_order=False)
        
        # Verify result structure
        self.assertIn("id", result)
        self.assertEqual(result["status"], "filled")
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["side"], "buy")
        self.assertEqual(result["type"], "LIMIT")
        self.assertEqual(result["quantity"], 1.0)
        self.assertEqual(result["price"], 35000.0)
        self.assertEqual(result["filled_quantity"], 1.0)
        self.assertEqual(result["filled_price"], 35000.0)
        
        # Verify order ID counter was incremented
        self.assertEqual(self.market_simulator.order_id_counter, 1)
        
    def test_get_current_market_price(self):
        """Test getting the current market price."""
        # Reset mock to clear initialization calls
        self.mock_logger.reset_mock()
        
        # Call the method
        result = self.market_simulator.get_current_market_price("BTC/USDT")
        
        # Verify logger was used
        self.mock_logger.debug.assert_called_with("Getting current market price for BTC/USDT")
        
        # Verify result is a float
        self.assertIsInstance(result, float)
        self.assertEqual(result, 0.0)  # Default dummy value


if __name__ == "__main__":
    unittest.main()