# EgoShield Security Documentation

**Version:** 3.0.0  
**Classification:** Internal

---

## Security Model Overview

EgoShield is designed with privacy and security as core principles. This document outlines the security measures implemented in the system.

## Threat Model

### Protected Assets

1. **User Privacy**: Content users view should not be transmitted externally
2. **Analysis Data**: Only metadata should be stored, not raw content
3. **System Integrity**: The daemon should not be exploitable for remote attacks

### Potential Threats

| Threat | Severity | Mitigation |
|--------|----------|------------|
| URL exfiltration | HIGH | Only SHA-256 hashes stored |
| Content logging | CRITICAL | Structured logging redacts content |
| Remote code execution | CRITICAL | Plugins disabled by default |
| Unauthorized API access | HIGH | Localhost-only binding |
| Extension ID spoofing | MEDIUM | Origin validation middleware |

---

## Network Security

### Localhost Binding

The daemon binds exclusively to `127.0.0.1`:

```python
# daemon/main.py
uvicorn.run(app, host="127.0.0.1", port=8765)
```

This prevents:
- Remote connections from other machines
- Network-based attacks
- Unauthorized API access

### CORS Configuration

Custom origin validation ensures only legitimate sources can access the API:

```python
# Valid origins:
# - chrome-extension://{extension_id}
# - moz-extension://{extension_id}
# - safari-extension://{extension_id}
# - http://127.0.0.1:8766
# - http://localhost:8766
```

### Rate Limiting

Sliding window rate limiter prevents abuse:

```python
# Default: 10 requests per 60 seconds per client
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10
```

---

## Data Privacy

### Forbidden Data

The following data types are **NEVER** logged or stored:

| Data Type | Rationale |
|-----------|-----------|
| Raw URLs | Privacy - could contain tokens/params |
| Page content | Privacy - user browsing data |
| Email bodies | Privacy - communication content |
| Credentials | Security - sensitive tokens |
| Form inputs | Privacy - could contain PII |

### Implemented Protections

```python
# daemon/utils/logging.py
def sanitize_for_logging(data: Any, max_length: int = 100) -> Any:
    forbidden_keys = {
        'content', 'body', 'text', 'password', 'credential',
        'token', 'secret', 'key', 'auth', 'email_body', 'page_text',
        'url', 'raw_url'
    }
    
    if key.lower() in forbidden_keys:
        return "[REDACTED]"
```

### URL Hashing

Raw URLs are never stored. Only SHA-256 hashes:

```python
# daemon/utils/security.py
def compute_url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()
```

### Evidence Phrases

Only short extracted phrases are stored, not full content:

```sql
-- Only tactics and evidence phrases, not content
INSERT INTO tactics (analysis_id, detector_name, tactic_name, severity, evidence_phrases)
VALUES (?, ?, ?, ?, ?);
```

---

## Plugin Security (ADR-006)

### Security Design

Plugins are disabled by default to prevent arbitrary code execution.

### Enable Process

1. User must explicitly enable: `plugins_enabled = 'true'`
2. User must specify path: `plugins_path = '/path/to/plugins'`
3. Restart required to load plugins

### File Restrictions

Only files matching the naming convention are loaded:

```python
# File must be: detector_*.py
for file_path in plugins_dir.glob(f"{PLUGIN_FILE_PREFIX}*.py"):
    # Load plugin
```

### Class Validation

Plugins must inherit from `DetectorBase`:

```python
# Reject if not a proper subclass
if issubclass(attr, DetectorBase) and attr is not DetectorBase:
    return attr  # Accept
```

### Path Traversal Prevention

Plugins cannot escape the configured directory:

```python
def _load_plugin_file(self, file_path: Path) -> Optional[Type[DetectorBase]]:
    # Security: Only load from the configured plugins directory
    resolved_path = file_path.resolve()
    if not str(resolved_path).startswith(str(self._plugins_path.resolve())):
        raise PluginLoadingError("Security violation: file outside plugins directory")
```

---

## Database Security

### File Permissions

Database directory is set to `0700` (owner only):

```python
os.chmod(db_path.parent, 0o700)
```

### WAL Mode

Write-Ahead Logging enables:
- Concurrent reads during writes
- Atomic transactions
- Crash recovery

### Retention Policy

Automatic expiration of old records:

```sql
DELETE FROM analyses WHERE expires_at < datetime('now')
```

---

## Extension Security

### Manifest V3

The extension uses Manifest V3 which provides:
- Limited background service worker lifetime
- No remote code execution
- Content script isolation

### Permissions

Minimal permissions requested:

```json
{
  "permissions": [
    "activeTab",
    "storage"
  ],
  "host_permissions": []
}
```

### Content Script Isolation

Content scripts cannot access:
- Extension background page directly
- Other tabs' content
- Chrome APIs not declared in manifest

---

## Logging Security

### Structured Logging Format

All logs are NDJSON with structured fields:

```json
{
  "ts": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "event": "analysis_complete",
  "version": "3.0.0",
  "data": {
    "analysis_id": "abc123...",
    "domain": "example.com"
    // Content NEVER logged here
  }
}
```

### Log Rotation

Prevents disk space exhaustion:
- Maximum file size: 5MB
- Maximum backups: 5
- Total log size: 25MB max

---

## Security Checklist

### Before Deployment

- [ ] Daemon binds to localhost only
- [ ] CORS origin validation enabled
- [ ] Rate limiting configured
- [ ] Plugin system disabled by default
- [ ] Database directory permissions set
- [ ] Log rotation configured

### During Development

- [ ] No raw URLs in logs
- [ ] No content in logs
- [ ] No credentials in code
- [ ] Plugin naming convention enforced
- [ ] Path traversal prevented

### Security Testing

```bash
# Run security-focused tests
python -m pytest tests/e2e/TestSecurityRequirements -v

# Check for credentials in code
grep -r "password\s*=" daemon/ --include="*.py"

# Verify no hardcoded secrets
ruff check daemon/ --select=SECRET,APIKEY
```

---

## Incident Response

### Suspected Breach

1. **Stop the daemon**: `pkill -f egoshield`
2. **Preserve logs**: Copy `~/.local/share/EgoShield/logs/`
3. **Check database**: Verify no unauthorized records
4. **Rotate credentials**: If any were involved
5. **Report**: Create security issue on GitHub

### Data Exposure

If sensitive data was logged:
1. Identify log entries
2. Delete log files
3. Clear database records if applicable
4. Review logging code for fixes

---

## Security Contacts

- **Maintainer**: team@egoshield.local
- **Security Issues**: Create private GitHub issue

---

## Acknowledgments

Security design inspired by:
- OWASP Privacy Principles
- Chrome Extension Security Best Practices
- SQLite Security Considerations