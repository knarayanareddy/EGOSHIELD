"""
EgoShield Structured Logging
NDJSON format logging with rotation to file
"""

import json
import logging
import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler

from .project_paths import get_logs_dir


class StructuredLogFormatter(logging.Formatter):
    """NDJSON formatter for structured logs"""
    
    def __init__(self, version: str = "2.0.0"):
        super().__init__()
        self.version = version
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "event": getattr(record, 'event', record.name.replace('.', '_')),
            "version": self.version,
            "data": getattr(record, 'data', {})
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None
            }
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Wrapper for structured logging with NDJSON output to rotating file.
    """
    
    _instances: Dict[str, logging.Logger] = {}
    _lock = threading.Lock()
    _log_dir: Optional[Path] = None
    
    def __init__(self, name: str, version: str = "2.0.0"):
        self.name = name
        self.version = version
        self._logger = self._get_logger(name, version)
    
    def _get_logger(self, name: str, version: str) -> logging.Logger:
        """Get or create a logger instance"""
        with self._lock:
            if name in StructuredLogger._instances:
                return StructuredLogger._instances[name]
            
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            
            # Remove existing handlers
            logger.handlers = []
            
            # Get log directory using robust path resolution
            log_dir = get_logs_dir()
            log_dir.mkdir(parents=True, exist_ok=True)
            StructuredLogger._log_dir = log_dir
            
            # Set file permissions to 600
            try:
                os.chmod(log_dir, 0o700)
            except Exception:
                pass
            
            # File handler with rotation - 5MB per file, max 5 files (25MB total)
            log_file = log_dir / "daemon.log"
            file_handler = RotatingFileHandler(
                str(log_file),
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(StructuredLogFormatter(version))
            logger.addHandler(file_handler)
            
            # Console handler (INFO level only for stdout)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(StructuredLogFormatter(version))
            logger.addHandler(console_handler)
            
            StructuredLogger._instances[name] = logger
            return logger
    
    def debug(self, event: str, data: Dict[str, Any] = None):
        self._log(logging.DEBUG, event, data)
    
    def info(self, event: str, data: Dict[str, Any] = None):
        self._log(logging.INFO, event, data)
    
    def warning(self, event: str, data: Dict[str, Any] = None):
        self._log(logging.WARNING, event, data)
    
    def error(self, event: str, data: Dict[str, Any] = None):
        self._log(logging.ERROR, event, data)
    
    def critical(self, event: str, data: Dict[str, Any] = None):
        self._log(logging.CRITICAL, event, data)
    
    def setLevel(self, level):
        """Set the logging level for all handlers"""
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.INFO)
        self._logger.setLevel(level)
        for handler in self._logger.handlers:
            handler.setLevel(level)
    
    def _log(self, level: int, event: str, data: Dict[str, Any] = None):
        """Internal log method"""
        extra = {
            'event': event,
            'data': data or {}
        }
        self._logger.log(level, event, extra=extra)


def setup_logging(version: str = "2.0.0") -> StructuredLogger:
    """
    Setup structured logging for the daemon.
    
    Configures:
    - Rotating file handler (5MB, 5 backups = 25MB max)
    - Console handler for stdout
    - NDJSON format output
    
    Returns a configured StructuredLogger.
    """
    logger = StructuredLogger("egoshield", version)
    
    # Configure root logger to not double-handle
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.DEBUG)
        # Only add our structured handlers, don't use basicConfig which creates default handlers
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredLogFormatter(version))
        root_logger.addHandler(handler)
    
    return logger


def log_event(logger, level: str, event: str, data: Dict[str, Any] = None):
    """
    Helper to log structured events.
    
    Args:
        logger: Logger instance (must be StructuredLogger)
        level: Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
        event: Event name (snake_case)
        data: Event data dict
    """
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(event, data)


def sanitize_for_logging(data: Any, max_length: int = 100) -> Any:
    """
    Sanitize data for logging by removing or truncating sensitive content.
    
    Per Section 7.4 - Forbidden Data:
    - Page content or email body: NEVER
    - Evidence phrase full text: MAY log length only
    - Credentials: NEVER
    - Raw URLs: MAY log hash only
    """
    if data is None:
        return None
    
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            # Never log these keys
            forbidden_keys = {
                'content', 'body', 'text', 'password', 'credential',
                'token', 'secret', 'key', 'auth', 'email_body', 'page_text',
                'url', 'raw_url'
            }
            
            if key.lower() in forbidden_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > max_length:
                sanitized[key] = value[:max_length] + "...[truncated]"
            else:
                sanitized[key] = sanitize_for_logging(value, max_length)
        
        return sanitized
    
    elif isinstance(data, list):
        return [sanitize_for_logging(item, max_length) for item in data]
    
    elif isinstance(data, str) and len(data) > max_length:
        return data[:max_length] + "...[truncated]"
    
    return data


def get_log_file_path() -> Optional[Path]:
    """Get the path to the current daemon log file"""
    if StructuredLogger._log_dir:
        return StructuredLogger._log_dir / "daemon.log"
    return None


def read_recent_logs(lines: int = 500) -> str:
    """
    Read recent lines from the daemon log file.
    
    Args:
        lines: Number of lines to read from the end
        
    Returns:
        String containing the recent log lines
    """
    log_file = get_log_file_path()
    if not log_file or not log_file.exists():
        return ""
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            return ''.join(all_lines[-lines:])
    except Exception:
        return ""