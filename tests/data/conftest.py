"""Test configuration for data tests."""

import sys
from unittest.mock import Mock, patch

import pytest


# This fixture will be applied to all tests in this directory
@pytest.fixture(autouse=True, scope="session")
def patch_config_manager():
    """Patch the config_manager singleton for data tests."""
    # Save the original module if it exists
    original_module = sys.modules.get('src.utils.config')
    
    # Create a mock for the config module
    mock_config = Mock()
    mock_config_manager = Mock()
    
    # Configure the mock module
    mock_config.config_manager = mock_config_manager
    mock_config.ConfigManager = Mock
    
    # Apply the patch
    with patch.dict('sys.modules', {'src.utils.config': mock_config}):
        yield
    
    # Restore the original module if it existed
    if original_module:
        sys.modules['src.utils.config'] = original_module