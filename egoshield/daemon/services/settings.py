"""
EgoShield Settings Service
Manages daemon and extension settings
"""

import logging
from typing import Dict, List, Optional

from ..db.connection import Database
from ..db.models import SettingsRepository
from ..utils.logging import log_event

logger = logging.getLogger(__name__)


class SettingsService:
    """
    Service for managing settings.
    
    Settings are stored in SQLite and control daemon behavior.
    """
    
    # Valid setting keys and their types
    VALID_SETTINGS = {
        'retention_days': 'int',
        'llm_threshold': 'float',
        'llm_timeout_ms': 'int',
        'detector_timeout_ms': 'int',
        'max_content_bytes': 'int',
        'dashboard_port': 'int',
        'daemon_port': 'int',
        'overlay_enabled': 'bool',
        'email_analysis_enabled': 'bool',
        # ADR-006: Plugin system settings
        'plugins_enabled': 'bool',
        'plugins_path': 'string',  # Path to custom detector plugins directory
    }
    
    def __init__(self, db: Database):
        self.db = db
        self.repo = SettingsRepository(db)
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value"""
        return self.repo.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer setting"""
        return self.repo.get_int(key, default)
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float setting"""
        return self.repo.get_float(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting"""
        return self.repo.get_bool(key, default)
    
    def set(self, key: str, value: str) -> bool:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value (will be validated)
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If key is invalid or value is wrong type
        """
        if key not in self.VALID_SETTINGS:
            raise ValueError(f"Unknown setting: {key}")
        
        # Type validation
        expected_type = self.VALID_SETTINGS[key]
        
        if expected_type == 'int':
            try:
                int(value)
            except ValueError:
                raise ValueError(f"Setting {key} requires integer value, got: {value}")
        
        elif expected_type == 'float':
            try:
                float(value)
            except ValueError:
                raise ValueError(f"Setting {key} requires float value, got: {value}")
        
        elif expected_type == 'bool':
            if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                raise ValueError(f"Setting {key} requires boolean value, got: {value}")
        
        elif expected_type == 'string':
            # String type accepts any non-empty value
            pass  # No validation needed for strings
        
        self.repo.set(key, value)
        return True
    
    def set_int(self, key: str, value: int):
        """Set an integer setting"""
        self.set(key, str(value))
    
    def set_float(self, key: str, value: float):
        """Set a float setting"""
        self.set(key, str(value))
    
    def set_bool(self, key: str, value: bool):
        """Set a boolean setting"""
        self.set(key, str(value).lower())
    
    def get_all(self) -> Dict[str, str]:
        """Get all settings as a dictionary"""
        return self.repo.get_all()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        defaults = {
            'retention_days': '90',
            'llm_threshold': '0.30',
            'llm_timeout_ms': '8000',
            'detector_timeout_ms': '2000',
            'max_content_bytes': '50000',
            'dashboard_port': '8766',
            'daemon_port': '8765',
            'overlay_enabled': 'true',
            'email_analysis_enabled': 'false',
            # ADR-006: Plugin system (disabled by default)
            'plugins_enabled': 'false',
            'plugins_path': '',
        }
        
        for key, value in defaults.items():
            self.repo.set(key, value)
        
        log_event(logger, "INFO", "settings_reset", {})
    
    def export_settings(self) -> Dict:
        """
        Export settings for diagnostics bundle.
        Per Section 11.4, does not include forbidden data.
        """
        return self.get_all()
    
    def validate_settings(self) -> Dict[str, List[str]]:
        """
        Validate all settings.
        
        Returns:
            Dict of issues by setting key
        """
        issues = {}
        
        all_settings = self.get_all()
        
        for key, expected_type in self.VALID_SETTINGS.items():
            if key not in all_settings:
                issues[key] = [f"Missing setting: {key}"]
                continue
            
            value = all_settings[key]
            
            # Check type
            try:
                if expected_type == 'int':
                    int(value)
                elif expected_type == 'float':
                    float(value)
                elif expected_type == 'bool':
                    if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
                        issues[key] = [f"Invalid boolean value: {value}"]
            except ValueError as e:
                issues[key] = [str(e)]
        
        # Check for unexpected settings
        for key in all_settings:
            if key not in self.VALID_SETTINGS:
                if key not in issues:
                    issues[key] = []
                issues[key].append(f"Unknown setting: {key}")
        
        return issues