"""Tests for the feature engineering module."""

import unittest
from unittest.mock import MagicMock, patch

from src.ml.feature_engineering import FeatureEngineer


class TestFeatureEngineer(unittest.TestCase):
    """Test cases for the FeatureEngineer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {
            "features": {}
        }
        
        # Create feature engineer with mock dependencies
        self.feature_engineer = FeatureEngineer(
            config=self.mock_config,
            logger=self.mock_logger,
        )
        
    def test_initialization(self):
        """Test feature engineer initialization."""
        # Verify config was accessed
        self.mock_config.get.assert_called_once_with("ml", {})
        
        # Verify logger was called
        self.mock_logger.info.assert_called_once()
        self.mock_logger.debug.assert_called_once()
        
    def test_extract_features(self):
        """Test extracting features."""
        # Test with sample market data
        market_data = {
            "symbol": "BTC/USDT",
            "timestamp": 1619712000000,
            "open": 54000.0,
            "high": 55000.0,
            "low": 53000.0,
            "close": 54500.0,
            "volume": 1000.0,
        }
        
        # Call extract_features
        result = self.feature_engineer.extract_features(market_data)
        
        # Verify logger was called
        self.mock_logger.debug.assert_called_with(f"Extracting features from: {market_data}")
        
        # Verify result is a dictionary
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()