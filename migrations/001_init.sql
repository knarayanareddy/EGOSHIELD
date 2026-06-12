-- Migration 001: Initial Schema (v1)
-- This migration is superseded by schema.sql (v2)
-- Kept for backward compatibility with v1 installations

-- Add new tables if they don't exist (v1 to v2 migration helper)

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    url_hash TEXT NOT NULL,
    domain TEXT NOT NULL,
    content_type TEXT NOT NULL,
    composite_score REAL NOT NULL CHECK (composite_score BETWEEN 0.0 AND 1.0),
    severity_band TEXT NOT NULL,
    tactic_count INTEGER NOT NULL DEFAULT 0,
    partial_result INTEGER NOT NULL DEFAULT 0,
    arbiter_tier INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analyses_domain ON analyses(domain);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);

CREATE TABLE IF NOT EXISTS tactics (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    detector_name TEXT NOT NULL,
    tactic_name TEXT NOT NULL,
    severity REAL NOT NULL,
    evidence_phrases TEXT NOT NULL,
    explanation TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tactics_analysis_id ON tactics(analysis_id);

-- Update schema version
INSERT OR REPLACE INTO schema_meta (key, value) VALUES ('schema_version', '1');