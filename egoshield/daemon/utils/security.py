"""
EgoShield Security Utilities
Origin validation, input sanitization, credential management
"""

import hashlib
import re
import logging
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


class OriginValidator:
    """
    Validates request origins for the daemon API.
    Implements cross-origin request protection per Section 9.3.
    """
    
    # CANONICAL allowed origins
    DEFAULT_ALLOWED_ORIGINS: List[str] = [
        "chrome-extension://",
        "moz-extension://",
        "safari-extension://",
    ]
    
    def __init__(self, allowed_origins: List[str] = None, extension_ids: List[str] = None):
        """
        Initialize the origin validator.
        
        Args:
            allowed_origins: List of allowed origin prefixes
            extension_ids: List of valid extension IDs
        """
        self.allowed_origins = allowed_origins or self.DEFAULT_ALLOWED_ORIGINS.copy()
        self.extension_ids: Set[str] = set(extension_ids or [])
        
        # Add localhost dashboard
        self.allowed_origins.append("http://127.0.0.1:8766")
        self.allowed_origins.append("http://localhost:8766")
    
    def validate(self, origin: Optional[str], allowed_extension_id: Optional[str] = None) -> bool:
        """
        Validate an origin header.
        
        Args:
            origin: The Origin header value
            allowed_extension_id: The valid extension ID
            
        Returns:
            True if origin is valid, False otherwise
        """
        if not origin:
            return False
        
        # Check against allowed origin prefixes
        for allowed_prefix in self.allowed_origins:
            if origin.startswith(allowed_prefix):
                # For extension origins, validate the extension ID
                if allowed_prefix in ("chrome-extension://", "moz-extension://", "safari-extension://"):
                    # Extract extension ID from origin
                    ext_id = origin.replace(allowed_prefix, "").split("/")[0]
                    if self.extension_ids:
                        return ext_id in self.extension_ids
                    # If no specific IDs configured, allow any extension origin
                    return True
                
                # For localhost origins, validate port
                if origin.startswith("http://127.0.0.1") or origin.startswith("http://localhost"):
                    return self._validate_localhost_origin(origin)
                
                return True
        
        logger.warning(
            "origin_rejected",
            extra={
                'event': 'origin_rejected',
                'data': {
                    'origin': origin[:100],  # Log truncated
                    'endpoint': 'unknown'
                }
            }
        )
        return False
    
    def _validate_localhost_origin(self, origin: str) -> bool:
        """Validate localhost origin has correct port"""
        # Extract port from localhost origin
        match = re.match(r'http://(?:localhost|127\.0\.0\.1):(\d+)', origin)
        if match:
            port = int(match.group(1))
            # Only allow dashboard port
            return port == 8766
        return False
    
    def add_extension_id(self, extension_id: str):
        """Add a valid extension ID"""
        self.extension_ids.add(extension_id)
    
    def get_allowed_origins(self) -> List[str]:
        """Get list of all allowed origins"""
        return self.allowed_origins.copy()


def sanitize_content(content: str, max_length: int = 50000) -> str:
    """
    Sanitize and normalize content for analysis.
    
    Removes:
    - HTML tags
    - Extra whitespace
    - Control characters
    - Potentially dangerous content
    
    Args:
        content: Raw content string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized content string
    """
    if not content:
        return ""
    
    # Remove null bytes
    content = content.replace('\x00', '')
    
    # Remove control characters (except newlines and tabs)
    content = ''.join(char for char in content if char == '\n' or char == '\t' or ord(char) >= 32)
    
    # Strip HTML tags
    content = re.sub(r'<[^>]+>', ' ', content)
    
    # Decode common HTML entities
    html_entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'",
    }
    for entity, char in html_entities.items():
        content = content.replace(entity, char)
    
    # Normalize whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Trim
    content = content.strip()
    
    # Truncate if needed
    if len(content) > max_length:
        content = content[:max_length]
    
    return content


def compute_url_hash(url: str) -> str:
    """
    Compute SHA-256 hash of a URL.
    Per ADR-007, raw URLs must never be stored.
    
    Args:
        url: The full URL string
        
    Returns:
        SHA-256 hex digest of the URL
    """
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def extract_domain(url_or_host: str) -> str:
    """
    Extract eTLD+1 domain from a URL or hostname.
    
    Args:
        url_or_host: URL or hostname string
        
    Returns:
        eTLD+1 domain (e.g., "example.com")
    """
    from urllib.parse import urlparse
    
    # If it doesn't look like a URL, assume it's already a domain
    if not url_or_host.startswith(('http://', 'https://')):
        url_or_host = 'https://' + url_or_host
    
    try:
        parsed = urlparse(url_or_host)
        domain = parsed.netloc.lower()
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # Remove subdomains to get eTLD+1 (simplified)
        # For a full implementation, use tldextract library
        parts = domain.split('.')
        if len(parts) >= 2:
            # Assume last two parts are eTLD+1
            return '.'.join(parts[-2:])
        
        return domain
    except Exception:
        return url_or_host


def validate_content_type(content_type: str) -> bool:
    """
    Validate that content_type is a known type.
    
    Args:
        content_type: Content type string
        
    Returns:
        True if valid
    """
    valid_types = {'page', 'email', 'other'}
    return content_type.lower() in valid_types


def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize SQL identifiers to prevent injection.
    
    Args:
        identifier: SQL identifier (table name, column name)
        
    Returns:
        Sanitized identifier
        
    Raises:
        ValueError: If identifier is invalid
    """
    if not identifier:
        raise ValueError("Empty SQL identifier")
    
    # Only allow alphanumeric and underscore
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    
    return identifier


def check_content_safety(text: str) -> tuple[bool, List[str]]:
    """
    Check if content contains potentially unsafe elements.
    
    Per Section 7.4 - Forbidden Data:
    - Password fields
    - Payment card fields
    - Hidden inputs
    
    Args:
        text: Content to check
        
    Returns:
        Tuple of (is_safe, warnings)
    """
    warnings = []
    
    # Check for password-related content
    password_patterns = [
        r'password\s*[:=]',
        r'passwd',
        r'secret\s*[:=]',
        r'api[_-]?key\s*[:=]',
        r'token\s*[:=]',
        r'auth\s*[:=]',
    ]
    
    for pattern in password_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            warnings.append(f"Content may contain sensitive data (matched pattern: {pattern})")
    
    return len(warnings) == 0, warnings