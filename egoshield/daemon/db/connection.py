"""
EgoShield Database Connection Layer
Handles SQLite connection, WAL mode, and migrations
"""

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from ..utils.logging import log_event
from ..utils.project_paths import get_migrations_dir, get_db_schema_path, get_db_path

logger = logging.getLogger(__name__)


class Database:
    """Thread-safe SQLite database manager with WAL mode"""
    
    _instance: Optional['Database'] = None
    _lock = threading.Lock()
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or self._get_default_db_path()
        self._local = threading.local()
        self._ensure_directory()
        
    @staticmethod
    def _get_default_db_path() -> str:
        """Get the default database path based on OS"""
        return str(get_db_path())
    
    def _ensure_directory(self):
        """Ensure the database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # Set file permissions to 600 (owner read/write only)
        try:
            import os
            os.chmod(Path(self.db_path).parent, 0o700)
        except Exception:
            pass  # May not have permissions on all platforms
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            self._enable_wal_mode(self._local.conn)
        return self._local.conn
    
    @staticmethod
    def _enable_wal_mode(conn: sqlite3.Connection):
        """Enable WAL mode for concurrent reads during writes (ADR-002)"""
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=30000;")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def initialize(self):
        """Initialize database with schema and run migrations"""
        with self.get_connection() as conn:
            # Run schema initialization using robust path
            schema_path = get_db_schema_path()
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            
            log_event(logger, "INFO", "db_initialized", {
                "db_path": self.db_path,
                "schema_version": self.get_schema_version()
            })
    
    def get_schema_version(self) -> str:
        """Get current schema version"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
            return row['value'] if row else "0"
    
    def run_migrations(self):
        """Run pending database migrations"""
        # Use robust path resolution for migrations directory
        migrations_dir = get_migrations_dir()
        
        if not migrations_dir.exists():
            logger.info(f"Migrations directory not found at {migrations_dir}, skipping migrations")
            return
        
        current_version = int(self.get_schema_version())
        
        migration_files = sorted(migrations_dir.glob("*.sql"))
        
        for migration_file in migration_files:
            try:
                # Extract version number from filename (e.g., "001_init.sql" -> 1)
                version_str = migration_file.stem.split('_')[0]
                version = int(version_str)
            except (ValueError, IndexError):
                logger.warning(f"Could not parse migration version from {migration_file.name}")
                continue
            
            if version > current_version:
                with self.get_connection() as conn:
                    try:
                        conn.execute(f"-- migration: {migration_file.name}")
                        with open(migration_file, 'r') as f:
                            conn.executescript(f.read())
                        conn.execute(
                            "UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
                            (str(version),)
                        )
                        log_event(logger, "INFO", "migration_applied", {
                            "version": version,
                            "file": migration_file.name
                        })
                    except Exception as e:
                        log_event(logger, "CRITICAL", "migration_failed", {
                            "version": version,
                            "file": migration_file.name,
                            "error": str(e)
                        })
                        raise
    
    def retention_purge(self) -> tuple[int, int]:
        """Purge expired analyses and old metrics"""
        with self.get_connection() as conn:
            # Purge expired analyses
            cursor = conn.execute("""
                DELETE FROM analyses WHERE expires_at < datetime('now')
            """)
            analyses_deleted = cursor.rowcount
            
            # Purge old metrics (30 days)
            cursor = conn.execute("""
                DELETE FROM metrics WHERE created_at < datetime('now', '-30 days')
            """)
            metrics_deleted = cursor.rowcount
            
            log_event(logger, "INFO", "retention_purge", {
                "analyses_deleted": analyses_deleted,
                "metrics_deleted": metrics_deleted
            })
            
            return analyses_deleted, metrics_deleted
    
    def health_check(self) -> bool:
        """Verify database is writable"""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
                conn.execute("INSERT INTO metrics (event_type, metadata) VALUES ('health_check', '{}')")
                return True
        except Exception as e:
            log_event(logger, "ERROR", "sqlite_health_check_failed", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            return False
    
    def close(self):
        """Close all database connections"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# Global database instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get the global database instance"""
    global _db
    if _db is None:
        with Database._lock:
            if _db is None:
                _db = Database()
                _db.initialize()
    return _db


def init_db(db_path: Optional[str] = None) -> Database:
    """Initialize the database with a specific path"""
    global _db
    with Database._lock:
        _db = Database(db_path)
        _db.initialize()
        _db.run_migrations()
        _db.retention_purge()
    return _db