# ADR-004: Structured NDJSON Logging

**Status:** Accepted  
**Date:** 2024-02-01  
**Deciders:** EgoShield Team

---

## Context

EgoShield needs comprehensive logging for:
- Debugging production issues
- Security audit trails
- Performance monitoring

We needed a logging format that is:
- Machine-parseable
- Human-readable
- Structured for queries
- Rotatable for disk management

---

## Decision

**Structured NDJSON (Newline-Delimited JSON) Logging**

Each log entry is a single-line JSON object:

```json
{"ts":"2024-01-01T12:00:00Z","level":"INFO","event":"analysis_complete","version":"3.0.0","data":{"analysis_id":"abc123","domain":"example.com"}}
```

---

## Format Specification

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `ts` | ISO8601 string | Timestamp in UTC |
| `level` | string | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `event` | string | Event name in snake_case |
| `version` | string | Daemon semver version |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `data` | object | Event-specific metadata |
| `exception` | object | If error, contains type and message |

### Example Events

```json
// Daemon startup
{"ts":"...","level":"INFO","event":"daemon_start","version":"3.0.0","data":{"port":8765}}

// Analysis complete
{"ts":"...","level":"INFO","event":"analysis_complete","version":"3.0.0","data":{"score":0.73}}

// Detector timeout
{"ts":"...","level":"WARNING","event":"detector_timeout","version":"3.0.0","data":{"detector":"gaslighting"}}

// Error
{"ts":"...","level":"ERROR","event":"unhandled_exception","version":"3.0.0","data":{"error":"..."},"exception":{"type":"ValueError","message":"..."}}
```

---

## Rationale

### NDJSON Benefits

- **Streaming**: Can tail with `tail -f` and process line-by-line
- **Append-only**: Perfect for log files
- **Splittable**: Easy to parse with `jq`, `grep`, etc.
- **No parsing errors**: One JSON per line, no multi-line issues

### Structured Benefits

- **Searchable**: Can query specific fields
- **Aggregatable**: Can group by event type
- **Typed**: Fields have known types

### Rotation

Using `RotatingFileHandler`:
- Max file size: 5MB
- Backup count: 5
- Total disk usage: 25MB max

---

## Implementation

### Formatter

```python
class StructuredLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "event": getattr(record, 'event', record.name),
            "version": self.version,
            "data": getattr(record, 'data', {})
        })
```

### PII Redaction

```python
def sanitize_for_logging(data: Any) -> Any:
    forbidden_keys = {'content', 'password', 'url', 'token', ...}
    if key.lower() in forbidden_keys:
        return "[REDACTED]"
```

---

## Consequences

### Positive

- Easy to search and analyze logs
- Can use standard JSON tools (jq, Python json module)
- Rotation prevents disk exhaustion
- Structured format enables dashboards

### Negative

- Larger log files than plain text
- Requires JSON parsing to read
- Some tools don't understand NDJSON natively

---

## Log Locations

| Platform | Path |
|----------|------|
| Linux | `~/.local/share/EgoShield/logs/daemon.log` |
| macOS | `~/Library/Logs/EgoShield/daemon.log` |
| Windows | `%APPDATA%/EgoShield/logs/daemon.log` |

---

## Related Decisions

- [ADR-001: Local-First Architecture](adr-001-local-first-architecture.md)