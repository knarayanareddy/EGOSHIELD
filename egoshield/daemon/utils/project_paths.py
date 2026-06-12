"""
EgoShield Project Path Resolution
Provides robust path resolution that works regardless of directory nesting level.
Uses marker files to discover the project root dynamically.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Cache the project root once discovered
_project_root: Optional[Path] = None


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    The project root is the directory containing:
    - dashboard.html (the dashboard file)
    - Either: daemon/ (flat structure) OR egoshield/daemon/ (nested structure)
    - migrations/
    - setup.py / pyproject.toml (package metadata)
    
    This function works regardless of how deeply nested the calling module is,
    by traversing up from __file__ and searching for marker files.
    
    Returns:
        Path to the project root directory
    """
    global _project_root
    
    if _project_root is not None:
        return _project_root
    
    # Start from the directory containing this module
    current = Path(__file__).resolve().parent
    
    # Search upward for project root (max 15 levels to prevent infinite loops)
    for _ in range(15):
        # Check for dashboard.html at this level
        if (current / 'dashboard.html').exists():
            _project_root = current
            return _project_root
        
        # Move to parent directory
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    # Fallback: use the directory containing this file's package
    # This handles both flat (daemon/) and nested (egoshield/daemon/) structures
    current = Path(__file__).resolve().parent
    for _ in range(15):
        # If we find a 'daemon' directory at this level, check if parent has dashboard.html
        if current.name == 'daemon':
            if (current.parent / 'dashboard.html').exists():
                _project_root = current.parent
                return _project_root
            # Also check if 'daemon' itself contains dashboard.html (flat structure)
            if (current / 'dashboard.html').exists():
                _project_root = current
                return _project_root
        # Check for 'egoshield' package directory
        if current.name == 'egoshield':
            # Check if dashboard.html is in the parent (project root for nested structure)
            if (current.parent / 'dashboard.html').exists():
                _project_root = current.parent  # The actual project root
                return _project_root
            # Check if dashboard.html is in egoshield/ (alternative structure)
            if (current / 'dashboard.html').exists():
                _project_root = current
                return _project_root
        
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # Last resort: use the egoshield package parent as project root
    # This handles the egoshield/egoshield/ structure
    _project_root = Path(__file__).parent.parent.parent
    return _project_root


def get_daemon_dir() -> Path:
    """
    Get the daemon package directory.
    
    Handles both:
    - Flat structure: project_root/daemon/
    - Nested structure: project_root/egoshield/daemon/
    """
    root = get_project_root()
    
    # Check for flat structure first
    flat_daemon = root / 'daemon'
    if flat_daemon.exists() and (flat_daemon / '__init__.py').exists():
        return flat_daemon
    
    # Check for nested structure
    nested_daemon = root / 'egoshield' / 'daemon'
    if nested_daemon.exists() and (nested_daemon / '__init__.py').exists():
        return nested_daemon
    
    # Fallback: return root/daemon even if it doesn't exist
    return flat_daemon


def get_migrations_dir() -> Path:
    """Get the migrations directory"""
    return get_project_root() / 'migrations'


def get_dashboard_path() -> Path:
    """Get the path to dashboard.html"""
    return get_project_root() / 'dashboard.html'


def get_db_schema_path() -> Path:
    """Get the path to the database schema SQL file"""
    return get_daemon_dir() / 'db' / 'schema.sql'


def get_logs_dir() -> Path:
    """Get the logs directory for the platform"""
    import platform
    
    system = platform.system()
    
    if system == "Windows":
        base = Path(os.environ.get('APPDATA', Path.home() / "AppData"))
        return base / "EgoShield" / "logs"
    elif system == "Darwin":
        return Path.home() / "Library" / "Logs" / "EgoShield"
    else:  # Linux
        xdg = os.environ.get('XDG_DATA_HOME', str(Path.home() / ".local" / "share"))
        return Path(xdg) / "EgoShield" / "logs"


def get_db_path() -> Path:
    """Get the default database path for the platform"""
    import platform
    
    system = platform.system()
    home = Path.home()
    
    if system == "Windows":
        base = Path(os.environ.get('APPDATA', home / "AppData"))
        return base / "EgoShield" / "egoshield.db"
    elif system == "Darwin":
        return home / "Library" / "Application Support" / "EgoShield" / "egoshield.db"
    else:  # Linux
        xdg = Path(os.environ.get('XDG_DATA_HOME', home / ".local" / "share"))
        return xdg / "EgoShield" / "egoshield.db"


def get_extensions_dir() -> Path:
    """Get the extensions directory"""
    return get_project_root() / 'extension'