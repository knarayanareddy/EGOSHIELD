"""
EgoShield Dynamic Plugin System (ADR-006)
Allows loading custom detector plugins from user-specified directories.

Security Notes:
- Plugin loading is DISABLED by default
- Must be explicitly enabled via settings
- Only Python files following naming conventions are loaded
- Plugin classes must inherit from DetectorBase
- Plugin code execution happens in a restricted context

To enable: Set 'plugins_enabled' = 'true' and 'plugins_path' = '/path/to/plugins'
"""

import os
import sys
import importlib
import importlib.util
import logging
from pathlib import Path
from typing import List, Optional, Type, Dict
from threading import Lock

from .base import DetectorBase, TacticResult, NormalizedContent
from ..utils.logging import log_event
from ..utils.project_paths import get_project_root

logger = logging.getLogger(__name__)

# Plugin file naming convention: detector_*.py
PLUGIN_FILE_PREFIX = "detector_"
PLUGIN_CLASS_SUFFIX = "Detector"


class PluginLoadingError(Exception):
    """Raised when plugin loading fails"""
    pass


class PluginManager:
    """
    Manages dynamic loading of detector plugins.
    
    Thread-safe singleton implementation.
    """
    
    _instance: Optional['PluginManager'] = None
    _lock = Lock()
    
    def __init__(self):
        self._plugins: Dict[str, DetectorBase] = {}
        self._plugin_classes: List[Type[DetectorBase]] = []
        self._enabled = False
        self._plugins_path: Optional[Path] = None
        self._loaded = False
    
    @classmethod
    def get_instance(cls) -> 'PluginManager':
        """Get the singleton instance"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = PluginManager()
            return cls._instance
    
    def configure(self, enabled: bool, plugins_path: Optional[str] = None):
        """
        Configure the plugin system.
        
        Args:
            enabled: Whether plugin loading is enabled
            plugins_path: Path to the plugins directory (if enabled)
        """
        with self._lock:
            self._enabled = enabled
            if plugins_path:
                self._plugins_path = Path(plugins_path)
            else:
                # Default to user plugins directory
                project_root = get_project_root()
                self._plugins_path = project_root / "plugins"
            
            # Reset loaded state if configuration changed
            if self._loaded and enabled:
                logger.info("Plugin configuration updated, reload required")
    
    def is_enabled(self) -> bool:
        """Check if plugin loading is enabled"""
        return self._enabled
    
    def get_plugins_path(self) -> Optional[Path]:
        """Get the configured plugins directory path"""
        return self._plugins_path
    
    def load_plugins(self) -> List[Type[DetectorBase]]:
        """
        Load all valid detector plugins from the plugins directory.
        
        Returns:
            List of loaded plugin classes
            
        Raises:
            PluginLoadingError: If loading fails
        """
        if not self._enabled:
            logger.info("Plugin loading is disabled")
            return []
        
        if self._loaded:
            logger.info("Plugins already loaded")
            return self._plugin_classes
        
        if not self._plugins_path:
            logger.warning("No plugins path configured")
            return []
        
        if not self._plugins_path.exists():
            logger.warning(f"Plugins directory does not exist: {self._plugins_path}")
            # Create the directory structure for user convenience
            try:
                self._plugins_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created plugins directory: {self._plugins_path}")
            except Exception as e:
                logger.error(f"Failed to create plugins directory: {e}")
            return []
        
        loaded_classes: List[Type[DetectorBase]] = []
        errors: List[str] = []
        
        # Scan for Python files matching the detector naming convention
        for file_path in self._plugins_path.glob(f"{PLUGIN_FILE_PREFIX}*.py"):
            try:
                plugin_class = self._load_plugin_file(file_path)
                if plugin_class:
                    loaded_classes.append(plugin_class)
                    logger.info(f"Loaded plugin: {plugin_class.__name__} from {file_path.name}")
            except Exception as e:
                error_msg = f"Failed to load {file_path.name}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        if errors:
            log_event(logger, "WARNING", "plugin_loading_errors", {
                "errors": errors,
                "successful_loads": len(loaded_classes)
            })
        
        with self._lock:
            self._plugin_classes = loaded_classes
            self._loaded = True
        
        log_event(logger, "INFO", "plugins_loaded", {
            "count": len(loaded_classes),
            "path": str(self._plugins_path)
        })
        
        return loaded_classes
    
    def _load_plugin_file(self, file_path: Path) -> Optional[Type[DetectorBase]]:
        """
        Load a single plugin file and extract the detector class.
        
        Args:
            file_path: Path to the plugin Python file
            
        Returns:
            The detector class, or None if not found
        """
        # Security: Only load from the configured plugins directory
        resolved_path = file_path.resolve()
        if self._plugins_path:
            resolved_plugins_dir = self._plugins_path.resolve()
            if not str(resolved_path).startswith(str(resolved_plugins_dir)):
                raise PluginLoadingError(f"Security violation: file outside plugins directory")
        
        # Load the module dynamically
        module_name = f"egoshield_plugin_{file_path.stem}"
        
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise PluginLoadingError(f"Could not load spec for {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        
        # Add the plugins directory to sys.path temporarily for imports
        original_path = sys.path.copy()
        try:
            sys.path.insert(0, str(self._plugins_path))
            spec.loader.exec_module(module)
        finally:
            sys.path = original_path
        
        # Find the detector class in the module
        for attr_name in dir(module):
            if attr_name.endswith(PLUGIN_CLASS_SUFFIX):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, DetectorBase):
                    if attr is not DetectorBase:  # Don't accept the base class itself
                        return attr
        
        logger.warning(f"No detector class found in {file_path.name}")
        return None
    
    def instantiate_plugins(self) -> List[DetectorBase]:
        """
        Create instances of all loaded plugin detector classes.
        
        Returns:
            List of detector instances
        """
        if not self._loaded:
            self.load_plugins()
        
        instances = []
        for plugin_class in self._plugin_classes:
            try:
                instance = plugin_class()
                instances.append(instance)
            except Exception as e:
                logger.error(f"Failed to instantiate {plugin_class.__name__}: {e}")
        
        return instances
    
    def get_plugin_count(self) -> int:
        """Get the number of loaded plugins"""
        return len(self._plugin_classes)
    
    def reload(self):
        """Reload all plugins"""
        with self._lock:
            self._loaded = False
            self._plugin_classes = []
            self._plugins = {}
        
        return self.load_plugins()
    
    def get_status_dict(self) -> dict:
        """Get plugin system status as a dictionary"""
        return {
            "enabled": self._enabled,
            "plugins_path": str(self._plugins_path) if self._plugins_path else None,
            "loaded_count": self.get_plugin_count(),
            "loaded": self._loaded
        }


# Convenience function
def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance"""
    return PluginManager.get_instance()


