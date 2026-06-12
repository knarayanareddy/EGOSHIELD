# EgoShield API Reference

## Base URL

```
http://127.0.0.1:8765
```

## Versioning

All endpoints are versioned under `/api/v2/`. Breaking changes will increment the version.

## Headers

All requests must include:
- `Content-Type: application/json` (for POST/PUT)
- `X-EgoShield-Client: extension/{version}` (for analysis requests)

All responses include:
- `X-EgoShield-Daemon: {version}` (e.g., `2.0.0`)

## Endpoints

### Health Check

```
GET /health
```

Returns daemon health status.

**Response:**
```json
{
  "status": "healthy",
  "daemon_version": "2.0.0",
  "uptime_seconds": 3600
}
```

**Status values:**
- `healthy`: All systems operational
- `degraded`: Some subsystems unavailable (Ollama down, etc.)

---

### Readiness Check

```
GET /ready
```

Returns detailed readiness status for each subsystem.

**Response:**
```json
{
  "ready": true,
  "checks": {
    "sqlite": "ok",
    "detectors": "ok",
    "ollama": "unavailable"
  }
}
```

**Check values:**
- `ok`: Operational
- `unavailable`: Optional component not running
- `partial`: Some detectors timed out
- `error`: Critical failure

---

### Analyze Content

```
POST /api/v2/analyze
```

Analyzes content for manipulation patterns.

**Request:**
```json
{
  "url_hash": "sha256-hash-of-full-url",
  "domain": "example.com",
  "content_type": "page",
  "content": "visible text content...",
  "truncated": false,
  "client_timestamp": "2025-01-15T10:30:00Z"
}
```

**Constraints:**
- `content` must not exceed 50,000 bytes (configurable)
- `url_hash` must be SHA-256 hex string (64 chars)
- `domain` must be eTLD+1 format

**Response (200 OK):**
```json
{
  "analysis_id": "uuid-string",
  "composite_score": 0.65,
  "severity_band": "HIGH",
  "partial_result": false,
  "arbiter_tier": 3,
  "tactics": [
    {
      "detector_name": "dark_pattern",
      "tactic_name": "Fake Urgency",
      "severity": 0.8,
      "evidence_phrases": ["limited time offer", "act now"],
      "explanation": "Detected [Fake Urgency] pattern..."
    }
  ],
  "meta": {
    "daemon_version": "2.0.0",
    "analysis_duration_ms": 145,
    "detectors_run": 5,
    "detectors_timed_out": 0
  }
}
```

**Severity Bands:**
- `LOW`: 0.0 - 0.30
- `MEDIUM`: 0.30 - 0.60
- `HIGH`: 0.60 - 0.85
- `CRITICAL`: 0.85 - 1.0

**Error Responses:**
- `400 INVALID_PAYLOAD`: Missing or invalid fields
- `413 CONTENT_TOO_LARGE`: Content exceeds max size
- `422 VALIDATION_ERROR`: Schema validation failed
- `429 RATE_LIMITED`: More than 10 requests/minute
- `503 PIPELINE_UNAVAILABLE`: All detectors timed out

---

### Get Rules

```
GET /api/v2/rules
```

Returns all user rules.

**Response:**
```json
{
  "trusted_domains": ["trusted-site.com", "my-site.com"],
  "suppressed_tactics": ["Pity Appeal", "Superficial Compliment"],
  "custom_patterns": []
}
```

---

### Create Rule

```
POST /api/v2/rules
```

**Request:**
```json
{
  "rule_type": "trusted_domain",
  "value": "example.com",
  "notes": "Personal site"
}
```

**Rule Types:**
- `trusted_domain`: Skip analysis for this domain
- `suppress_tactic`: Hide this tactic from results
- `custom_pattern`: User-defined detection pattern

**Response:**
```json
{
  "id": "uuid-string",
  "rule_type": "trusted_domain",
  "value": "example.com",
  "notes": "Personal site",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### Delete Rule

```
DELETE /api/v2/rules/{rule_id}
```

**Response:**
```json
{
  "deleted": true
}
```

---

### Get Settings

```
GET /api/v2/settings
```

**Response:**
```json
{
  "settings": {
    "retention_days": "90",
    "llm_threshold": "0.30",
    "llm_timeout_ms": "8000",
    "detector_timeout_ms": "2000",
    "max_content_bytes": "50000",
    "dashboard_port": "8766",
    "daemon_port": "8765",
    "overlay_enabled": "true",
    "email_analysis_enabled": "false"
  }
}
```

---

### Update Setting

```
PUT /api/v2/settings
```

**Request:**
```json
{
  "key": "retention_days",
  "value": "180"
}
```

**Response:**
```json
{
  "updated": true,
  "key": "retention_days"
}
```

---

### Reset Settings

```
POST /api/v2/settings/reset
```

Resets all settings to defaults.

**Response:**
```json
{
  "reset": true
}
```

---

### Get Analysis History

```
GET /api/v2/history?limit=50&offset=0&domain=example.com
```

**Query Parameters:**
- `limit`: Number of results (default: 50, max: 100)
- `offset`: Pagination offset
- `domain`: Filter by domain (optional)

**Response:**
```json
{
  "analyses": [
    {
      "analysis_id": "uuid",
      "url_hash": "sha256...",
      "domain": "example.com",
      "content_type": "page",
      "composite_score": 0.65,
      "severity_band": "HIGH",
      "tactic_count": 3,
      "partial_result": false,
      "arbiter_tier": 3,
      "created_at": "2025-01-15T10:30:00Z",
      "tactics": [...]
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

### Get Dashboard Summary

```
GET /api/v2/dashboard
```

**Response:**
```json
{
  "total_analyses": 1250,
  "domain_stats": [...],
  "recent_analyses": [...],
  "tactic_distribution": [...],
  "llm_status": {
    "status": "healthy",
    "model": "llama3.2:3b",
    "available": true
  },
  "detectors": [
    {"name": "dark_pattern", "version": "1.0.0", "timeout_ms": 2000},
    ...
  ]
}
```

---

### Get Diagnostics

```
GET /api/v2/diagnostics
```

Returns diagnostics bundle for export.

**Response:**
```json
{
  "daemon_version": "2.0.0",
  "timestamp": "2025-01-15T10:30:00Z",
  "uptime_seconds": 3600,
  "schema_version": "2",
  "settings": {...},
  "metrics_summary": {...},
  "detector_versions": [...],
  "ollama_status": {...}
}
```

## Rate Limiting

The `/api/v2/analyze` endpoint is rate-limited to 10 requests per minute per client.

Exceeded limits return `429 RATE_LIMITED`.

## Version Compatibility

| Extension | Daemon | Compatible |
|-----------|--------|------------|
| 2.0.0 | 2.0.0 | ✅ Yes |
| 2.0.0 | 1.x | ⚠️ Warning |
| 1.x | 2.0.0 | ⚠️ Warning |

Major version mismatch triggers a warning in the extension UI.