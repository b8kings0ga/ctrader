"""Tests for the model manager module."""

import os
import unittest
from unittest.mock import patch, mock_open

from src.ml.model_manager import ModelManager


class TestModelManager(unittest.TestCase):
    """Test cases for the ModelManager class."""
    
    @patch('os.makedirs')
    def setUp(self, mock_makedirs):
        """Set up test fixtures."""
        # Create model manager with test directory
        self.test_model_dir = './test_models'
        self.model_manager = ModelManager(model_dir=self.test_model_dir)
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with(self.test_model_dir, exist_ok=True)
    
    def test_initialization(self):
        """Test model manager initialization."""
        # Verify model directory was set
        self.assertEqual(self.model_manager.model_dir, self.test_model_dir)
        
        # Verify model is None initially
        self.assertIsNone(self.model_manager.model)
    
    @patch('joblib.dump')
    def test_save_model(self, mock_dump):
        """Test saving a model."""
        # Create a dummy model
        dummy_model = {"type": "dummy_model"}
        model_name = "test_model"
        
        # Call save_model
        self.model_manager.save_model(dummy_model, model_name)
        
        # Verify joblib.dump was called with correct arguments
        expected_path = os.path.join(self.test_model_dir, f"{model_name}.joblib")
        mock_dump.assert_called_once_with(dummy_model, expected_path)
    
    @patch('os.path.exists')
    @patch('joblib.load')
    def test_load_model_success(self, mock_load, mock_exists):
        """Test loading a model successfully."""
        # Configure mocks
        mock_exists.return_value = True
        dummy_model = {"type": "dummy_model"}
        mock_load.return_value = dummy_model
        
        # Call load_model
        model_name = "test_model"
        result = self.model_manager.load_model(model_name)
        
        # Verify os.path.exists was called with correct path
        expected_path = os.path.join(self.test_model_dir, f"{model_name}.joblib")
        mock_exists.assert_called_once_with(expected_path)
        
        # Verify joblib.load was called with correct path
        mock_load.assert_called_once_with(expected_path)
        
        # Verify result is True
        self.assertTrue(result)
        
        # Verify model was stored
        self.assertEqual(self.model_manager.model, dummy_model)
    
    @patch('os.path.exists')
    def test_load_model_file_not_found(self, mock_exists):
        """Test loading a model when file doesn't exist."""
        # Configure mock
        mock_exists.return_value = False
        
        # Call load_model
        model_name = "nonexistent_model"
        result = self.model_manager.load_model(model_name)
        
        # Verify os.path.exists was called with correct path
        expected_path = os.path.join(self.test_model_dir, f"{model_name}.joblib")
        mock_exists.assert_called_once_with(expected_path)
        
        # Verify result is False
        self.assertFalse(result)
        
        # Verify model is None
        self.assertIsNone(self.model_manager.model)
    
    @patch('os.path.exists')
    @patch('joblib.load')
    def test_load_model_exception(self, mock_load, mock_exists):
        """Test loading a model when an exception occurs."""
        # Configure mocks
        mock_exists.return_value = True
        mock_load.side_effect = Exception("Test exception")
        
        # Call load_model
        model_name = "test_model"
        result = self.model_manager.load_model(model_name)
        
        # Verify result is False
        self.assertFalse(result)
        
        # Verify model is None
        self.assertIsNone(self.model_manager.model)
    
    def test_predict_no_model(self):
        """Test predicting when no model is loaded."""
        # Ensure no model is loaded
        self.model_manager.model = None
        
        # Call predict
        features = {"feature1": 1.0, "feature2": 2.0}
        prediction = self.model_manager.predict(features)
        
        # Verify prediction is None
        self.assertIsNone(prediction)
    
    def test_predict_with_model(self):
        """Test predicting with a loaded model."""
        # Set a dummy model
        self.model_manager.model = {"type": "dummy_model"}
        
        # Call predict
        features = {"feature1": 1.0, "feature2": 2.0}
        prediction = self.model_manager.predict(features)
        
        # Verify prediction is returned (should be 0.5 for the placeholder implementation)
        self.assertEqual(prediction, 0.5)


if __name__ == "__main__":
    unittest.main()