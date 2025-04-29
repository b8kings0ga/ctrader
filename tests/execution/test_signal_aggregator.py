"""Tests for the signal aggregator."""

import unittest
from unittest.mock import MagicMock, patch

from src.execution.signal_aggregator import SignalAggregator


class TestSignalAggregator(unittest.TestCase):
    """Test cases for the SignalAggregator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        
        # Create signal aggregator with mock dependencies
        self.signal_aggregator = SignalAggregator(
            config=self.mock_config,
            logger=self.mock_logger,
        )
        
    def test_process_signal_valid(self):
        """Test processing a valid signal."""
        # Valid signal data
        signal_data = {
            "strategy_id": "test_strategy",
            "symbol": "BTC/USDT",
            "side": "buy",
            "signal_type": "entry",
            "strength": 0.8,
            "timestamp": 1619712345000,
        }
        
        # Process signal
        result = self.signal_aggregator.process_signal(signal_data)
        
        # Verify logger was called (once during init, once for the signal)
        self.assertEqual(self.mock_logger.info.call_count, 2)
        # Optionally, check the content of the second call
        # self.mock_logger.info.assert_called_with(f"Received signal: {signal_data}")
        
        # Verify signal was returned unchanged
        self.assertEqual(result, signal_data)
        
    def test_process_signal_missing_required_field(self):
        """Test processing a signal with missing required fields."""
        # Test each required field
        required_fields = ["strategy_id", "symbol", "side", "signal_type"]
        
        for field in required_fields:
            # Create signal data with missing field
            signal_data = {
                "strategy_id": "test_strategy",
                "symbol": "BTC/USDT",
                "side": "buy",
                "signal_type": "entry",
            }
            del signal_data[field]
            
            # Process signal
            result = self.signal_aggregator.process_signal(signal_data)
            
            # Verify warning was logged
            self.mock_logger.warning.assert_called()
            
            # Verify error was returned
            self.assertIn("error", result)
            self.assertIn(field, result["error"])
            
            # Reset mock
            self.mock_logger.reset_mock()


if __name__ == "__main__":
    unittest.main()