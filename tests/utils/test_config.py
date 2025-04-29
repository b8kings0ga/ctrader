"""Tests for the configuration manager."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

from src.utils.config import ConfigManager


@pytest.fixture
def config_file():
    """Create a temporary config file for testing."""
    # Ensure file is opened in text mode ('w') for yaml.dump
    with tempfile.NamedTemporaryFile(mode='w', suffix=".yaml", delete=False) as f:
        config = {
            "general": {
                "log_level": "INFO",
                "data_dir": "data",
            },
            "exchange": {
                "name": "binance",
                "api_key": "",
                "api_secret": "",
                "testnet": True,
            },
            "data": {
                "symbols": ["BTC/USDT", "ETH/USDT"],
                "timeframes": ["1m", "5m"],
            },
        }
        yaml.dump(config, f)
        
    yield Path(f.name)
    
    # Clean up
    os.unlink(f.name)


def test_config_manager_init(config_file):
    """Test ConfigManager initialization."""
    config_manager = ConfigManager(
        config_dir=str(config_file.parent),
        config_file=config_file.name,
    )
    
    assert config_manager.config is not None
    assert "general" in config_manager.config
    assert "exchange" in config_manager.config
    assert "data" in config_manager.config


def test_config_manager_get(config_file):
    """Test ConfigManager.get method."""
    config_manager = ConfigManager(
        config_dir=str(config_file.parent),
        config_file=config_file.name,
    )
    
    # Test getting a section
    general = config_manager.get("general")
    assert general is not None
    assert general["log_level"] == "INFO"
    
    # Test getting a key
    log_level = config_manager.get("general", "log_level")
    assert log_level == "INFO"
    
    # Test getting a key with default
    unknown_key = config_manager.get("general", "unknown_key", "default_value")
    assert unknown_key == "default_value"
    
    # Test getting an unknown section
    unknown_section = config_manager.get("unknown_section", default={})
    assert unknown_section == {}


def test_config_manager_set(config_file):
    """Test ConfigManager.set method."""
    config_manager = ConfigManager(
        config_dir=str(config_file.parent),
        config_file=config_file.name,
    )
    
    # Test setting a key in an existing section
    config_manager.set("general", "log_level", "DEBUG")
    assert config_manager.get("general", "log_level") == "DEBUG"
    
    # Test setting a key in a new section
    config_manager.set("new_section", "new_key", "new_value")
    assert config_manager.get("new_section", "new_key") == "new_value"


def test_config_manager_save(config_file):
    """Test ConfigManager.save method."""
    config_manager = ConfigManager(
        config_dir=str(config_file.parent),
        config_file=config_file.name,
    )
    
    # Modify the config
    config_manager.set("general", "log_level", "DEBUG")
    
    # Save the config
    config_manager.save()
    
    # Load the config again
    new_config_manager = ConfigManager(
        config_dir=str(config_file.parent),
        config_file=config_file.name,
    )
    
    # Check that the changes were saved
    assert new_config_manager.get("general", "log_level") == "DEBUG"


def test_config_manager_override_from_env(config_file):
    """Test ConfigManager._override_from_env method."""
    # Set environment variables
    with mock.patch.dict(os.environ, {
        "CTRADER_EXCHANGE_API_KEY": "test_api_key",
        "CTRADER_EXCHANGE_API_SECRET": "test_api_secret",
        "CTRADER_NEW_SECTION_NEW_KEY": "new_value",
    }):
        config_manager = ConfigManager(
            config_dir=str(config_file.parent),
            config_file=config_file.name,
        )
        
        # Check that environment variables override config values
        assert config_manager.get("exchange", "api_key") == "test_api_key"
        assert config_manager.get("exchange", "api_secret") == "test_api_secret"
        
        # Check that environment variables can create new sections and keys
        assert config_manager.get("new_section", "new_key") == "new_value"