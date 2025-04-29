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
            "stop_loss_percentage": 0.01,
            "daily_loss_limit": 50,
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
        self.assertEqual(self.risk_manager.stop_loss_percentage, 0.01)
        self.assertEqual(self.risk_manager.daily_loss_limit, 50)
        
        # Verify logger was called
        self.mock_logger.info.assert_called_once()
        self.mock_logger.debug.assert_called_once()
        
    def test_check_order_risk(self):
        """Test checking order risk."""
        # Test with various order parameters
        order_params = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "type": "limit",
            "quantity": 1.0,
            "price": 50000.0,
        }
        
        # Call check_order_risk
        result = self.risk_manager.check_order_risk(order_params)
        
        # Verify logger was called
        self.mock_logger.debug.assert_called()
        
        # Verify True was returned (always true in current implementation)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()