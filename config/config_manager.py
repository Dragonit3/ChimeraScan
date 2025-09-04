"""
Configuration Manager for ChimeraScan
====================================

Centralizes all configuration management following SOLID principles.
Ensures no hardcoded values throughout the application.
"""

import os
from typing import Optional, Union
from dotenv import load_dotenv


class ConfigManager:
    """
    Centralized configuration manager.
    Single source of truth for all application settings.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._load_environment()
            ConfigManager._initialized = True
    
    def _load_environment(self):
        """Load environment variables from .env file"""
        # Try to load from .env file in current directory
        load_dotenv('.env')
        
        # Also try common locations
        for env_path in ['.env', '../.env', '../../.env']:
            if os.path.exists(env_path):
                load_dotenv(env_path)
                break
    
    @property
    def timezone_offset(self) -> int:
        """
        Get timezone offset from environment.
        Returns UTC offset in hours (e.g., -3 for Brazil).
        """
        try:
            return int(os.getenv('UTC_OFFSET', '0'))
        except (ValueError, TypeError):
            return 0  # Default to UTC if parsing fails
    
    @property
    def timezone_name(self) -> str:
        """Get timezone name based on offset"""
        offset = self.timezone_offset
        if offset == 0:
            return "UTC"
        else:
            return f"UTC{offset:+d}"
    
    @property
    def timezone_description(self) -> str:
        """Get human-readable timezone description"""
        offset = self.timezone_offset
        if offset == 0:
            return "Coordinated Universal Time"
        else:
            return f"UTC offset: {offset} hours from UTC"
    
    @property
    def database_url(self) -> str:
        """Get database URL"""
        return os.getenv('DATABASE_URL', 'sqlite:///fraud_detection.db')
    
    @property
    def blacklist_database_url(self) -> str:
        """Get blacklist database URL"""
        return os.getenv('DATABASE_BLACKLIST_URL', 'sqlite:///blacklist.db')
    
    @property
    def ethereum_rpc_url(self) -> str:
        """Get Ethereum RPC URL"""
        return os.getenv('ETHEREUM_RPC_URL', '')
    
    @property
    def debug_mode(self) -> bool:
        """Get debug mode setting"""
        return os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes', 'on')
    
    @property
    def log_level(self) -> str:
        """Get log level"""
        return os.getenv('LOG_LEVEL', 'WARNING')
    
    @property
    def detection_threshold(self) -> float:
        """Get fraud detection threshold"""
        try:
            return float(os.getenv('DETECTION_THRESHOLD', '0.7'))
        except (ValueError, TypeError):
            return 0.7
    
    @property
    def high_value_threshold(self) -> float:
        """Get high value transaction threshold"""
        try:
            return float(os.getenv('HIGH_VALUE_THRESHOLD', '10000'))
        except (ValueError, TypeError):
            return 10000.0
    
    @property
    def update_interval_seconds(self) -> int:
        """Get update interval in seconds"""
        try:
            return int(os.getenv('UPDATE_INTERVAL_SECONDS', '5'))
        except (ValueError, TypeError):
            return 5
    
    def get_timezone_config(self) -> dict:
        """
        Get complete timezone configuration as dictionary.
        Used for API responses and frontend configuration.
        """
        return {
            "utc_offset": self.timezone_offset,
            "timezone_name": self.timezone_name,
            "description": self.timezone_description
        }
    
    def get_all_config(self) -> dict:
        """Get all configuration as dictionary"""
        return {
            "timezone": self.get_timezone_config(),
            "database_url": self.database_url,
            "blacklist_database_url": self.blacklist_database_url,
            "ethereum_rpc_url": self.ethereum_rpc_url,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
            "detection_threshold": self.detection_threshold,
            "high_value_threshold": self.high_value_threshold,
            "update_interval_seconds": self.update_interval_seconds
        }


# Global configuration instance
config = ConfigManager()
