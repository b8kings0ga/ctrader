"""Tests for the order manager."""

import unittest
from unittest.mock import MagicMock, patch

from src.execution.order_manager import OrderManager
from src.exchange.binance_connector import OrderRequest, OrderResponse


class TestOrderManager(unittest.TestCase):
    """Test cases for the OrderManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        self.mock_exchange_connector = MagicMock()
        
        # Create order manager with mock dependencies
        self.order_manager = OrderManager(
            config=self.mock_config,
            logger=self.mock_logger,
            exchange_connector=self.mock_exchange_connector,
        )
        
    def test_create_order_success(self):
        """Test creating an order successfully."""
        # Mock exchange connector response
        mock_response = MagicMock(spec=OrderResponse)
        mock_response.id = "test_order_id"
        mock_response.symbol = "BTC/USDT"
        mock_response.side = "buy"
        mock_response.type = "limit"
        mock_response.amount = 1.0
        mock_response.price = 50000.0
        mock_response.status = "open"
        mock_response.timestamp = 1619712345000
        mock_response.datetime = "2021-04-29T12:34:56.000Z"
        mock_response.dict = MagicMock(return_value={
            "id": "test_order_id",
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "amount": 1.0,
            "price": 50000.0,
            "status": "open",
            "timestamp": 1619712345000,
            "datetime": "2021-04-29T12:34:56.000Z",
        })
        
        self.mock_exchange_connector.create_order.return_value = mock_response
        
        # Call create_order
        order_id = self.order_manager.create_order(
            symbol="BTC/USDT",
            side="buy",
            type="limit",
            quantity=1.0,
            price=50000.0,
        )
        
        # Verify exchange connector was called with correct parameters
        self.mock_exchange_connector.create_order.assert_called_once()
        call_args = self.mock_exchange_connector.create_order.call_args[0][0]
        self.assertIsInstance(call_args, OrderRequest)
        self.assertEqual(call_args.symbol, "BTC/USDT")
        self.assertEqual(call_args.side, "buy")
        self.assertEqual(call_args.type, "limit")
        self.assertEqual(call_args.amount, 1.0)
        self.assertEqual(call_args.price, 50000.0)
        
        # Verify order ID was returned
        self.assertEqual(order_id, "test_order_id")
        
        # Verify order was added to active orders
        self.assertIn("test_order_id", self.order_manager.active_orders)
        
    def test_create_order_failure(self):
        """Test creating an order with failure."""
        # Mock exchange connector to raise an exception
        self.mock_exchange_connector.create_order.side_effect = Exception("Test error")
        
        # Call create_order
        order_id = self.order_manager.create_order(
            symbol="BTC/USDT",
            side="buy",
            type="limit",
            quantity=1.0,
            price=50000.0,
        )
        
        # Verify exchange connector was called
        self.mock_exchange_connector.create_order.assert_called_once()
        
        # Verify None was returned
        self.assertIsNone(order_id)
        
        # Verify error was logged
        self.mock_logger.error.assert_called_once()
        
    def test_cancel_order_success(self):
        """Test cancelling an order successfully."""
        # Mock exchange connector response
        self.mock_exchange_connector.cancel_order.return_value = {"id": "test_order_id", "status": "canceled"}
        
        # Add order to active orders
        self.order_manager.active_orders["test_order_id"] = {"id": "test_order_id", "status": "open"}
        
        # Call cancel_order
        result = self.order_manager.cancel_order("test_order_id", "BTC/USDT")
        
        # Verify exchange connector was called with correct parameters
        self.mock_exchange_connector.cancel_order.assert_called_once_with("test_order_id", "BTC/USDT")
        
        # Verify True was returned
        self.assertTrue(result)
        
        # Verify order was removed from active orders
        self.assertNotIn("test_order_id", self.order_manager.active_orders)
        
    def test_cancel_order_failure(self):
        """Test cancelling an order with failure."""
        # Mock exchange connector to raise an exception
        self.mock_exchange_connector.cancel_order.side_effect = Exception("Test error")
        
        # Add order to active orders
        self.order_manager.active_orders["test_order_id"] = {"id": "test_order_id", "status": "open"}
        
        # Call cancel_order
        result = self.order_manager.cancel_order("test_order_id", "BTC/USDT")
        
        # Verify exchange connector was called
        self.mock_exchange_connector.cancel_order.assert_called_once()
        
        # Verify False was returned
        self.assertFalse(result)
        
        # Verify error was logged
        self.mock_logger.error.assert_called_once()
        
    def test_get_order_status_from_cache(self):
        """Test getting order status from cache."""
        # Add order to active orders
        self.order_manager.active_orders["test_order_id"] = {"id": "test_order_id", "status": "open"}
        
        # Call get_order_status
        result = self.order_manager.get_order_status("test_order_id", "BTC/USDT")
        
        # Verify exchange connector was not called
        self.mock_exchange_connector.get_order.assert_not_called()
        
        # Verify correct result was returned
        self.assertEqual(result, {"id": "test_order_id", "status": "open"})
        
    def test_get_order_status_from_exchange(self):
        """Test getting order status from exchange."""
        # Mock exchange connector response
        self.mock_exchange_connector.get_order.return_value = {"id": "test_order_id", "status": "filled"}
        
        # Call get_order_status
        result = self.order_manager.get_order_status("test_order_id", "BTC/USDT")
        
        # Verify exchange connector was called with correct parameters
        self.mock_exchange_connector.get_order.assert_called_once_with("test_order_id", "BTC/USDT")
        
        # Verify correct result was returned
        self.assertEqual(result, {"id": "test_order_id", "status": "filled"})
        
    def test_get_open_orders(self):
        """Test getting open orders."""
        # Mock exchange connector response
        self.mock_exchange_connector.get_open_orders.return_value = [
            {"id": "order1", "status": "open"},
            {"id": "order2", "status": "open"},
        ]
        
        # Call get_open_orders
        result = self.order_manager.get_open_orders("BTC/USDT")
        
        # Verify exchange connector was called with correct parameters
        self.mock_exchange_connector.get_open_orders.assert_called_once_with("BTC/USDT")
        
        # Verify correct result was returned
        self.assertEqual(result, [{"id": "order1", "status": "open"}, {"id": "order2", "status": "open"}])
        
        # Verify orders were added to active orders
        self.assertIn("order1", self.order_manager.active_orders)
        self.assertIn("order2", self.order_manager.active_orders)
        
    def test_update_local_order_state(self):
        """Test updating local order state."""
        # Add order to active orders
        self.order_manager.active_orders["test_order_id"] = {"id": "test_order_id", "status": "open"}
        
        # Call update_local_order_state with closed status
        self.order_manager.update_local_order_state({"id": "test_order_id", "status": "closed"})
        
        # Verify order was removed from active orders
        self.assertNotIn("test_order_id", self.order_manager.active_orders)
        
        # Call update_local_order_state with open status
        self.order_manager.update_local_order_state({"id": "new_order_id", "status": "open"})
        
        # Verify order was added to active orders
        self.assertIn("new_order_id", self.order_manager.active_orders)


if __name__ == "__main__":
    unittest.main()