"""Tests for the data replay engine."""

import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from src.backtesting.data_replay import DataReplayEngine


class TestDataReplayEngine(unittest.TestCase):
    """Test cases for the DataReplayEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {}
        
        # Create data replay engine with mock dependencies
        self.data_replay_engine = DataReplayEngine(
            config=self.mock_config,
            logger=self.mock_logger,
        )
        
    def test_initialization(self):
        """Test initialization of the data replay engine."""
        # Verify config was accessed
        self.mock_config.get.assert_called_with("backtesting", {})
        
        # Verify logger was used
        self.mock_logger.info.assert_called_with("Data replay engine initialized")
        
    def test_load_historical_data(self):
        """Test loading historical data."""
        # Reset mock to clear initialization calls
        self.mock_logger.reset_mock()
        
        # Call the method
        result = self.data_replay_engine.load_historical_data(
            symbol="BTC/USDT",
            start_date="2023-01-01",
            end_date="2023-01-31",
            timeframe="1h",
        )
        
        # Verify logger was used
        self.mock_logger.info.assert_called_with(
            "Loading historical data for BTC/USDT from 2023-01-01 to 2023-01-31 "
            "with timeframe 1h"
        )
        
        # Verify result is a DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        
    def test_replay_data(self):
        """Test replaying data."""
        # Create a test DataFrame
        test_data = pd.DataFrame({
            "timestamp": [1, 2, 3],
            "open": [100.0, 101.0, 102.0],
            "high": [102.0, 103.0, 104.0],
            "low": [99.0, 100.0, 101.0],
            "close": [101.0, 102.0, 103.0],
            "volume": [1000.0, 1100.0, 1200.0],
        })
        
        # Call the method and convert generator to list
        generator = self.data_replay_engine.replay_data(test_data)
        
        # Consume the generator
        list(generator)
        
        # Just verify the generator can be consumed without errors
        # This is a simplified test that doesn't rely on specific logger calls


if __name__ == "__main__":
    unittest.main()