"""Tests for the performance analyzer."""

import unittest
from unittest.mock import MagicMock, patch, call

from src.backtesting.performance import PerformanceAnalyzer


class TestPerformanceAnalyzer(unittest.TestCase):
    """Test cases for the PerformanceAnalyzer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {"initial_balance": 10000.0}
        
        # Create performance analyzer with mock dependencies
        self.performance_analyzer = PerformanceAnalyzer(
            config=self.mock_config,
            logger=self.mock_logger,
        )
        
    def test_initialization(self):
        """Test initialization of the performance analyzer."""
        # Verify config was accessed
        self.mock_config.get.assert_called_with("backtesting", {})
        
        # Verify logger was used
        self.mock_logger.info.assert_called_with("Performance analyzer initialized")
        
        # Verify initial state
        self.assertEqual(self.performance_analyzer.trades, [])
        self.assertEqual(self.performance_analyzer.initial_balance, 10000.0)
        self.assertEqual(self.performance_analyzer.current_balance, 10000.0)
        
    def test_record_trade(self):
        """Test recording a trade."""
        # Reset mock to clear initialization calls
        self.mock_logger.reset_mock()
        
        # Create test trade data
        trade_data = {
            "order_id": "test_order_1",
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 1.0,
            "price": 35000.0,
            "timestamp": 1625097600000,
        }
        
        # Call the method
        self.performance_analyzer.record_trade(trade_data)
        
        # Verify logger was used
        self.mock_logger.info.assert_called_with(f"Recording trade: {trade_data}")
        
        # Verify trade was added to the list
        self.assertEqual(len(self.performance_analyzer.trades), 1)
        self.assertEqual(self.performance_analyzer.trades[0], trade_data)
        
    def test_calculate_metrics(self):
        """Test calculating performance metrics."""
        # Reset mock to clear initialization calls
        self.mock_logger.reset_mock()
        
        # Add some test trades
        self.performance_analyzer.trades = [
            {
                "order_id": "test_order_1",
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 1.0,
                "price": 35000.0,
                "timestamp": 1625097600000,
            },
            {
                "order_id": "test_order_2",
                "symbol": "BTC/USDT",
                "side": "sell",
                "quantity": 1.0,
                "price": 36000.0,
                "timestamp": 1625184000000,
            },
        ]
        
        # Call the method
        result = self.performance_analyzer.calculate_metrics()
        
        # Verify logger calls - should have two calls in sequence
        expected_calls = [
            call("Calculating performance metrics"),
            call(f"Performance metrics: {result}")
        ]
        self.mock_logger.info.assert_has_calls(expected_calls, any_order=False)
        
        # Verify result structure
        self.assertIn("total_return", result)
        self.assertIn("sharpe_ratio", result)
        self.assertIn("max_drawdown", result)
        self.assertIn("win_rate", result)
        self.assertIn("profit_factor", result)
        self.assertIn("total_trades", result)
        
        # Verify total trades count
        self.assertEqual(result["total_trades"], 2)


if __name__ == "__main__":
    unittest.main()