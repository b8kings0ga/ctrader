"""Unit tests for the base strategy."""

import unittest
from unittest.mock import MagicMock, patch

from src.strategies import BaseStrategy


# Create a concrete strategy class for testing
class ConcreteStrategy(BaseStrategy):
    """Concrete strategy for testing."""
    
    def initialize(self, exchange_connector, data_cache):
        """Initialize the strategy."""
        self.exchange = exchange_connector
        self.data_cache = data_cache
        
    def on_tick(self, market_data):
        """Process a market data tick."""
        pass
        
    def on_order_update(self, order_update):
        """Process an order update."""
        pass
        
    def on_error(self, error_data):
        """Process an error."""
        pass


class TestBaseStrategy(unittest.TestCase):
    """Test cases for the base strategy."""
    
    @patch("src.strategies.base_strategy.config_manager")
    def test_init_with_default_config(self, mock_config_manager):
        """Test initializing a strategy with default config."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "enabled": True,
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
        }
        
        # Initialize a strategy
        strategy = ConcreteStrategy("test_strategy")
        
        # Check that the strategy is initialized correctly
        self.assertEqual(strategy.strategy_id, "test_strategy")
        self.assertIsNotNone(strategy.logger)
        self.assertEqual(strategy.config, {
            "enabled": True,
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
        })
        
        # Check that the config manager was called correctly
        mock_config_manager.get.assert_called_once_with("strategies", "concrete", {})
        
    @patch("src.strategies.base_strategy.config_manager")
    def test_init_with_custom_config(self, mock_config_manager):
        """Test initializing a strategy with custom config."""
        # Mock the config manager
        mock_config_manager.get.return_value = {
            "enabled": True,
            "min_profit_threshold": 0.001,
            "max_trade_amount": 100,
        }
        
        # Custom config
        custom_config = {
            "enabled": False,
            "min_profit_threshold": 0.002,
            "custom_param": "value",
        }
        
        # Initialize a strategy with custom config
        strategy = ConcreteStrategy("test_strategy", custom_config)
        
        # Check that the strategy is initialized correctly
        self.assertEqual(strategy.strategy_id, "test_strategy")
        self.assertIsNotNone(strategy.logger)
        
        # Check that the custom config overrides the default config
        expected_config = {
            "enabled": False,  # Overridden
            "min_profit_threshold": 0.002,  # Overridden
            "max_trade_amount": 100,  # From default config
            "custom_param": "value",  # Added
        }
        self.assertEqual(strategy.config, expected_config)
        
    def test_initialize(self):
        """Test initializing a strategy with components."""
        # Create mock components
        mock_exchange = MagicMock()
        mock_data_cache = MagicMock()
        
        # Initialize a strategy
        strategy = ConcreteStrategy("test_strategy")
        strategy.initialize(mock_exchange, mock_data_cache)
        
        # Check that the components are set correctly
        self.assertEqual(strategy.exchange, mock_exchange)
        self.assertEqual(strategy.data_cache, mock_data_cache)


if __name__ == "__main__":
    unittest.main()