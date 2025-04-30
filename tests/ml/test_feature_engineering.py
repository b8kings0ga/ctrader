"""Tests for the feature engineering module."""

import unittest
from typing import List, Tuple
from unittest.mock import patch

# We need to patch the config_manager before importing FeatureEngineering
with patch('src.utils.config.config_manager'):
    from src.ml.feature_engineering import FeatureEngineering


class TestFeatureEngineering(unittest.TestCase):
    """Test cases for the FeatureEngineering class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.feature_engineering = FeatureEngineering()
        
        # Sample market data for testing
        self.sample_market_data = {
            'symbol': 'BTC/USDT',
            'bid': 60000.0,
            'ask': 60010.0,
            'bids': [(60000.0, 1.5), (59990.0, 2.0), (59980.0, 3.0), (59970.0, 2.5), (59960.0, 1.0), (59950.0, 0.5)],
            'asks': [(60010.0, 1.0), (60020.0, 1.5), (60030.0, 2.0), (60040.0, 2.5), (60050.0, 3.0), (60060.0, 1.0)]
        }
    
    def test_calculate_spread(self):
        """Test calculating bid-ask spread."""
        # Test with valid inputs
        spread = FeatureEngineering.calculate_spread(60000.0, 60010.0)
        self.assertEqual(spread, 10.0)
        
        # Test with equal bid and ask
        spread = FeatureEngineering.calculate_spread(60000.0, 60000.0)
        self.assertIsNone(spread)
        
        # Test with invalid inputs (bid > ask)
        spread = FeatureEngineering.calculate_spread(60010.0, 60000.0)
        self.assertIsNone(spread)
        
        # Test with None values
        spread = FeatureEngineering.calculate_spread(None, 60010.0)
        self.assertIsNone(spread)
        spread = FeatureEngineering.calculate_spread(60000.0, None)
        self.assertIsNone(spread)
    
    def test_calculate_mid_price(self):
        """Test calculating mid price."""
        # Test with valid inputs
        mid_price = FeatureEngineering.calculate_mid_price(60000.0, 60010.0)
        self.assertEqual(mid_price, 60005.0)
        
        # Test with None values
        mid_price = FeatureEngineering.calculate_mid_price(None, 60010.0)
        self.assertIsNone(mid_price)
        mid_price = FeatureEngineering.calculate_mid_price(60000.0, None)
        self.assertIsNone(mid_price)
    
    def test_calculate_book_imbalance(self):
        """Test calculating order book imbalance."""
        # Create test data
        bids: List[Tuple[float, float]] = [(60000.0, 1.5), (59990.0, 2.0), (59980.0, 3.0)]
        asks: List[Tuple[float, float]] = [(60010.0, 1.0), (60020.0, 1.5), (60030.0, 2.0)]
        
        # Test with valid inputs and default depth
        imbalance = FeatureEngineering.calculate_book_imbalance(bids, asks)
        # Expected: (1.5 + 2.0 + 3.0 + 0.0 + 0.0) / (1.5 + 2.0 + 3.0 + 1.0 + 1.5 + 2.0) = 6.5 / 11.0
        self.assertAlmostEqual(imbalance, 6.5 / 11.0)
        
        # Test with custom depth
        imbalance = FeatureEngineering.calculate_book_imbalance(bids, asks, depth=2)
        # Expected: (1.5 + 2.0) / (1.5 + 2.0 + 1.0 + 1.5) = 3.5 / 6.0
        self.assertAlmostEqual(imbalance, 3.5 / 6.0)
        
        # Test with empty lists
        imbalance = FeatureEngineering.calculate_book_imbalance([], asks)
        self.assertIsNone(imbalance)
        imbalance = FeatureEngineering.calculate_book_imbalance(bids, [])
        self.assertIsNone(imbalance)
        
        # Test with zero volumes
        zero_bids: List[Tuple[float, float]] = [(60000.0, 0.0), (59990.0, 0.0)]
        zero_asks: List[Tuple[float, float]] = [(60010.0, 0.0), (60020.0, 0.0)]
        imbalance = FeatureEngineering.calculate_book_imbalance(zero_bids, zero_asks)
        self.assertIsNone(imbalance)
    
    def test_generate_tick_features(self):
        """Test generating features from market data tick."""
        # Test with complete market data
        features = self.feature_engineering.generate_tick_features(self.sample_market_data)
        
        # Verify all expected features are present
        self.assertIn('spread', features)
        self.assertIn('mid_price', features)
        self.assertIn('book_imbalance_5', features)
        
        # Verify feature values
        self.assertEqual(features['spread'], 10.0)
        self.assertEqual(features['mid_price'], 60005.0)
        self.assertIsNotNone(features['book_imbalance_5'])
        
        # Test with partial market data (no order book)
        partial_data = {
            'symbol': 'BTC/USDT',
            'bid': 60000.0,
            'ask': 60010.0
        }
        features = self.feature_engineering.generate_tick_features(partial_data)
        
        # Verify basic features are present
        self.assertEqual(features['spread'], 10.0)
        self.assertEqual(features['mid_price'], 60005.0)
        self.assertIsNone(features['book_imbalance_5'])
        
        # Test with invalid market data
        invalid_data = {
            'symbol': 'BTC/USDT'
        }
        features = self.feature_engineering.generate_tick_features(invalid_data)
        
        # Verify all features are None
        self.assertIsNone(features['spread'])
        self.assertIsNone(features['mid_price'])
        self.assertIsNone(features['book_imbalance_5'])


if __name__ == "__main__":
    unittest.main()