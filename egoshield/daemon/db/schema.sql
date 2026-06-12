-- ============================================================
-- EgoShield SQLite Schema v2 (CANONICAL)
-- Single Source of Truth for all database structures
-- ============================================================

-- ============================================================
-- META
-- ============================================================
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', '2');
INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('created_at', datetime('now'));

-- ============================================================
-- ANALYSES
-- ============================================================
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    url_hash TEXT NOT NULL, -- SHA-256 of full URL; raw URL MUST NOT be stored
    domain TEXT NOT NULL, -- eTLD+1 only (e.g., example.com)
    content_type TEXT NOT NULL CHECK (content_type IN ('page', 'email', 'other')),
    composite_score REAL NOT NULL CHECK (composite_score BETWEEN 0.0 AND 1.0),
    severity_band TEXT NOT NULL CHECK (severity_band IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    tactic_count INTEGER NOT NULL DEFAULT 0,
    partial_result INTEGER NOT NULL DEFAULT 0, -- 1 if any detector timed out
    arbiter_tier INTEGER CHECK (arbiter_tier IN (1, 2, 3, NULL)),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL -- MUST be set to created_at + retention_days
);

CREATE INDEX IF NOT EXISTS idx_analyses_domain ON analyses(domain);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_analyses_expires_at ON analyses(expires_at);

-- ============================================================
-- TACTICS (child of analyses)
-- ============================================================
CREATE TABLE IF NOT EXISTS tactics (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    detector_name TEXT NOT NULL,
    tactic_name TEXT NOT NULL,
    severity REAL NOT NULL CHECK (severity BETWEEN 0.0 AND 1.0),
    evidence_phrases TEXT NOT NULL, -- JSON array of strings; MUST NOT be empty
    explanation TEXT, -- Arbiter output or template string
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tactics_analysis_id ON tactics(analysis_id);
CREATE INDEX IF NOT EXISTS idx_tactics_tactic_name ON tactics(tactic_name);

-- ============================================================
-- USER RULES
-- ============================================================
CREATE TABLE IF NOT EXISTS user_rules (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    rule_type TEXT NOT NULL CHECK (rule_type IN ('trusted_domain','suppress_tactic','custom_pattern')),
    value TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_rules_type_value ON user_rules(rule_type, value);

-- ============================================================
-- DOMAIN STATS (aggregate; no raw URLs stored)
-- ============================================================
CREATE TABLE IF NOT EXISTS domain_stats (
    domain TEXT PRIMARY KEY,
    total_analyses INTEGER NOT NULL DEFAULT 0,
    avg_composite_score REAL NOT NULL DEFAULT 0.0,
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- SETTINGS
-- ============================================================
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- CANONICAL default settings (MUST be inserted on first run):
INSERT OR IGNORE INTO settings (key, value) VALUES ('retention_days', '90');
INSERT OR IGNORE INTO settings (key, value) VALUES ('llm_threshold', '0.30');
INSERT OR IGNORE INTO settings (key, value) VALUES ('llm_timeout_ms', '8000');
INSERT OR IGNORE INTO settings (key, value) VALUES ('detector_timeout_ms', '2000');
INSERT OR IGNORE INTO settings (key, value) VALUES ('max_content_bytes', '50000');
INSERT OR IGNORE INTO settings (key, value) VALUES ('dashboard_port', '8766');
INSERT OR IGNORE INTO settings (key, value) VALUES ('daemon_port', '8765');
INSERT OR IGNORE INTO settings (key, value) VALUES ('overlay_enabled', 'true');
INSERT OR IGNORE INTO settings (key, value) VALUES ('email_analysis_enabled', 'false');
-- ADR-006 Plugin system settings (DISABLED by default for security)
INSERT OR IGNORE INTO settings (key, value) VALUES ('plugins_enabled', 'false');
INSERT OR IGNORE INTO settings (key, value) VALUES ('plugins_path', '');

-- ============================================================
-- METRICS (internal operability — see Section 11)
-- ============================================================
CREATE TABLE IF NOT EXISTS metrics (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    event_type TEXT NOT NULL,
    value_ms REAL,
    value_int INTEGER,
    metadata TEXT, -- JSON; MUST NOT contain user content
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_metrics_event_type ON metrics(event_type);
CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON metrics(created_at);