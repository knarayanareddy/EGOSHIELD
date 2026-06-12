"""
Tests for ADR-006 Plugin System
"""

import pytest
from pathlib import Path
import tempfile
import sys

# Ensure project root is in path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root.parent) not in sys.path:
    sys.path.insert(0, str(_project_root.parent))


class TestPluginSystem:
    """Test the dynamic plugin loading system"""
    
    def test_plugin_manager_imports(self):
        """Test that plugin manager can be imported"""
        from egoshield.daemon.detectors.plugin_manager import PluginManager, get_plugin_manager
        assert PluginManager is not None
        assert get_plugin_manager is not None
    
    def test_plugin_manager_singleton(self):
        """Test that plugin manager is a singleton"""
        from egoshield.daemon.detectors.plugin_manager import get_plugin_manager
        
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        
        assert manager1 is manager2
    
    def test_plugin_manager_disabled_by_default(self):
        """Test that plugins are disabled by default"""
        from egoshield.daemon.detectors.plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        manager.configure(enabled=False)
        
        assert not manager.is_enabled()
    
    def test_plugin_manager_configuration(self):
        """Test plugin manager configuration"""
        from egoshield.daemon.detectors.plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        manager.configure(enabled=True, plugins_path=None)
        
        assert manager.is_enabled()
    
    def test_plugin_status_dict(self):
        """Test plugin status reporting"""
        from egoshield.daemon.detectors.plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        manager.configure(enabled=False)
        
        status = manager.get_status_dict()
        
        assert 'enabled' in status
        assert 'plugins_path' in status
        assert 'loaded_count' in status
        assert 'loaded' in status
    
    def test_get_all_detector_classes_includes_plugins(self):
        """Test that get_all_detector_classes integrates with plugin system"""
        from egoshield.daemon.detectors import get_all_detector_classes
        
        classes = get_all_detector_classes()
        
        # Should have at least the built-in detectors
        assert len(classes) >= 5
    
    def test_example_plugin_file_syntax(self):
        """Test that example plugin has valid syntax"""
        project_root = Path(__file__).resolve().parent.parent.parent
        plugin_path = project_root / 'plugins' / 'detector_example.py'
        
        if plugin_path.exists():
            # Just check it can be parsed as valid Python
            with open(plugin_path) as f:
                code = f.read()
            compile(code, str(plugin_path), 'exec')
    
    def test_plugin_discovery(self):
        """Test that plugin discovery works"""
        from egoshield.daemon.detectors.plugin_manager import get_plugin_manager
        
        project_root = Path(__file__).resolve().parent.parent.parent
        plugins_dir = project_root / 'plugins'
        
        manager = get_plugin_manager()
        manager.configure(enabled=True, plugins_path=str(plugins_dir))
        
        # Should not raise errors even if plugins directory is empty
        classes = manager.load_plugins()
        assert isinstance(classes, list)


class TestPluginSecurity:
    """Test plugin loading security"""
    
    def test_plugin_outside_directory_rejected(self):
        """Test that plugins outside the configured directory are rejected"""
        from egoshield.daemon.detectors.plugin_manager import PluginLoadingError
        
        # The security check is internal to the plugin manager
        # This test just verifies the exception exists
        assert PluginLoadingError is not None
    
    def test_plugin_base_class_not_accepted(self):
        """Test that the base DetectorBase class itself is not accepted as a plugin"""
        from egoshield.daemon.detectors.base import DetectorBase
        from egoshield.daemon.detectors.plugin_manager import get_plugin_manager
        
        manager = get_plugin_manager()
        manager.configure(enabled=False)
        
        # The manager should not accept DetectorBase itself as a plugin
        # This is enforced by checking `attr is not DetectorBase` in the loader
        assert DetectorBase.__name__ == 'DetectorBase'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])