"""Tests for the model manager module."""

import unittest
from unittest.mock import MagicMock, patch

from src.ml.model_manager import ModelManager


class TestModelManager(unittest.TestCase):
    """Test cases for the ModelManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock()
        self.mock_logger = MagicMock()
        
        # Configure mock config
        self.mock_config.get.return_value = {
            "models": {
                "model_dir": "models"
            }
        }
        
        # Create model manager with mock dependencies
        self.model_manager = ModelManager(
            config=self.mock_config,
            logger=self.mock_logger,
        )
        
    def test_initialization(self):
        """Test model manager initialization."""
        # Verify config was accessed
        self.mock_config.get.assert_called_once_with("ml", {})
        
        # Verify model directory was loaded
        self.assertEqual(self.model_manager.model_dir, "models")
        
        # Verify logger was called
        self.mock_logger.info.assert_called_once()
        self.mock_logger.debug.assert_called_once()
        
    def test_load_model(self):
        """Test loading a model."""
        # Call load_model
        model = self.model_manager.load_model("test_model")
        
        # Verify logger was called
        self.mock_logger.debug.assert_called_with("Loading model: test_model")
        
        # Verify model is returned
        self.assertIsInstance(model, dict)
        self.assertEqual(model["name"], "test_model")
        self.assertEqual(model["type"], "dummy")
        
    def test_predict(self):
        """Test making predictions."""
        # Create a dummy model and features
        model = {"name": "test_model", "type": "dummy"}
        features = {"feature1": 1.0, "feature2": 2.0}
        
        # Call predict
        prediction = self.model_manager.predict(model, features)
        
        # Verify logger was called
        self.mock_logger.debug.assert_called_with(
            f"Making prediction with model {model} using features: {features}"
        )
        
        # Verify prediction is returned
        self.assertIsInstance(prediction, dict)
        self.assertIn("prediction", prediction)
        self.assertIn("confidence", prediction)


if __name__ == "__main__":
    unittest.main()