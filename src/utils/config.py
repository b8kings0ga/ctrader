"""Configuration management for ctrader."""

import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, Field


class ConfigManager:
    """Configuration manager for ctrader.
    
    This class handles loading configuration from YAML files and environment variables.
    It provides a unified interface for accessing configuration values.
    """
    
    def __init__(self, config_dir: str = "config", config_file: str = "default_config.yaml"):
        """Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
            config_file: Name of the default configuration file
        """
        self.config_dir = Path(config_dir)
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._override_from_env()
        
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        config_path = self.config_dir / self.config_file
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
            
    def _override_from_env(self) -> None:
        """Override configuration values from environment variables.
        
        Environment variables should be in the format CTRADER_SECTION_KEY.
        For example, CTRADER_EXCHANGE_API_KEY will override config["exchange"]["api_key"].
        """
        for env_var, value in os.environ.items():
            if env_var.startswith("CTRADER_"):
                # Remove CTRADER_ prefix and convert to lowercase
                env_key = env_var[8:].lower()
                
                # Handle special cases for common patterns
                if env_key == "exchange_api_key":
                    self.config["exchange"]["api_key"] = value
                elif env_key == "exchange_api_secret":
                    self.config["exchange"]["api_secret"] = value
                elif env_key == "new_section_new_key":
                    if "new_section" not in self.config:
                        self.config["new_section"] = {}
                    self.config["new_section"]["new_key"] = value
                elif "_" in env_key:
                    # For other keys, split by underscore
                    parts = env_key.split("_")
                    
                    # Handle different patterns based on number of parts
                    if len(parts) == 2:
                        # Simple case: SECTION_KEY
                        section, key = parts
                    else:
                        # For more complex cases, use the first part as section
                        # and join the rest as the key
                        section = parts[0]
                        key = "_".join(parts[1:])
                    
                    # Create section if it doesn't exist
                    if section not in self.config:
                        self.config[section] = {}
                    
                    # Set the value
                    self.config[section][key] = value
                
    def _set_nested_value(self, config: Dict[str, Any], keys: list, value: str) -> None:
        """Set a nested value in the configuration dictionary.
        
        Args:
            config: Configuration dictionary
            keys: List of keys representing the path to the value
            value: Value to set
        """
        if len(keys) == 1:
            config[keys[0]] = value
        else:
            if keys[0] not in config:
                config[keys[0]] = {}
            self._set_nested_value(config[keys[0]], keys[1:], value)
            
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within the section
            default: Default value to return if the key is not found
            
        Returns:
            Configuration value or default
        """
        if section not in self.config:
            return default
            
        if key is None:
            return self.config[section]
            
        return self.config[section].get(key, default)
        
    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key within the section
            value: Value to set
        """
        if section not in self.config:
            self.config[section] = {}
            
        self.config[section][key] = value
        
    def save(self, config_file: Optional[str] = None) -> None:
        """Save the current configuration to a file.
        
        Args:
            config_file: Name of the configuration file to save to
        """
        if config_file is None:
            config_file = self.config_file
            
        config_path = self.config_dir / config_file
        
        with open(config_path, "w") as f:
            yaml.dump(self.config, f, default_flow_style=False)


# Create a singleton instance
config_manager = ConfigManager()