# Example plugin template (for documentation purposes)
EXAMPLE_PLUGIN_CODE = '''
"""
Example Custom Detector Plugin

Place this file in your plugins directory as: detector_example.py

The filename must start with 'detector_' and contain a class ending with 'Detector'
that inherits from DetectorBase.
"""

import re
from typing import List
from daemon.detectors.base import DetectorBase, NormalizedContent, TacticResult


class ExampleDetector(DetectorBase):
    """
    Example custom detector for demonstration purposes.
    Detects custom manipulation patterns.
    """
    
    name = "example"
    version = "1.0.0"
    severity_weight = 0.5
    timeout_ms = 1000
    
    PATTERNS = {
        "custom_pattern": {
            "patterns": [
                r"(?i)example\\s+manipulation\\s+phrase",
            ],
            "severity_base": 0.6,
            "tactic_name": "Custom Manipulation"
        }
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        """Detect custom manipulation patterns"""
        results: List[TacticResult] = []
        text = normalized.cleaned_text
        
        if not text or len(text) < 10:
            return results
        
        for pattern_type, pattern_data in self.PATTERNS.items():
            all_evidence = []
            
            for pattern in pattern_data["patterns"]:
                try:
                    evidence = self._find_evidence_in_text(text, pattern)
                    if evidence:
                        all_evidence.extend(evidence)
                except re.error:
                    continue
            
            if all_evidence:
                seen = set()
                unique_evidence = []
                for e in all_evidence:
                    if e.lower() not in seen:
                        seen.add(e.lower())
                        unique_evidence.append(e)
                
                severity = self._calculate_severity(
                    pattern_data["severity_base"],
                    len(unique_evidence)
                )
                
                results.append(self._create_result(
                    tactic_name=pattern_data["tactic_name"],
                    severity=severity,
                    evidence_phrases=unique_evidence[:10],
                    matched_patterns=[pattern_type]
                ))
        
        return results
'''