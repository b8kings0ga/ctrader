"""Tests for the backtester."""

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from src.backtesting.backtester import Backtester


class TestBacktester(unittest.TestCase):
    """Test cases for the Backtester class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_strategy = MagicMock()
        self.mock_data_replay_engine = MagicMock()
        self.mock_market_simulator = MagicMock()
        self.mock_performance_analyzer = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {}
        
        # Create backtester with mock dependencies
        self.backtester = Backtester(
            config=self.mock_config,
            logger=self.mock_logger,
            strategy=self.mock_strategy,
            data_replay_engine=self.mock_data_replay_engine,
            market_simulator=self.mock_market_simulator,
            performance_analyzer=self.mock_performance_analyzer,
        )
        
    def test_initialization(self):
        """Test initialization of the backtester."""
        # Verify config was accessed
        self.mock_config.get.assert_called_with("backtesting", {})
        
        # Verify logger was used
        self.mock_logger.info.assert_called_with("Backtester initialized")
        
        # Verify dependencies were set
        self.assertEqual(self.backtester.strategy, self.mock_strategy)
        self.assertEqual(self.backtester.data_replay_engine, self.mock_data_replay_engine)
        self.assertEqual(self.backtester.market_simulator, self.mock_market_simulator)
        self.assertEqual(self.backtester.performance_analyzer, self.mock_performance_analyzer)
        
    def test_initialization_without_strategy(self):
        """Test initialization without a strategy."""
        # Attempt to create backtester without a strategy
        with self.assertRaises(ValueError):
            Backtester(
                config=self.mock_config,
                logger=self.mock_logger,
                strategy=None,
            )
            
    def test_run(self):
        """Test running a backtest."""
        # Configure mock data replay engine
        test_data = pd.DataFrame({
            "timestamp": [1, 2, 3],
            "open": [100.0, 101.0, 102.0],
            "high": [102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0],
            "close": [101.0, 102.0, 103.0],
            "volume": [1000.0, 1100.0, 1200.0],
        })
        self.mock_data_replay_engine.load_historical_data.return_value = test_data
        self.mock_data_replay_engine.replay_data.return_value = [
            {"timestamp": 1, "price": 101.0},
            {"timestamp": 2, "price": 102.0},
            {"timestamp": 3, "price": 103.0},
        ]
        
        # Configure mock strategy
        self.mock_strategy.__class__.__name__ = "TestStrategy"
        self.mock_strategy.on_tick.return_value = [
            {
                "symbol": "BTC/USDT",
                "side": "buy",
                "quantity": 1.0,
                "price": 101.0,
            }
        ]
        
        # Configure mock market simulator
        self.mock_market_simulator.simulate_order_fill.return_value = {
            "id": "test_order_1",
            "status": "filled",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "LIMIT",
            "quantity": 1.0,
            "price": 101.0,
            "filled_quantity": 1.0,
            "filled_price": 101.0,
            "timestamp": 1,
        }
        
        # Configure mock performance analyzer
        self.mock_performance_analyzer.calculate_metrics.return_value = {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_trades": 3,
        }
        
        # Call the method
        result = self.backtester.run(
            symbol="BTC/USDT",
            start_date="2023-01-01",
            end_date="2023-01-31",
            timeframe="1h",
        )
        
        # Verify data replay engine was called
        self.mock_data_replay_engine.load_historical_data.assert_called_with(
            symbol="BTC/USDT",
            start_date="2023-01-01",
            end_date="2023-01-31",
            timeframe="1h",
        )
        self.mock_data_replay_engine.replay_data.assert_called_with(test_data)
        
        # Verify strategy was initialized and called for each tick
        self.mock_strategy.initialize.assert_called_once()
        self.assertEqual(self.mock_strategy.on_tick.call_count, 3)
        
        # Verify market simulator was called for each tick and signal
        self.assertEqual(self.mock_market_simulator.process_tick.call_count, 3)
        self.assertEqual(self.mock_market_simulator.simulate_order_fill.call_count, 3)
        
        # Verify performance analyzer was called for each trade and metrics
        self.assertEqual(self.mock_performance_analyzer.record_trade.call_count, 3)
        self.mock_performance_analyzer.calculate_metrics.assert_called_once()
        
        # Verify result structure
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["start_date"], "2023-01-01")
        self.assertEqual(result["end_date"], "2023-01-31")
        self.assertEqual(result["timeframe"], "1h")
        self.assertEqual(result["strategy"], "TestStrategy")
        self.assertIn("metrics", result)
        
    def test_convert_signal_to_order_params(self):
        """Test converting a signal to order parameters."""
        # Create test signal
        signal = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "quantity": 1.0,
            "price": 35000.0,
            "order_type": "LIMIT",
        }
        
        # Call the method
        result = self.backtester._convert_signal_to_order_params(signal)
        
        # Verify result
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["side"], "buy")
        self.assertEqual(result["type"], "LIMIT")
        self.assertEqual(result["quantity"], 1.0)
        self.assertEqual(result["price"], 35000.0)
        
    def test_convert_order_to_trade(self):
        """Test converting an order to a trade record."""
        # Create test order
        order = {
            "id": "test_order_1",
            "status": "filled",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "LIMIT",
            "quantity": 1.0,
            "price": 35000.0,
            "filled_quantity": 1.0,
            "filled_price": 35000.0,
            "timestamp": 1625097600000,
        }
        
        # Call the method
        result = self.backtester._convert_order_to_trade(order)
        
        # Verify result
        self.assertEqual(result["order_id"], "test_order_1")
        self.assertEqual(result["symbol"], "BTC/USDT")
        self.assertEqual(result["side"], "buy")
        self.assertEqual(result["quantity"], 1.0)
        self.assertEqual(result["price"], 35000.0)
        self.assertEqual(result["timestamp"], 1625097600000)


if __name__ == "__main__":
    unittest.main()