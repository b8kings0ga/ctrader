"""Tests for the risk manager."""

import unittest
from unittest.mock import MagicMock, patch

from src.risk.risk_manager import RiskManager


class TestRiskManager(unittest.TestCase):
    """Test cases for the RiskManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {
            "max_position_size": 100,
            "max_open_positions": 3,
            "max_order_quantity": 1.0,
            "stop_loss_percentage": 0.01,
            "daily_loss_limit": 50,
            "max_order_value_usd": 100.0,
        }
        
        # Create risk manager with mock dependencies
        self.risk_manager = RiskManager(
            config=self.mock_config,
            logger=self.mock_logger,
        )
        
    def test_initialization(self):
        """Test risk manager initialization."""
        # Verify config was accessed
        self.mock_config.get.assert_called_once_with("risk", {})
        
        # Verify risk parameters were loaded
        self.assertEqual(self.risk_manager.max_position_size, 100)
        self.assertEqual(self.risk_manager.max_open_positions, 3)
        self.assertEqual(self.risk_manager.max_order_quantity, 1.0)
        self.assertEqual(self.risk_manager.stop_loss_percentage, 0.01)
        self.assertEqual(self.risk_manager.daily_loss_limit, 50)
        self.assertEqual(self.risk_manager.max_order_value_usd, 100.0)
        
        # Verify logger was called
        self.mock_logger.info.assert_called_once()
        self.mock_logger.debug.assert_called_once()
        
    def test_check_order_risk_valid(self):
        """Test checking order risk with valid parameters."""
        # Test with valid order parameters (below max_order_quantity)
        order_params = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 0.5,  # Below max_order_quantity of 1.0
            "price": 50000.0,
        }
        
        # Call check_order_risk
        result = self.risk_manager.check_order_risk(order_params)
        
        # Verify logger was called
        self.mock_logger.debug.assert_called()
        
        # Verify True was returned for valid order
        self.assertTrue(result)
        
    def test_check_order_risk_exceeds_max_quantity(self):
        """Test checking order risk with quantity exceeding max_order_quantity."""
        # Test with order quantity exceeding max_order_quantity
        order_params = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 1.5,  # Exceeds max_order_quantity of 1.0
            "price": 50000.0,
        }
        
        # Call check_order_risk
        result = self.risk_manager.check_order_risk(order_params)
        
        # Verify warning was logged
        self.mock_logger.warning.assert_called()
        
        # Verify False was returned for invalid order
        self.assertFalse(result)
        
    def test_check_order_risk_exceeds_position_size(self):
        """Test checking order risk with position size exceeding max_position_size."""
        # Set up a large existing position
        self.risk_manager.positions = {"BTC/USDT": 90.0}
        
        # Test with order that would exceed max_position_size when combined with existing position
        order_params = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 20.0,  # Would result in position of 110, exceeding max of 100
            "price": 50000.0,
        }
        
        # Call check_order_risk
        result = self.risk_manager.check_order_risk(order_params)
        
        # Verify warning was logged
        self.mock_logger.warning.assert_called()
        
        # Verify False was returned for invalid order
        self.assertFalse(result)
        
    def test_update_position(self):
        """Test updating position tracking."""
        # Test buy order
        self.risk_manager.update_position("BTC/USDT", 1.0, "buy")
        self.assertEqual(self.risk_manager.positions["BTC/USDT"], 1.0)
        
        # Test another buy order
        self.risk_manager.update_position("BTC/USDT", 0.5, "buy")
        self.assertEqual(self.risk_manager.positions["BTC/USDT"], 1.5)
        
        # Test sell order
        self.risk_manager.update_position("BTC/USDT", 0.7, "sell")
        self.assertEqual(self.risk_manager.positions["BTC/USDT"], 0.8)
        
    def test_check_order_valid(self):
        """Test checking order with valid parameters (below max_order_value_usd)."""
        # Test action
        action = {
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.001,  # Small quantity
        }
        
        # Test latest prices
        latest_prices = {
            "BTC-USDT": 50000.0,  # Value = 0.001 * 50000 = 50 USD (below max of 100)
        }
        
        # Call check_order
        result = self.risk_manager.check_order(action, latest_prices)
        
        # Verify logger was called
        self.mock_logger.debug.assert_called()
        self.mock_logger.info.assert_called()
        
        # Verify True was returned for valid order
        self.assertTrue(result)
        
    def test_check_order_exceeds_max_value(self):
        """Test checking order with value exceeding max_order_value_usd."""
        # Test action
        action = {
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.003,  # Larger quantity
        }
        
        # Test latest prices
        latest_prices = {
            "BTC-USDT": 50000.0,  # Value = 0.003 * 50000 = 150 USD (exceeds max of 100)
        }
        
        # Call check_order
        result = self.risk_manager.check_order(action, latest_prices)
        
        # Verify warning was logged
        self.mock_logger.warning.assert_called()
        
        # Verify False was returned for invalid order
        self.assertFalse(result)
        
    def test_check_order_non_usd_quote(self):
        """Test checking order with non-USD quote currency."""
        # Test action
        action = {
            "symbol": "ETH-BTC",
            "side": "buy",
            "quantity": 10.0,
        }
        
        # Test latest prices
        latest_prices = {
            "ETH-BTC": 0.05,  # Cannot directly convert to USD
        }
        
        # Call check_order
        result = self.risk_manager.check_order(action, latest_prices)
        
        # Verify warning was logged about inability to calculate USD value
        self.mock_logger.warning.assert_called_with(
            "Cannot calculate USD value for ETH-BTC, allowing order for now."
        )
        
        # Verify True was returned (allowing the order for now)
        self.assertTrue(result)
        
    def test_check_order_missing_price(self):
        """Test checking order with missing price data."""
        # Test action
        action = {
            "symbol": "BTC-USDT",
            "side": "buy",
            "quantity": 0.001,
        }
        
        # Test latest prices (missing the required symbol)
        latest_prices = {
            "ETH-USDT": 3000.0,
        }
        
        # Call check_order
        result = self.risk_manager.check_order(action, latest_prices)
        
        # Verify warning was logged
        self.mock_logger.warning.assert_called_with(
            "Cannot assess risk for BTC-USDT: price not available"
        )
        
        # Verify False was returned (cannot assess risk without price)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()