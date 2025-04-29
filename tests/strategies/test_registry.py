"""Unit tests for the strategy registry."""

import unittest
from unittest.mock import MagicMock

from src.strategies import BaseStrategy, register_strategy, get_strategy_class, list_strategies, strategy_registry


# Create a mock strategy class for testing
class MockStrategy(BaseStrategy):
    """Mock strategy for testing."""
    
    def initialize(self, exchange_connector, data_cache):
        """Initialize the strategy."""
        pass
        
    def on_tick(self, market_data):
        """Process a market data tick."""
        pass
        
    def on_order_update(self, order_update):
        """Process an order update."""
        pass
        
    def on_error(self, error_data):
        """Process an error."""
        pass


class TestStrategyRegistry(unittest.TestCase):
    """Test cases for the strategy registry."""
    
    def setUp(self):
        """Set up the test case."""
        # Clear the registry before each test
        strategy_registry._strategies = {}
        
    def test_register_strategy(self):
        """Test registering a strategy."""
        # Register a strategy
        register_strategy("mock", MockStrategy)
        
        # Check that the strategy is registered
        self.assertIn("mock", strategy_registry._strategies)
        self.assertEqual(strategy_registry._strategies["mock"], MockStrategy)
        
    def test_register_duplicate_strategy(self):
        """Test registering a duplicate strategy."""
        # Register a strategy
        register_strategy("mock", MockStrategy)
        
        # Try to register the same strategy again
        with self.assertRaises(ValueError):
            register_strategy("mock", MockStrategy)
            
    def test_register_invalid_strategy(self):
        """Test registering an invalid strategy."""
        # Try to register a class that doesn't inherit from BaseStrategy
        with self.assertRaises(TypeError):
            register_strategy("invalid", MagicMock)
            
    def test_get_strategy_class(self):
        """Test getting a strategy class."""
        # Register a strategy
        register_strategy("mock", MockStrategy)
        
        # Get the strategy class
        strategy_class = get_strategy_class("mock")
        
        # Check that the correct class is returned
        self.assertEqual(strategy_class, MockStrategy)
        
    def test_get_nonexistent_strategy(self):
        """Test getting a nonexistent strategy."""
        # Try to get a strategy that doesn't exist
        with self.assertRaises(KeyError):
            get_strategy_class("nonexistent")
            
    def test_list_strategies(self):
        """Test listing all strategies."""
        # Register some strategies
        register_strategy("mock1", MockStrategy)
        register_strategy("mock2", MockStrategy)
        
        # List all strategies
        strategies = list_strategies()
        
        # Check that all strategies are listed
        self.assertEqual(len(strategies), 2)
        self.assertIn("mock1", strategies)
        self.assertIn("mock2", strategies)
        self.assertEqual(strategies["mock1"], MockStrategy)
        self.assertEqual(strategies["mock2"], MockStrategy)


if __name__ == "__main__":
    unittest.main()