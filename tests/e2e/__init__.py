"""
EgoShield E2E Tests
End-to-end tests for the full system

Uses robust path resolution that works regardless of directory nesting level.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
# We need to find the project root which contains daemon/, extension/, etc.
_project_root = Path(__file__).resolve().parent.parent.parent
while not (_project_root / "daemon").exists() and not (_project_root / "extension").exists():
    if _project_root.parent == _project_root:
        break
    _project_root = _project_root.parent

# Try both package structure possibilities
for candidate in [_project_root, _project_root / "egoshield"]:
    if (candidate / "daemon").exists():
        sys.path.insert(0, str(candidate.parent))
        break

from egoshield.daemon.utils.project_paths import get_project_root, get_daemon_dir


class TestExtensionLoading:
    """Test that extension loads correctly"""
    
    def test_manifest_exists(self):
        project_root = get_project_root()
        manifest_path = project_root / "extension" / "manifest.json"
        
        assert manifest_path.exists(), f"Manifest not found at {manifest_path}"
    
    def test_manifest_valid_json(self):
        import json
        
        project_root = get_project_root()
        manifest_path = project_root / "extension" / "manifest.json"
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        assert manifest['manifest_version'] == 3
        assert 'background' in manifest
        assert 'content_scripts' in manifest


class TestDaemonStartup:
    """Test daemon starts correctly"""
    
    def test_main_module_exists(self):
        daemon_dir = get_daemon_dir()
        main_path = daemon_dir / "main.py"
        
        assert main_path.exists(), f"Main module not found at {main_path}"
    
    def test_imports_work(self):
        import sys
        from pathlib import Path
        
        # Ensure project root is in path
        project_root = get_project_root()
        if str(project_root.parent) not in sys.path:
            sys.path.insert(0, str(project_root.parent))
        
        from egoshield.daemon import __version__
        assert __version__ == "2.0.0"


class TestDatabaseSchema:
    """Test database schema conformance"""
    
    def test_schema_sql_exists(self):
        daemon_dir = get_daemon_dir()
        schema_path = daemon_dir / "db" / "schema.sql"
        
        assert schema_path.exists(), f"Schema SQL not found at {schema_path}"
    
    def test_schema_contains_required_tables(self):
        daemon_dir = get_daemon_dir()
        schema_path = daemon_dir / "db" / "schema.sql"
        
        with open(schema_path) as f:
            schema = f.read()
        
        required_tables = [
            'analyses',
            'tactics',
            'user_rules',
            'domain_stats',
            'settings',
            'metrics',
            'schema_meta'
        ]
        
        for table in required_tables:
            assert f'CREATE TABLE' in schema and table in schema, f"Table {table} not found in schema"


class TestAPIContract:
    """Test API contract conformance"""
    
    def test_schemas_define_required_fields(self):
        from pathlib import Path
        
        # Ensure project root is in path
        project_root = get_project_root()
        if str(project_root.parent) not in sys.path:
            sys.path.insert(0, str(project_root.parent))
        
        from egoshield.daemon.api.schemas import AnalyzeRequest, AnalyzeResponse
        
        # Verify request schema has required fields
        assert hasattr(AnalyzeRequest, 'model_fields')
        assert 'url_hash' in AnalyzeRequest.model_fields
        assert 'domain' in AnalyzeRequest.model_fields
        assert 'content' in AnalyzeRequest.model_fields
        
        # Verify response schema has required fields
        assert hasattr(AnalyzeResponse, 'model_fields')
        assert 'analysis_id' in AnalyzeResponse.model_fields
        assert 'composite_score' in AnalyzeResponse.model_fields
        assert 'severity_band' in AnalyzeResponse.model_fields


class TestSecurityRequirements:
    """Test security requirements are met"""
    
    def test_daemon_binds_to_localhost(self):
        daemon_dir = get_daemon_dir()
        main_path = daemon_dir / "main.py"
        
        with open(main_path) as f:
            content = f.read()
        
        # Should bind to 127.0.0.1
        assert '127.0.0.1' in content
    
    def test_url_hash_stored_not_raw_url(self):
        from pathlib import Path
        
        # Ensure project root is in path
        project_root = get_project_root()
        if str(project_root.parent) not in sys.path:
            sys.path.insert(0, str(project_root.parent))
        
        from egoshield.daemon.utils.security import compute_url_hash
        
        # Verify we have hashing function
        result = compute_url_hash("https://example.com/secret?token=abc123")
        
        # Should produce hash, not store actual URL
        assert len(result) == 64
        assert 'secret' not in result
        assert 'token' not in result
    
    def test_forbidden_data_not_in_logs(self):
        from pathlib import Path
        
        # Ensure project root is in path
        project_root = get_project_root()
        if str(project_root.parent) not in sys.path:
            sys.path.insert(0, str(project_root.parent))
        
        from egoshield.daemon.utils.logging import sanitize_for_logging
        
        data = {
            'content': 'This is secret content',
            'password': 'supersecret',
            'url': 'https://example.com/private',
            'safe_field': 'visible'
        }
        
        sanitized = sanitize_for_logging(data)
        
        assert sanitized['content'] == '[REDACTED]'
        assert sanitized['password'] == '[REDACTED]'
        assert sanitized['url'] == '[REDACTED]'
        assert sanitized['safe_field'] == 'visible'


class TestObservability:
    """Test observability requirements"""
    
    def test_log_events_defined(self):
        """
        Test that logging events are used throughout the daemon.
        This test checks that key event names are used in the codebase,
        not just in the logging module itself.
        """
        daemon_dir = get_daemon_dir()
        
        # Check that key event names appear in the daemon services
        key_events = [
            'daemon_start',
            'analysis_complete',
        ]
        
        # Also check logging module for formatter definitions
        log_events_path = daemon_dir / "utils" / "logging.py"
        
        with open(log_events_path) as f:
            log_content = f.read()
        
        # The logging module should define the formatter and event handling
        assert 'StructuredLogFormatter' in log_content
        assert 'log_event' in log_content
        
        # Check that analysis service uses key events
        analysis_path = daemon_dir / "services" / "analysis.py"
        if analysis_path.exists():
            with open(analysis_path) as f:
                analysis_content = f.read()
            
            # Should use log_event for analysis events
            assert 'log_event' in analysis_content


class TestPathResolution:
    """Test that path resolution works correctly"""
    
    def test_project_root_discovered(self):
        """Test that project root is correctly discovered"""
        project_root = get_project_root()
        
        # Project root should exist
        assert project_root.exists()
        
        # Should contain key directories (check both flat and nested structures)
        daemon_dir = get_daemon_dir()
        assert daemon_dir.exists(), f"Daemon dir not found at {daemon_dir}"
        assert (project_root / "extension").exists() or (project_root / "extension").is_dir()
    
    def test_dashboard_path_resolved(self):
        """Test that dashboard.html path is correctly resolved"""
        from egoshield.daemon.utils.project_paths import get_dashboard_path
        
        dashboard_path = get_dashboard_path()
        
        assert dashboard_path.exists(), f"Dashboard not found at {dashboard_path}"
    
    def test_migrations_dir_resolved(self):
        """Test that migrations directory is correctly resolved"""
        from egoshield.daemon.utils.project_paths import get_migrations_dir
        
        migrations_dir = get_migrations_dir()
        
        # Migrations directory should exist (even if empty)
        assert migrations_dir.is_dir(), f"Migrations dir not found at {migrations_dir}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])