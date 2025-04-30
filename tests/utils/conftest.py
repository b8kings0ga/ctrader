"""Test configuration for utils tests."""

import os
import sys
from unittest.mock import Mock, patch

import pytest


# This fixture will be applied to all tests in this directory
@pytest.fixture(autouse=True, scope="session")
def patch_config_manager():
    """Patch the config_manager singleton for tests."""
    # Save the original module if it exists
    original_module = sys.modules.get('src.utils.config')
    
    # Create a mock for the config module
    mock_config = Mock()
    
    # Only patch if we're running tests for utils/test_config.py
    # This ensures we don't affect other tests
    if 'PYTEST_CURRENT_TEST' in os.environ and 'utils/test_config.py' not in os.environ['PYTEST_CURRENT_TEST']:
        # Apply the patch
        with patch.dict('sys.modules', {'src.utils.config': mock_config}):
            yield
    else:
        # Don't patch for test_config.py
        yield
    
    # Restore the original module if it existed
    if original_module:
        sys.modules['src.utils.config'] = original_module