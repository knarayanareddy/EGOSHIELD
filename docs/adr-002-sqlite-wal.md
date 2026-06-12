# ADR-002: SQLite with WAL Mode

**Status:** Accepted  
**Date:** 2024-01-15  
**Deciders:** EgoShield Team

---

## Context

EgoShield needs persistent storage for:
- Analysis history
- User rules
- Settings
- Metrics

We evaluated:
- **Option A**: SQLite (single file, simple)
- **Option B**: SQLite with WAL mode (better concurrency)
- **Option C**: PostgreSQL (network, complexity)
- **Option D**: NoSQL (overkill for our schema)

---

## Decision

**We chose Option B: SQLite with WAL Mode**

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;
PRAGMA busy_timeout=30000;
```

---

## Rationale

### Simplicity

- Single file database
- No server process required
- Easy backup and portability

### WAL Benefits

- **Concurrent reads during writes**: Users can query history while new analyses are being saved
- **Atomic transactions**: Data integrity guaranteed
- **Crash recovery**: WAL ensures no corruption
- **Performance**: Better than DELETE journal mode for concurrent access

### Suitability

- Single-user local application
- Read-heavy workload (many queries, fewer writes)
- Schema is well-defined and relational

---

## Consequences

### Positive

- Simple deployment (single file)
- Concurrent access handled correctly
- Crash-safe
- No database server to manage

### Negative

- File locking on Windows can be problematic
- Single-writer limitation (though WAL helps)
- Not suitable for multi-user scenarios

---

## Configuration

### Schema Version 2

```sql
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    url_hash TEXT NOT NULL,
    domain TEXT NOT NULL,
    composite_score REAL NOT NULL,
    severity_band TEXT NOT NULL,
    tactic_count INTEGER NOT NULL,
    partial_result INTEGER NOT NULL,
    arbiter_tier INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyses_domain ON analyses(domain);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_analyses_expires_at ON analyses(expires_at);
```

### Initialization

```python
# daemon/db/connection.py
def _enable_wal_mode(conn: sqlite3.Connection):
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=30000;")
```

---

## Migration Strategy

Migrations are SQL files in `migrations/` directory:

```
migrations/
├── 001_init.sql      # Schema v1
└── 002_add_plugins.sql  # Schema v2 (optional)
```

Applied automatically on startup based on `schema_meta.version`.

---

## Backup

Users can backup by copying:
- `~/.local/share/EgoShield/egoshield.db`
- `~/.local/share/EgoShield/egoshield.db-wal` (if exists)
- `~/.local/share/EgoShield/egoshield.db-shm` (if exists)

---

## Related Decisions

- [ADR-001: Local-First Architecture](adr-001-local-first-architecture.md)