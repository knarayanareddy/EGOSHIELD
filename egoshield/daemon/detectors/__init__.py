"""
EgoShield Detectors module

This module contains all built-in manipulation pattern detectors and
integrates with the dynamic plugin system (ADR-006) for custom detectors.
"""

from .base import DetectorBase, TacticResult, NormalizedContent
from .dark_pattern import DarkPatternDetector
from .emotional_manipulation import EmotionalManipulationDetector
from .urgency_inflation import UrgencyInflationDetector
from .gaslighting import GaslightingDetector
from .social_engineering import SocialEngineeringDetector
from .plugin_manager import PluginManager, get_plugin_manager, PluginLoadingError

# Registry of all built-in detectors
DETECTOR_REGISTRY = {
    "dark_pattern": DarkPatternDetector,
    "emotional_manipulation": EmotionalManipulationDetector,
    "urgency_inflation": UrgencyInflationDetector,
    "gaslighting": GaslightingDetector,
    "social_engineering": SocialEngineeringDetector,
}


def get_all_detector_classes() -> list:
    """
    Get all detector classes including dynamically loaded plugins.
    
    This function should be called after the plugin manager is configured
    and before running analysis.
    
    Returns:
        List of detector classes (built-in + plugins)
    """
    # Get built-in detector classes
    classes = list(DETECTOR_REGISTRY.values())
    
    # Get plugin detector classes
    plugin_manager = get_plugin_manager()
    if plugin_manager.is_enabled():
        try:
            plugin_classes = plugin_manager.load_plugins()
            classes.extend(plugin_classes)
        except PluginLoadingError as e:
            # Log but don't fail - built-in detectors still work
            import logging
            logging.getLogger(__name__).warning(f"Plugin loading failed: {e}")
    
    return classes


def get_builtin_detector_count() -> int:
    """Get the count of built-in detectors"""
    return len(DETECTOR_REGISTRY)


__all__ = [
    "DetectorBase",
    "TacticResult", 
    "NormalizedContent",
    "DarkPatternDetector",
    "EmotionalManipulationDetector",
    "UrgencyInflationDetector",
    "GaslightingDetector",
    "SocialEngineeringDetector",
    "PluginManager",
    "get_plugin_manager",
    "PluginLoadingError",
    "DETECTOR_REGISTRY",
    "get_all_detector_classes",
    "get_builtin_detector_count"
]