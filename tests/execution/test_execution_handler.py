"""Tests for the execution handler."""

import unittest
from unittest.mock import MagicMock, patch

from src.execution.execution_handler import ExecutionHandler


class TestExecutionHandler(unittest.TestCase):
    """Test cases for the ExecutionHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_order_manager = MagicMock()
        self.mock_signal_aggregator = MagicMock()
        self.mock_risk_manager = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {"default_order_type": "LIMIT"}
        
        # Create execution handler with mock dependencies
        self.execution_handler = ExecutionHandler(
            config=self.mock_config,
            logger=self.mock_logger,
            order_manager=self.mock_order_manager,
            signal_aggregator=self.mock_signal_aggregator,
            risk_manager=self.mock_risk_manager,
        )
        
    def test_handle_signal_success(self):
        """Test handling a signal successfully."""
        # Mock signal data
        signal_data = {
            "strategy_id": "test_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_type": "entry",
            "strength": 0.8,
            "price": 50000.0,
            "quantity": 1.0,
        }
        
        # Mock signal aggregator response
        self.mock_signal_aggregator.process_signal.return_value = signal_data
        
        # Mock risk manager response
        self.mock_risk_manager.check_order_risk.return_value = True
        
        # Mock order manager response
        self.mock_order_manager.create_order.return_value = "test_order_id"
        
        # Call handle_signal
        result = self.execution_handler.handle_signal(signal_data)
        
        # Verify signal aggregator was called with correct parameters
        self.mock_signal_aggregator.process_signal.assert_called_once_with(signal_data)
        
        # Verify risk manager was called with correct parameters
        expected_order_params = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "LIMIT",
            "quantity": 1.0,
            "price": 50000.0,
        }
        self.mock_risk_manager.check_order_risk.assert_called_once()
        actual_order_params = self.mock_risk_manager.check_order_risk.call_args[0][0]
        self.assertEqual(actual_order_params["symbol"], expected_order_params["symbol"])
        self.assertEqual(actual_order_params["side"], expected_order_params["side"])
        self.assertEqual(actual_order_params["type"], expected_order_params["type"])
        self.assertEqual(actual_order_params["quantity"], expected_order_params["quantity"])
        self.assertEqual(actual_order_params["price"], expected_order_params["price"])
        
        # Verify order manager was called with correct parameters
        self.mock_order_manager.create_order.assert_called_once_with(
            symbol="BTC/USDT",
            side="buy",
            type="LIMIT",
            quantity=1.0,
            price=50000.0,
            params={},
        )
        
        # Verify correct result was returned
        self.assertEqual(result, "test_order_id")
        
    def test_handle_signal_with_signal_error(self):
        """Test handling a signal with an error in signal processing."""
        # Mock signal data
        signal_data = {
            "strategy_id": "test_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_type": "entry",
        }
        
        # Mock signal aggregator to return an error
        self.mock_signal_aggregator.process_signal.return_value = {"error": "Missing required field"}
        
        # Call handle_signal
        result = self.execution_handler.handle_signal(signal_data)
        
        # Verify signal aggregator was called
        self.mock_signal_aggregator.process_signal.assert_called_once()
        
        # Verify risk manager was not called
        self.mock_risk_manager.check_order_risk.assert_not_called()
        
        # Verify order manager was not called
        self.mock_order_manager.create_order.assert_not_called()
        
        # Verify None was returned
        self.assertIsNone(result)
        
    def test_handle_signal_with_risk_rejection(self):
        """Test handling a signal that fails risk checks."""
        # Mock signal data
        signal_data = {
            "strategy_id": "test_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_type": "entry",
            "strength": 0.8,
            "price": 50000.0,
            "quantity": 1.0,
        }
        
        # Mock signal aggregator response
        self.mock_signal_aggregator.process_signal.return_value = signal_data
        
        # Mock risk manager to reject the order
        self.mock_risk_manager.check_order_risk.return_value = False
        
        # Call handle_signal
        result = self.execution_handler.handle_signal(signal_data)
        
        # Verify signal aggregator was called
        self.mock_signal_aggregator.process_signal.assert_called_once()
        
        # Verify risk manager was called
        self.mock_risk_manager.check_order_risk.assert_called_once()
        
        # Verify order manager was not called
        self.mock_order_manager.create_order.assert_not_called()
        
        # Verify None was returned
        self.assertIsNone(result)
        
    def test_handle_signal_with_order_creation_failure(self):
        """Test handling a signal with order creation failure."""
        # Mock signal data
        signal_data = {
            "strategy_id": "test_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_type": "entry",
            "strength": 0.8,
            "price": 50000.0,
            "quantity": 1.0,
        }
        
        # Mock signal aggregator response
        self.mock_signal_aggregator.process_signal.return_value = signal_data
        
        # Mock risk manager response
        self.mock_risk_manager.check_order_risk.return_value = True
        
        # Mock order manager to fail
        self.mock_order_manager.create_order.return_value = None
        
        # Call handle_signal
        result = self.execution_handler.handle_signal(signal_data)
        
        # Verify signal aggregator was called
        self.mock_signal_aggregator.process_signal.assert_called_once()
        
        # Verify risk manager was called
        self.mock_risk_manager.check_order_risk.assert_called_once()
        
        # Verify order manager was called
        self.mock_order_manager.create_order.assert_called_once()
        
        # Verify None was returned
        self.assertIsNone(result)
        
    def test_translate_signal_to_order(self):
        """Test translating a signal to order parameters."""
        # Test with explicit quantity
        signal_data = {
            "strategy_id": "test_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_type": "entry",
            "quantity": 1.0,
            "price": 50000.0,
        }
        
        result = self.execution_handler._translate_signal_to_order(signal_data)
        
        expected = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "LIMIT",
            "quantity": 1.0,
            "price": 50000.0,
        }
        
        self.assertEqual(result["symbol"], expected["symbol"])
        self.assertEqual(result["side"], expected["side"])
        self.assertEqual(result["type"], expected["type"])
        self.assertEqual(result["quantity"], expected["quantity"])
        self.assertEqual(result["price"], expected["price"])
        
        # Test with strength-based quantity
        self.mock_risk_manager.max_position_size = 100
        
        signal_data = {
            "strategy_id": "test_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_type": "entry",
            "strength": 0.5,
            "price": 50000.0,
        }
        
        result = self.execution_handler._translate_signal_to_order(signal_data)
        
        expected = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "LIMIT",
            "quantity": 50.0,  # 100 * 0.5
            "price": 50000.0,
        }
        
        self.assertEqual(result["symbol"], expected["symbol"])
        self.assertEqual(result["side"], expected["side"])
        self.assertEqual(result["type"], expected["type"])
        self.assertEqual(result["quantity"], expected["quantity"])
        self.assertEqual(result["price"], expected["price"])


if __name__ == "__main__":
    unittest.main()