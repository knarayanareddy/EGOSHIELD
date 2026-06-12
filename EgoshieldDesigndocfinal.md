> ⚠️ **Note:** This document is generated purely from architectural analysis of the existing design docs and the improvement framework discussed. It does not pull from the live repos at generation time — treat section-level implementation details (schemas, API shapes, etc.) as **canonical directives** to reconcile against your current codebase. Anything marked `[OWNER TO CONFIRM]` requires a human decision before this doc is `Approved`.

---

# EgoShield — Production Engineering Specification

---

```yaml
title:         EgoShield — Production Engineering Specification
version:       2.0.0
status:        DRAFT → requires sign-off to become APPROVED / SSOT
owner:         [OWNER TO CONFIRM]
authors:       [OWNER TO CONFIRM]
reviewers:     [OWNER TO CONFIRM — Security, Privacy, Platform, QA leads]
created:       2025
last_updated:  [DATE]
next_review:   [DATE + 90 days]
compatibility: Extension <-> Daemon API v2; SQLite schema v2
license:       [OWNER TO CONFIRM]
jurisdiction:  [OWNER TO CONFIRM — affects data retention and privacy obligations]
```

---

## ⚠️ Pre-Production Human Actions Required

The following items MUST be resolved by a named human owner before this document transitions from `DRAFT` to `APPROVED` and before any production deployment:

| # | Action | Owner | Blocker for |
|---|--------|-------|-------------|
| 1 | Confirm jurisdiction and applicable privacy law (GDPR, CCPA, PIPEDA, etc.) | `[OWNER]` | Section 9 |
| 2 | Confirm encryption key derivation mechanism and OS keychain integration per platform | `[OWNER]` | Section 9.4 |
| 3 | Sign off on data retention defaults and purge policy | `[OWNER]` | Section 9.5 |
| 4 | Confirm extension store (Chrome Web Store, Firefox AMO, etc.) and code signing strategy | `[OWNER]` | Section 13 |
| 5 | Confirm minimum hardware spec for Ollama models | `[OWNER]` | ADR-004 |
| 6 | Confirm threat model mitigations are implemented before first public release | `[OWNER]` | Section 10 |
| 7 | Review and approve all ADRs — mark each as ACCEPTED or SUPERSEDED | `[OWNER]` | Section 15 |

---

## Changelog

| Version | Date | Author | Summary |
|---------|------|--------|---------|
| 1.0.0 | [original date] | [original author] | Initial architecture + implementation design |
| 2.0.0 | [current date] | [author] | Full production-spec retrofit: governance, ADRs, threat model, observability plan, testing pyramid, release/upgrade story, RFC-2119 normative language, compatibility contracts |

---

## Table of Contents

1. [Purpose & Scope](#1)
2. [Normative Language](#2)
3. [Product Philosophy](#3)
4. [Goals, Non-Goals & Constraints](#4)
5. [System Architecture](#5)
6. [Component Specifications](#6)
7. [Data Architecture](#7)
8. [API Contract — Extension ↔ Daemon](#8)
9. [Security & Privacy Specification](#9)
10. [Threat Model](#10)
11. [Observability & Operability](#11)
12. [Testing Specification](#12)
13. [Release, Packaging & Upgrade](#13)
14. [Non-Functional Requirements (Acceptance Criteria)](#14)
15. [Architecture Decision Records (ADRs)](#15)
16. [Glossary](#16)

---

<a name="1"></a>
## 1. Purpose & Scope

### 1.1 Purpose

This document is the **single source of truth (SSOT)** for the engineering design, operational posture, and production readiness of EgoShield. It is a **directive, not a description**: it defines what MUST be built, what MUST be enforced, and how the system MUST behave under normal and failure conditions.

Any implementation that contradicts this document is a defect. Any change to this document that touches a section marked `[REQUIRES ADR]` MUST produce a corresponding ADR entry in Section 15 before the change is merged.

### 1.2 What is EgoShield?

EgoShield is a **local-first, privacy-preserving cognitive shield** that runs in the browser and on the user's machine to detect, annotate, and explain manipulative communication patterns — dark patterns, emotional manipulation tactics, gaslighting, urgency inflation, and social engineering signals — in real time.

It operates as:
- A **browser extension** (MV3) that captures page/email content and renders overlay annotations
- A **local FastAPI daemon** that hosts all detection, scoring, and persistence logic
- An **optional local LLM arbiter** (via Ollama) that provides natural-language explanations
- An **optional desktop dashboard** for historical analysis, rules, and settings

**EgoShield is a mirror, not a muzzle.** It annotates; it does not block.

### 1.3 Scope of this Document

**In scope:**
- All components of the EgoShield system as described above
- Extension ↔ Daemon API contract (versioned)
- SQLite schema (canonical)
- Security controls, threat model, and privacy obligations
- Observability, testing, and release strategy

**Out of scope:**
- External LLM providers (EgoShield MUST remain local-first; no cloud inference)
- Browser-vendor-specific store policies (reference Section 13 for signing; store submission is operational)
- User-facing feature roadmap beyond engineering scope

---

<a name="2"></a>
## 2. Normative Language

This document uses normative language per **RFC 2119**:

| Keyword | Meaning |
|---------|---------|
| **MUST** / **MUST NOT** | Absolute requirement. Non-compliance = defect. |
| **SHOULD** / **SHOULD NOT** | Strong recommendation. Deviation requires documented justification. |
| **MAY** | Optional. Permitted but not required. |
| **REQUIRED** | Equivalent to MUST. |
| **CANONICAL** | This document defines the authoritative version; all code MUST match. |

---

<a name="3"></a>
## 3. Product Philosophy

These five principles are **non-negotiable design invariants**. Any feature, change, or optimization that violates them MUST be rejected or elevated to an ADR that explicitly supersedes the principle.

| # | Principle | Operative Meaning |
|---|-----------|-------------------|
| P-1 | **Mirror, Don't Muzzle** | EgoShield annotates and explains. It MUST NOT block, suppress, or alter content on the page. |
| P-2 | **Local-First, Always** | No user content, analysis results, page text, or communication content MUST EVER leave the user's machine. Zero telemetry. Zero cloud inference. |
| P-3 | **Graceful Degradation** | Every subsystem MUST have a defined fallback. The absence of Ollama, a timed-out detector, or a crashed daemon MUST result in degraded-but-functional behavior, never a hard failure. |
| P-4 | **Transparent by Default** | Every annotation MUST cite the specific tactic detected and the evidence phrase that triggered it. No black-box scores. |
| P-5 | **Minimal Footprint** | EgoShield MUST NOT request browser permissions beyond what is strictly necessary. It MUST store only what is needed, with defined retention limits. |

---

<a name="4"></a>
## 4. Goals, Non-Goals & Constraints

### 4.1 Goals

- **G-1:** Detect manipulative communication patterns in real time from web page and email content with P95 latency ≤ 200ms (excluding LLM arbiter path).
- **G-2:** Provide clear, evidence-anchored natural language explanations for each detected tactic.
- **G-3:** Operate entirely on-device with no network egress of user data.
- **G-4:** Support user-defined trust rules (trusted domains, suppressed tactic classes).
- **G-5:** Persist analysis history locally with configurable retention.
- **G-6:** Be installable and fully functional without account creation, registration, or cloud setup.

### 4.2 Non-Goals

- **NG-1:** EgoShield is NOT a content blocker or parental control system.
- **NG-2:** EgoShield does NOT perform sentiment analysis as a primary feature.
- **NG-3:** EgoShield does NOT sync, back up, or share analysis data across devices.
- **NG-4:** EgoShield does NOT operate as a cloud SaaS or require any user account.
- **NG-5:** EgoShield does NOT provide legal, psychological, or medical advice.
- **NG-6:** EgoShield does NOT modify, intercept, or proxy network traffic.

### 4.3 Hard Constraints

| ID | Constraint | Source |
|----|-----------|--------|
| C-1 | Extension MUST use Manifest V3 APIs only | Browser vendor enforcement |
| C-2 | Content scripts MUST NOT exfiltrate raw page content off-device | P-2 |
| C-3 | Local daemon MUST bind to `127.0.0.1` only | Security (Section 10) |
| C-4 | SQLite DB file MUST be stored in user's OS application data directory, not a browser-accessible path | Security (Section 9.4) |
| C-5 | IMAP credentials MUST NEVER be stored in plaintext | Security (Section 9.4) |
| C-6 | Ollama MUST be treated as optional at all times; daemon MUST start and function without it | P-3 |
| C-7 | All detector results MUST include the evidence phrase(s) that triggered the detection | P-4 |
| C-8 | Extension permissions MUST be documented and justified in ADR-008 | P-5 |

---

<a name="5"></a>
## 5. System Architecture

### 5.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S MACHINE                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  BROWSER (MV3 Extension)                  │  │
│  │                                                          │  │
│  │  ┌──────────────┐    ┌──────────────┐  ┌─────────────┐  │  │
│  │  │Content Script│    │ Background   │  │  Popup UI   │  │  │
│  │  │(DOM capture) │───▶│Service Worker│  │(quick view) │  │  │
│  │  │              │    │(API bridge)  │  └─────────────┘  │  │
│  │  └──────────────┘    └──────┬───────┘                   │  │
│  └─────────────────────────────┼────────────────────────────┘  │
│                                │ HTTP (127.0.0.1:PORT)          │
│                                ▼                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LOCAL FASTAPI DAEMON                         │  │
│  │                                                          │  │
│  │  ┌────────────┐  ┌──────────────────────────────────┐   │  │
│  │  │  /health   │  │        Detection Pipeline         │   │  │
│  │  │  /ready    │  │                                   │   │  │
│  │  └────────────┘  │  ┌──────────┐  ┌──────────────┐  │   │  │
│  │                  │  │Normalizer│─▶│ DetectionPool │  │   │  │
│  │  ┌────────────┐  │  └──────────┘  │(ThreadPool)  │  │   │  │
│  │  │  Rules API │  │               └──────┬───────┘  │   │  │
│  │  │ Settings   │  │                      ▼          │   │  │
│  │  │  History   │  │  ┌───────────────────────────┐  │   │  │
│  │  └────────────┘  │  │      Scoring Engine       │  │   │  │
│  │                  │  └──────────────┬────────────┘  │   │  │
│  │                  │                 ▼               │   │  │
│  │                  │  ┌───────────────────────────┐  │   │  │
│  │                  │  │   LLM Arbiter (optional)  │  │   │  │
│  │                  │  │   [Ollama health-checked] │  │   │  │
│  │                  │  └──────────────┬────────────┘  │   │  │
│  │                  └─────────────────┼───────────────┘   │  │
│  │                                    ▼                    │  │
│  │  ┌──────────────────────────────────────────────────┐  │  │
│  │  │              SQLite (local DB)                   │  │  │
│  │  └──────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     Optional: Desktop Dashboard (local web UI)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │     Optional: Ollama (local LLM runtime)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

        NO DATA LEAVES THIS BOX. EVER.
```

### 5.2 Architectural Layers

| Layer | Component | Responsibility | Failure Mode |
|-------|-----------|----------------|--------------|
| Capture | Content Script | DOM/email extraction, serialization | Returns empty payload → daemon no-ops |
| Transport | Service Worker | HTTP bridge, timeout enforcement, retry | Falls back to cached last-known daemon health |
| Analysis | Detection Pipeline | Normalization, parallel detection, scoring | Individual detector timeout → score without it |
| Explanation | LLM Arbiter | Natural language tactic explanation | Falls back to template explanations |
| Persistence | SQLite | Local history, rules, settings, metrics | Write failure → log + skip persist, analysis still returned |
| Presentation | Overlay / Dashboard | Annotation rendering, history, rules UI | Overlay render failure must not affect host page JS |

### 5.3 Data Flow — Page Analysis

```
Content Script
    │
    │ 1. Capture visible text + DOM signals
    │    [MUST NOT capture passwords, payment fields, or hidden inputs]
    ▼
Service Worker
    │
    │ 2. POST /api/v2/analyze
    │    [MUST timeout at 5000ms total]
    ▼
FastAPI Daemon
    │
    │ 3. Normalize (clean, tokenize, chunk)
    ├──▶ 4a. Spawn detector pool (parallel)
    │         ├─ DarkPatternDetector
    │         ├─ EmotionalManipulationDetector
    │         ├─ UrgencyInflationDetector
    │         ├─ GaslightingDetector
    │         ├─ SocialEngineeringDetector
    │         └─ [user-defined plugin detectors]
    │
    │ 5. Aggregate results → Scoring Engine
    │         [severity weights × compounding factor → composite score]
    │
    ├──▶ 6. LLM Arbiter (if Ollama healthy AND score > threshold)
    │         [MUST timeout at 8000ms → fallback to template]
    │
    │ 7. Persist to SQLite (async, non-blocking to response)
    │
    └──▶ 8. Return AnalysisResponse to Service Worker
              │
              ▼
         Content Script renders overlay annotations
```

### 5.4 Data Flow — Email Analysis

```
Content Script (Gmail/Outlook web)
    │
    │ 1. Capture email body via DOM (MUST NOT capture headers with PII
    │    beyond sender domain for domain_stats tracking)
    ▼
[identical to page analysis flow from step 2]
```

---

<a name="6"></a>
## 6. Component Specifications

### 6.1 Browser Extension (MV3)

#### 6.1.1 Content Script

- **MUST** run in an isolated world (MV3 default) — MUST NOT share JS heap with host page.
- **MUST NOT** capture form field values, password fields, payment card fields, or any field with `type="password"` or `autocomplete` values indicating credentials.
- **MUST** extract only visible, user-readable text and structural DOM signals (element types, link densities).
- **MUST** serialize to a `CapturePayload` struct before sending to the Service Worker.
- **MUST** apply a content length cap: payloads exceeding `MAX_CONTENT_BYTES` (default: `50_000`) MUST be chunked or truncated with a `truncated: true` flag in the payload.
- **MUST NOT** inject inline scripts into the host page.
- **MUST** render overlay annotations without modifying the host page's own DOM event handlers.

#### 6.1.2 Service Worker (Background)

- **MUST** manage daemon health state and cache the last known health status.
- **MUST** enforce a `5000ms` total timeout on all calls to the daemon.
- **MUST NOT** retry more than `2` times on a single user-triggered analysis.
- **MUST** surface a "daemon unavailable" state to the popup UI and overlay without crashing.
- **MUST** use `chrome.storage.local` (or equivalent) for persisting user-facing state (enabled/disabled per domain, trusted domains). **MUST NOT** use `chrome.storage.sync` as it would sync data cross-device in violation of P-2.

#### 6.1.3 Popup UI

- **MUST** display current domain trust status.
- **MUST** allow toggling EgoShield on/off for the current domain.
- **MUST** display daemon health status (healthy / degraded / unavailable).
- **MUST** link to the dashboard for full history.

#### 6.1.4 Overlay

- **MUST** annotate evidence phrases inline using non-destructive DOM insertion (`::after` pseudo or injected `<span>` with a scoped class prefix `ego-`).
- **MUST NOT** alter layout flow in a way that causes page reflow on first paint.
- **MUST** render a severity-coded indicator (color + icon) per tactic.
- **MUST** show tactic name + evidence phrase on hover/focus (accessible).
- **MUST** be dismissible by the user without refreshing the page.

### 6.2 Local FastAPI Daemon

#### 6.2.1 Startup & Binding

- **MUST** bind exclusively to `127.0.0.1`. Binding to `0.0.0.0` is a critical defect.
- **MUST** use a configurable port (default: `8765`) with an OS-level port conflict check on startup.
- **MUST** emit a structured JSON log line on startup: `{"event": "daemon_start", "version": "...", "port": ..., "ollama_status": "..."}`.
- **MUST** expose `/health` and `/ready` endpoints (spec in Section 8.3).

#### 6.2.2 Detection Pipeline

```python
# CANONICAL pipeline interface — all implementations MUST conform

class DetectorBase(ABC):
    name: str                    # MUST be a stable, unique slug
    version: str                 # MUST be semver
    severity_weight: float       # MUST be in range [0.0, 1.0]
    timeout_ms: int              # MUST default to 2000

    @abstractmethod
    def detect(self, normalized: NormalizedContent) -> list[TacticResult]:
        """
        MUST return within timeout_ms.
        MUST NOT raise exceptions — catch internally and return [].
        MUST include evidence_phrases in every TacticResult.
        """
```

- The `DetectionPool` MUST use a `ThreadPoolExecutor` with a configurable worker count (default: `4`).
- Each detector MUST be individually time-boxed. A single slow detector MUST NOT block the pipeline.
- Results from timed-out detectors MUST be logged as `{"event": "detector_timeout", "detector": "...", "timeout_ms": ...}` and excluded from scoring with a `partial_result: true` flag in the response.

#### 6.2.3 Scoring Engine

**Canonical scoring formula:**

```
composite_score = Σ (tactic.severity × detector.severity_weight) × compounding_factor(n_tactics)
```

Where:
- `compounding_factor(n) = 1.0 + (0.1 × max(0, n - 1))` — each additional tactic adds 10% compounding, capped at `[OWNER TO CONFIRM]`.
- `composite_score` MUST be normalized to `[0.0, 1.0]`.
- Score thresholds for severity bands MUST be defined as named constants (not magic numbers):

```python
SEVERITY_THRESHOLDS = {
    "LOW":      (0.0,  0.30),
    "MEDIUM":   (0.30, 0.60),
    "HIGH":     (0.60, 0.85),
    "CRITICAL": (0.85, 1.0),
}
```

#### 6.2.4 LLM Arbiter (Ollama)

**Health check:**
- MUST poll `GET http://localhost:11434/api/tags` on daemon startup and cache result.
- MUST re-poll health every `60s` in the background.
- MUST NOT invoke Ollama if last health check failed.

**Invocation rules:**
- MUST only invoke arbiter if `composite_score >= LLM_THRESHOLD` (default: `0.30`; configurable).
- MUST enforce an `8000ms` timeout on Ollama requests.
- MUST implement a three-tier fallback:

```
Tier 1: Full arbiter — validate detections + generate explanation          [Ollama healthy]
Tier 2: Explanation-only — accept scores, generate explanation only        [Ollama slow/partial]
Tier 3: Template explanation — fill tactic name + evidence into template   [Ollama unavailable]
```

- Tier 3 template MUST produce a useful, non-empty explanation:
  ```
  "Detected [{tactic_name}] pattern. Key signal: '{evidence_phrase}'. 
  Severity: {severity_band}. Enable local LLM for detailed analysis."
  ```

- **MUST NOT** send any user content to any remote endpoint. The arbiter is local-only.
- If Ollama JSON response is malformed or fails schema validation, MUST fall to next tier.

### 6.3 Email Reader Module

- **MUST** use `imaplib` (Python stdlib) exclusively. No third-party IMAP libraries without an ADR.
- IMAP credentials **MUST** be retrieved from OS keychain at runtime (see Section 9.4).
- **MUST NOT** cache or store raw IMAP credentials in memory beyond the connection context.
- **MUST** fetch only the message body text. MUST NOT persist attachment content.
- **MUST** surface IMAP connection failures as structured log events, not unhandled exceptions.

### 6.4 Optional Desktop Dashboard

- **MUST** be served by the local daemon on a separate port (default: `8766`; configurable). **MUST** bind to `127.0.0.1` only.
- **MUST** provide: analysis history, tactic distribution charts, user rules editor, settings, diagnostics export.
- **MUST** support pagination for history (no unbounded queries).
- **SHOULD** be buildable as an Electron or Tauri wrapper for native app delivery (tracked as future ADR).

---

<a name="7"></a>
## 7. Data Architecture

### 7.1 CANONICAL SQLite Schema (v2)

This is the authoritative schema. All migrations MUST produce this end state. The schema version is tracked in the `schema_meta` table.

```sql
-- ============================================================
-- META
-- ============================================================
CREATE TABLE schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT INTO schema_meta (key, value) VALUES ('schema_version', '2');
INSERT INTO schema_meta (key, value) VALUES ('created_at', datetime('now'));

-- ============================================================
-- ANALYSES
-- ============================================================
CREATE TABLE analyses (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    url_hash        TEXT NOT NULL,          -- SHA-256 of full URL; raw URL MUST NOT be stored
    domain          TEXT NOT NULL,          -- eTLD+1 only (e.g., example.com)
    content_type    TEXT NOT NULL,          -- 'page' | 'email' | 'other'
    composite_score REAL NOT NULL CHECK (composite_score BETWEEN 0.0 AND 1.0),
    severity_band   TEXT NOT NULL CHECK (severity_band IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    tactic_count    INTEGER NOT NULL DEFAULT 0,
    partial_result  INTEGER NOT NULL DEFAULT 0, -- 1 if any detector timed out
    arbiter_tier    INTEGER CHECK (arbiter_tier IN (1, 2, 3, NULL)),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at      TEXT NOT NULL           -- MUST be set to created_at + retention_days
);

CREATE INDEX idx_analyses_domain      ON analyses(domain);
CREATE INDEX idx_analyses_created_at  ON analyses(created_at);
CREATE INDEX idx_analyses_expires_at  ON analyses(expires_at);

-- ============================================================
-- TACTICS (child of analyses)
-- ============================================================
CREATE TABLE tactics (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    analysis_id     TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    detector_name   TEXT NOT NULL,
    tactic_name     TEXT NOT NULL,
    severity        REAL NOT NULL CHECK (severity BETWEEN 0.0 AND 1.0),
    evidence_phrases TEXT NOT NULL,         -- JSON array of strings; MUST NOT be empty
    explanation     TEXT,                   -- Arbiter output or template string
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_tactics_analysis_id  ON tactics(analysis_id);
CREATE INDEX idx_tactics_tactic_name  ON tactics(tactic_name);

-- ============================================================
-- USER RULES
-- ============================================================
CREATE TABLE user_rules (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    rule_type       TEXT NOT NULL CHECK (rule_type IN ('trusted_domain','suppress_tactic','custom_pattern')),
    value           TEXT NOT NULL,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX idx_user_rules_type_value ON user_rules(rule_type, value);

-- ============================================================
-- DOMAIN STATS (aggregate; no raw URLs stored)
-- ============================================================
CREATE TABLE domain_stats (
    domain              TEXT PRIMARY KEY,
    total_analyses      INTEGER NOT NULL DEFAULT 0,
    avg_composite_score REAL NOT NULL DEFAULT 0.0,
    last_seen_at        TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================
-- SETTINGS
-- ============================================================
CREATE TABLE settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- CANONICAL default settings (MUST be inserted on first run):
INSERT OR IGNORE INTO settings (key, value) VALUES
    ('retention_days',         '90'),
    ('llm_threshold',          '0.30'),
    ('llm_timeout_ms',         '8000'),
    ('detector_timeout_ms',    '2000'),
    ('max_content_bytes',      '50000'),
    ('dashboard_port',         '8766'),
    ('daemon_port',            '8765'),
    ('overlay_enabled',        'true'),
    ('email_analysis_enabled', 'false');

-- ============================================================
-- METRICS (internal operability — see Section 11)
-- ============================================================
CREATE TABLE metrics (
    id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    event_type      TEXT NOT NULL,
    value_ms        REAL,
    value_int       INTEGER,
    metadata        TEXT,                   -- JSON; MUST NOT contain user content
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_metrics_event_type  ON metrics(event_type);
CREATE INDEX idx_metrics_created_at  ON metrics(created_at);
```

### 7.2 Data Retention

| Table | Retention Policy | Enforcement |
|-------|-----------------|-------------|
| `analyses` | `retention_days` setting (default: 90 days) | Purge cron (Section 7.3) |
| `tactics` | Cascades from `analyses` (ON DELETE CASCADE) | Automatic |
| `domain_stats` | Never auto-purged (aggregate only, no raw content) | Manual reset via UI |
| `metrics` | 30 days | Purge cron (Section 7.3) |
| `user_rules` | Never auto-purged | User-controlled |
| `settings` | Never purged | — |

### 7.3 Retention Purge (CANONICAL)

A background task MUST run on daemon startup and every `24h` thereafter:

```sql
-- MUST be executed as a single transaction
BEGIN;

DELETE FROM analyses
WHERE expires_at < datetime('now');

DELETE FROM metrics
WHERE created_at < datetime('now', '-30 days');

COMMIT;
```

The purge MUST be logged: `{"event": "retention_purge", "analyses_deleted": N, "metrics_deleted": M}`.

### 7.4 Forbidden Data

The following data **MUST NEVER** be stored in SQLite or logged:

| Forbidden | Reason |
|-----------|--------|
| Raw page URLs | Privacy — URL may contain PII, session tokens, or sensitive query params |
| Raw page content / email body | Privacy — P-2 |
| IMAP passwords or tokens | Security — credential exposure risk |
| Form field values | Security — may contain passwords, payment data |
| User's real name or email address | Privacy — unnecessary PII collection |

---

<a name="8"></a>
## 8. API Contract — Extension ↔ Daemon

**This is a versioned contract.** Breaking changes MUST increment the API version and produce an ADR. The extension MUST validate the daemon version on first connection and surface a "version mismatch" warning if the major version differs.

**Base URL:** `http://127.0.0.1:{daemon_port}/api/v2`

**All requests MUST include header:** `X-EgoShield-Client: extension/{extension_version}`

**All responses MUST include header:** `X-EgoShield-Daemon: {daemon_version}`

### 8.1 `POST /api/v2/analyze`

#### Request

```json
{
  "url_hash": "string (SHA-256 of current URL)",
  "domain": "string (eTLD+1)",
  "content_type": "page | email",
  "content": "string (visible text, max MAX_CONTENT_BYTES)",
  "truncated": "boolean",
  "client_timestamp": "ISO-8601"
}
```

**Constraints:**
- `content` MUST be pre-sanitized by the content script (strip HTML, trim whitespace).
- `content` MUST NOT exceed `MAX_CONTENT_BYTES`. If it does, the daemon MUST return `413`.
- The daemon MUST respond within `4500ms` (leaving buffer before the extension's `5000ms` timeout).

#### Response (200 OK)

```json
{
  "analysis_id": "string (UUID)",
  "composite_score": "float [0.0-1.0]",
  "severity_band": "LOW | MEDIUM | HIGH | CRITICAL",
  "partial_result": "boolean",
  "arbiter_tier": "1 | 2 | 3 | null",
  "tactics": [
    {
      "detector_name": "string",
      "tactic_name": "string",
      "severity": "float [0.0-1.0]",
      "evidence_phrases": ["string"],
      "explanation": "string (MUST be non-empty)"
    }
  ],
  "meta": {
    "daemon_version": "string",
    "analysis_duration_ms": "integer",
    "detectors_run": "integer",
    "detectors_timed_out": "integer"
  }
}
```

#### Error Responses

| Status | Code | Meaning |
|--------|------|---------|
| 400 | `INVALID_PAYLOAD` | Missing required fields or malformed JSON |
| 413 | `CONTENT_TOO_LARGE` | Content exceeds MAX_CONTENT_BYTES |
| 422 | `VALIDATION_ERROR` | Schema validation failure |
| 429 | `RATE_LIMITED` | >10 requests/min from extension (anti-runaway) |
| 503 | `PIPELINE_UNAVAILABLE` | All detectors timed out; no partial result possible |

### 8.2 `GET /api/v2/rules`

Returns active user rules. Used by content script to determine trusted domains before sending analysis requests.

#### Response (200 OK)

```json
{
  "trusted_domains": ["string"],
  "suppressed_tactics": ["string"],
  "custom_patterns": ["string"]
}
```

### 8.3 Health & Readiness Endpoints

#### `GET /health` — Is the daemon process alive?

```json
{
  "status": "healthy | degraded",
  "daemon_version": "string",
  "uptime_seconds": "integer"
}
```

- Returns `200` if process is running, even if subsystems are degraded.
- Returns `degraded` if: Ollama is unavailable, SQLite write test fails, or any detector has errored > 3 times in last 60s.

#### `GET /ready` — Is the daemon ready to serve analysis requests?

```json
{
  "ready": "boolean",
  "checks": {
    "sqlite": "ok | error",
    "detectors": "ok | partial | error",
    "ollama": "ok | unavailable | error"
  }
}
```

- Returns `200` with `ready: true` only if SQLite and at least one detector are functional.
- Returns `200` with `ready: false` (not `503`) so the extension can display "degraded" vs "unavailable" states.
- Ollama `unavailable` is NOT a readiness failure — it is a graceful degradation state.

---

<a name="9"></a>
## 9. Security & Privacy Specification

### 9.1 Principles (Operative)

These are not aspirations; they are enforceable requirements:

- **S-1:** All user content and analysis results MUST remain on the user's machine at all times.
- **S-2:** The daemon MUST bind to `127.0.0.1` only. MUST NOT listen on any external interface.
- **S-3:** All credential storage MUST use OS-native keychain services.
- **S-4:** The extension MUST request the minimum set of browser permissions required for functionality. Any permission not directly tied to a documented feature MUST be removed.
- **S-5:** EgoShield MUST NOT execute remote code. Plugin detectors MUST be local, signed, and loaded from the application directory only.

### 9.2 Extension Permissions Manifest

The following permissions are authorized. Any additional permission MUST be justified in ADR-008 and reviewed by the owner before submission to extension stores.

| Permission | Justification |
|-----------|---------------|
| `activeTab` | Access current tab content for analysis |
| `storage` | Persist domain trust rules locally |
| `scripting` | Inject content script and overlay |
| `alarms` | Schedule periodic daemon health checks |
| `host_permissions: 127.0.0.1:*` | Communicate with local daemon only |

**MUST NOT** request: `tabs` (broad), `history`, `bookmarks`, `cookies`, `webRequest`, `identity`, or any broad host permission (`<all_urls>` unless technically unavoidable with ADR justification).

### 9.3 Cross-Origin Request Protection

The daemon MUST validate the `Origin` header on all API requests:

```python
ALLOWED_ORIGINS = [
    f"chrome-extension://{EXTENSION_ID}",
    f"moz-extension://{EXTENSION_ID}",
    "http://127.0.0.1:8766",  # dashboard
]

# Any request with Origin not in ALLOWED_ORIGINS MUST return 403
```

The `EXTENSION_ID` MUST be configurable and MUST NOT be hardcoded in a way that allows an attacker to spoof it via a crafted web page.

### 9.4 Credential & Secrets Management

| Secret | Storage Mechanism | MUST NOT |
|--------|------------------|----------|
| IMAP password | OS keychain (`keyring` library) | Stored in SQLite, config file, or env var |
| Daemon port config | Local config file (non-sensitive) | — |
| Extension ID | Extension manifest (read-only) | — |

**OS Keychain Integration (CANONICAL):**

```python
import keyring

SERVICE_NAME = "EgoShield"

def store_imap_credential(account_id: str, password: str) -> None:
    keyring.set_password(SERVICE_NAME, account_id, password)

def get_imap_credential(account_id: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, account_id)

def delete_imap_credential(account_id: str) -> None:
    keyring.delete_password(SERVICE_NAME, account_id)
```

**On-disk SQLite encryption:** The SQLite file MUST be stored with OS-level file permissions restricting read access to the current user only (`chmod 600` equivalent). Full-disk encryption (SQLCipher or equivalent) is a PHASE 2 goal tracked in ADR-009.

### 9.5 Data Classification

| Data Class | Examples | Storage Allowed | Logging Allowed |
|-----------|----------|----------------|-----------------|
| User content | Page text, email body | NEVER | NEVER |
| Derived signals | Tactic names, evidence phrases | SQLite only | NEVER in full; MAY log phrase length |
| Aggregate stats | Domain avg score, tactic counts | SQLite | YES (no raw content) |
| Credentials | IMAP password | OS keychain only | NEVER |
| Config | Port, thresholds, retention days | Config file | YES |
| Metrics | Latency, error counts | SQLite metrics table | YES (no user content) |

### 9.6 Privacy Compliance

`[OWNER TO CONFIRM]` — The applicable privacy regulations depend on the jurisdiction declared in the document header. At minimum, the following obligations apply regardless of jurisdiction:

- EgoShield collects no data that leaves the device, which means traditional data processor/controller obligations are limited to on-device storage.
- A **Privacy Policy** MUST be published before any public release describing: what is stored, how long, how to delete it, and that no data is transmitted off-device.
- The installation/onboarding flow MUST include a one-time disclosure of on-device data storage practices before first analysis.

---

<a name="10"></a>
## 10. Threat Model

### 10.1 Assets to Protect

| Asset | Classification | Impact if Compromised |
|-------|---------------|----------------------|
| User browsing content (page text) | Critical | Privacy violation, potential reidentification |
| IMAP credentials | Critical | Full email account takeover |
| Analysis history (SQLite) | High | User behavior profiling, re-identification |
| EgoShield configuration | Medium | Disable or manipulate detection |
| Daemon API | Medium | Fraudulent analysis requests, resource exhaustion |

### 10.2 Threat Actors & Attack Surfaces

| Threat ID | Actor | Surface | Attack Vector | Likelihood | Impact | Mitigation |
|-----------|-------|---------|---------------|-----------|--------|-----------|
| T-1 | Malicious web page | Content Script | Script injection via DOM — attempt to manipulate EgoShield's content script | Medium | High | Isolated world execution (MV3); content script MUST NOT eval() or use innerHTML with page-supplied data |
| T-2 | Malicious web page | Daemon API | CSRF — craft a page that calls `127.0.0.1:8765/api/v2/analyze` with a forged origin | High | Medium | Origin header validation (Section 9.3); CORS policy MUST allow only extension origins |
| T-3 | Local attacker | SQLite file | Read analysis history file from disk | Medium | High | File permissions (Section 9.4); Phase 2: SQLCipher (ADR-009) |
| T-4 | Malicious page | Arbiter (Prompt injection) | Craft page content to manipulate LLM explanation output to mislead user | Medium | Medium | Arbiter prompt MUST clearly separate system instructions from user content; detections are rule-based (not LLM-driven); explanation is advisory only |
| T-5 | Supply chain | Extension update | Malicious extension update pushed via store | Low | Critical | Code signing; reproducible builds; extension store review; MUST document signing keys (ADR-010) |
| T-6 | Local attacker | Daemon process | Kill or manipulate daemon process | Medium | Low | Graceful degradation (P-3); extension detects unavailable state and notifies user |
| T-7 | Local malware | IMAP credentials | Read credentials from memory or keychain | Low | Critical | OS keychain (Section 9.4); credential held in memory only for connection lifetime |
| T-8 | Malicious plugin detector | Daemon plugin loader | Load a malicious custom detector | Low | High | Plugin loading MUST be from application directory only; no remote plugin loading (S-5) |

### 10.3 Mitigations Checklist (Pre-Production Gate)

All of the following MUST be verified before public release:

- [ ] Content script runs in isolated world (T-1)
- [ ] Daemon validates `Origin` header and rejects unknown origins (T-2)
- [ ] SQLite file has `chmod 600` equivalent permissions on all platforms (T-3)
- [ ] LLM arbiter prompt uses strict role separation (T-4)
- [ ] Extension package is code-signed (T-5)
- [ ] IMAP credentials are stored exclusively in OS keychain (T-7)
- [ ] Plugin detector loading validates source directory (T-8)

---

<a name="11"></a>
## 11. Observability & Operability

### 11.1 Structured Logging Specification

All log output from the daemon MUST be structured JSON, one object per line (NDJSON format), written to a rotating log file.

**Log file location:** `{user_data_dir}/egoshield/logs/daemon.log`  
**Rotation policy:** 5MB per file, max 5 files (25MB total), then rotate.

**CANONICAL log schema:**

```json
{
  "ts":           "ISO-8601 timestamp",
  "level":        "DEBUG | INFO | WARN | ERROR | CRITICAL",
  "event":        "snake_case_event_name",
  "version":      "daemon semver",
  "data":         {}
}
```

**MUST NOT** include in any log record:
- Page content or email body (any length)
- Evidence phrase full text (MAY log `evidence_phrase_length_chars`)
- IMAP credentials
- Raw URLs (MAY log `url_hash`)
- Any field from the SQLite `Forbidden Data` list (Section 7.4)

#### 11.2 CANONICAL Log Events

| Event | Level | Required Fields | Notes |
|-------|-------|-----------------|-------|
| `daemon_start` | INFO | `version`, `port`, `ollama_status` | — |
| `daemon_stop` | INFO | `version`, `uptime_seconds` | — |
| `analysis_complete` | INFO | `analysis_id`, `domain`, `composite_score`, `severity_band`, `duration_ms`, `detectors_run`, `detectors_timed_out`, `arbiter_tier` | MUST NOT include content |
| `detector_timeout` | WARN | `detector_name`, `timeout_ms` | — |
| `detector_error` | ERROR | `detector_name`, `error_type`, `error_message` | No stack trace in prod log; stack to DEBUG |
| `arbiter_fallback` | WARN | `from_tier`, `to_tier`, `reason` | — |
| `ollama_health_check` | DEBUG | `status`, `latency_ms` | — |
| `sqlite_write_error` | ERROR | `table`, `error_type` | — |
| `retention_purge` | INFO | `analyses_deleted`, `metrics_deleted` | — |
| `imap_connection_error` | ERROR | `account_id_hash`, `error_type` | MUST NOT log credentials |
| `rate_limit_triggered` | WARN | `client_header`, `requests_per_min` | — |
| `origin_rejected` | WARN | `origin`, `endpoint` | — |

### 11.3 Metrics (Internal — SQLite `metrics` table)

| Metric | Event Type | Value Field | Collected |
|--------|-----------|-------------|-----------|
| Analysis end-to-end latency | `analysis_latency` | `value_ms` | Every analysis |
| Detector latency per detector | `detector_latency` | `value_ms` | Per detector per analysis |
| LLM arbiter latency | `arbiter_latency` | `value_ms` | When arbiter invoked |
| LLM fallback count | `arbiter_fallback` | `value_int` (tier) | On fallback |
| Detector timeout count | `detector_timeout` | `value_int` (1) | On timeout |
| SQLite write latency | `sqlite_write_latency` | `value_ms` | Sampled 1-in-10 |

#### CANONICAL SLO Queries

```sql
-- P95 analysis latency (last 24h)
SELECT
    ROUND(value_ms, 0) as p95_ms
FROM (
    SELECT value_ms,
           ROW_NUMBER() OVER (ORDER BY value_ms) as rn,
           COUNT(*) OVER () as cnt
    FROM metrics
    WHERE event_type = 'analysis_latency'
      AND created_at > datetime('now', '-24 hours')
) WHERE rn = CAST(ROUND(0.95 * cnt) AS INT);

-- Arbiter fallback rate (last 24h)
SELECT
    ROUND(100.0 * COUNT(CASE WHEN value_int >= 2 THEN 1 END) / COUNT(*), 1) as fallback_rate_pct
FROM metrics
WHERE event_type IN ('analysis_latency', 'arbiter_fallback')
  AND created_at > datetime('now', '-24 hours');

-- Detector timeout rate by detector
SELECT
    json_extract(metadata, '$.detector_name') as detector_name,
    COUNT(*) as timeout_count
FROM metrics
WHERE event_type = 'detector_timeout'
  AND created_at > datetime('now', '-24 hours')
GROUP BY detector_name
ORDER BY timeout_count DESC;
```

### 11.4 Dashboard Diagnostics Export

The dashboard MUST provide a "Export Diagnostics Bundle" feature that produces a `.zip` containing:

```
diagnostics/
├── daemon.log                   # last 500 lines only
├── metrics_summary.json         # aggregated metrics (no user content)
├── settings.json                # current settings
├── detector_versions.json       # name, version, timeout_ms per detector
├── ollama_status.json           # last health check result
└── schema_meta.json             # schema version info
```

This bundle MUST NOT contain any of the Forbidden Data from Section 7.4.

---

<a name="12"></a>
## 12. Testing Specification

### 12.1 Test Pyramid

```
                    ╔═══════════════╗
                    ║   E2E Tests   ║   ~20 tests
                    ║  (Playwright) ║
                  ╔══════════════════════╗
                  ║  Integration Tests   ║   ~80 tests
                  ║  (pytest + fixtures) ║
                ╔══════════════════════════════╗
                ║         Unit Tests           ║   ~300+ tests
                ║    (pytest + hypothesis)     ║
                ╚══════════════════════════════╝
```

### 12.2 Unit Tests

**Target:** ≥ 90% line coverage on `detectors/`, `scoring/`, `arbiter/`, `db/`

| Suite | Tools | Key Cases |
|-------|-------|-----------|
| Detector suite | `pytest`, `hypothesis` | Each detector: true positive, true negative, edge cases (empty string, unicode, max length), timeout simulation |
| Scoring engine | `pytest` | Formula correctness, boundary values, compounding factor, threshold bands |
| LLM arbiter | `pytest` + mocked Ollama | Tier 1→2→3 fallback chain, JSON parse failure, timeout, healthy path |
| SQLite layer | `pytest` + in-memory SQLite | Write, read, cascade delete, retention purge, schema migration |
| Credential manager | `pytest` + mocked keyring | Store, retrieve, delete, missing credential handling |
| API validation | `pytest` + `httpx` | Request schema validation, oversized payload (413), rate limit (429) |

### 12.3 Integration Tests

**All integration tests MUST run against a real SQLite instance (in-memory or temp file) and a real FastAPI app, with Ollama mocked.**

| Suite | Key Flows |
|-------|-----------|
| Pipeline integration | Full `analyze` request → detectors → scoring → persist → response; partial result when detector times out |
| Extension ↔ Daemon API | Contract conformance for all v2 endpoints; version mismatch detection |
| Retention purge | Insert data with past `expires_at` → run purge → verify deletion |
| Rules + suppression | Insert suppressed tactic rule → run analysis → verify tactic absent from response |
| IMAP reader | Mock IMAP server → connect → fetch → assert no credential in log output |

### 12.4 E2E Tests (Playwright)

**Requires:** real browser with extension loaded, daemon running, Ollama mocked via proxy

| Test ID | Scenario | Pass Criteria |
|---------|----------|---------------|
| E2E-001 | Load a page with injected manipulation patterns | Overlay renders with correct tactic annotations and evidence phrases |
| E2E-002 | Load a page with no manipulation patterns | No overlay rendered; score = 0 |
| E2E-003 | Mark domain as trusted | Analysis skipped for that domain; overlay does not render |
| E2E-004 | Daemon unavailable | Extension popup shows "EgoShield unavailable"; page loads normally |
| E2E-005 | Ollama unavailable | Analysis completes with Tier 3 explanation; `arbiter_tier: 3` in response |
| E2E-006 | Content exceeds MAX_CONTENT_BYTES | Daemon returns 413; extension shows "content too large" notice |
| E2E-007 | Suppress a tactic | Suppressed tactic absent from overlay on a page that would trigger it |
| E2E-008 | Dashboard history | After 3 analyses, dashboard shows 3 entries with correct scores |
| E2E-009 | Diagnostics export | Export produces valid ZIP with no forbidden data in any contained file |
| E2E-010 | Extension version mismatch | Extension shows "daemon version mismatch" warning |

### 12.5 Performance Tests

**Must be run on a baseline machine spec: `[OWNER TO CONFIRM — e.g., 4-core, 8GB RAM, no GPU]`**

| Test | Method | Pass Criteria |
|------|--------|---------------|
| P95 analysis latency (no LLM) | `locust` or `pytest-benchmark`, 100 sequential requests | ≤ 200ms |
| P95 analysis latency (with Tier 3 fallback) | 100 sequential requests, Ollama mocked as unavailable | ≤ 250ms |
| Concurrent analysis requests | 10 concurrent requests | No deadlock; all return within 5000ms |
| SQLite write throughput | 1000 analysis inserts | No write errors; avg write < 5ms |
| Retention purge with 10k records | Single purge call | Completes < 2s |

### 12.6 Security Tests (Pre-Production Gate)

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Origin spoofing | Send request with `Origin: https://evil.com` | 403 returned |
| Oversized payload | Send content > MAX_CONTENT_BYTES | 413 returned; no crash |
| SQL injection via API | Inject SQL in `domain` field | Sanitized; no DB error |
| Log scrubbing | Run analysis with known content; inspect logs | No content appears in any log file |
| IMAP credential exposure | Run IMAP fetch; inspect logs + SQLite | No credential in either |
| Permission audit | Load extension in browser; inspect granted permissions | Matches manifest exactly |

### 12.7 CI Gates

All of the following MUST pass before any merge to `main`:

```
✅ Unit tests (pytest) — 100% pass, ≥90% coverage on core modules
✅ Integration tests — 100% pass
✅ Type checking (mypy --strict on daemon)
✅ Linting (ruff)
✅ Security scan (bandit)
✅ Dependency audit (pip-audit / safety)
✅ Extension manifest lint (web-ext lint)
✅ Schema migration test (apply all migrations to fresh DB)
```

E2E and performance tests MUST run on every release candidate branch.

---

<a name="13"></a>
## 13. Release, Packaging & Upgrade

### 13.1 Component Versioning

EgoShield uses **semantic versioning (semver)** for all components. Versions MUST be kept in sync across components at each release.

```
Extension:   major.minor.patch   (e.g., 2.1.0)
Daemon:      major.minor.patch   (e.g., 2.1.0)
DB Schema:   integer             (e.g., 2)
API Version: integer             (e.g., 2)  — in URL path
```

**Compatibility rules:**
- Extension `major` MUST match Daemon `major`. Mismatch MUST trigger a warning to the user.
- Daemon `minor` changes MAY introduce new optional API fields. Extension MUST ignore unknown fields.
- DB schema changes MUST be handled by a migration (Section 13.3). Downgrade is NOT guaranteed.

### 13.2 Packaging Targets

| Platform | Daemon Packaging | Extension Packaging |
|----------|-----------------|---------------------|
| macOS | `.pkg` installer or `brew` cask | `.crx` / `.xpi` |
| Windows | `.msi` or NSIS installer | `.crx` |
| Linux | `.deb`, `.rpm`, or AppImage | `.xpi` / `.crx` |

**MUST include in every installer:**
- Daemon binary (or Python package + venv)
- Default config file
- DB schema migration scripts
- Uninstaller that removes: daemon process, config files, and optionally SQLite DB (with user confirmation)

### 13.3 Database Migrations

- Migrations MUST be sequential numbered SQL files: `migrations/001_init.sql`, `002_add_metrics.sql`, etc.
- The daemon MUST run pending migrations on startup before serving any requests.
- Migration MUST be wrapped in a transaction. If a migration fails, the daemon MUST refuse to start and log a `CRITICAL` event.
- **MUST NOT** use destructive migrations (DROP COLUMN, DROP TABLE) without a `[REQUIRES ADR]` gate.

```python
# CANONICAL migration runner (pseudocode)
def run_migrations(db_path: str) -> None:
    current_version = get_schema_version()
    pending = get_pending_migrations(current_version)
    for migration in pending:
        with db.transaction():
            db.execute(migration.sql)
            db.execute("UPDATE schema_meta SET value = ? WHERE key = 'schema_version'",
                       [migration.version])
        log_event("migration_applied", {"version": migration.version})
```

### 13.4 Code Signing

- The daemon binary and installer MUST be code-signed before distribution.
- The browser extension MUST be signed by the respective extension store (Chrome Web Store, Firefox AMO).
- A self-signed option MAY be provided for developer/power-user installs, clearly labeled as such.
- Signing keys and processes MUST be documented in ADR-010 before first public release.

### 13.5 Auto-Update Policy

- The daemon MUST check for updates via a local manifest endpoint (not a remote endpoint that sends machine data). `[OWNER TO CONFIRM update mechanism]`
- The extension benefits from browser store auto-update; the daemon update MUST be separate and user-confirmed (not silent).
- Update MUST: stop daemon → apply migration → restart daemon. If migration fails, rollback to previous binary.

### 13.6 Phased Rollout

| Phase | Description | Gate |
|-------|-------------|------|
| Alpha | Internal only; all CI gates + manual threat model verification | Owner sign-off |
| Beta | Limited public release; diagnostics export enabled; telemetry opt-out confirmed | Security test pass + privacy policy published |
| GA | Full public release | All pre-production human actions complete; E2E + perf tests green |

---

<a name="14"></a>
## 14. Non-Functional Requirements (Acceptance Criteria)

These are **binary pass/fail gates** for production release. They MUST be verified by automated tests wherever possible, and by documented manual test otherwise.

| ID | Category | Requirement | Measurement | Target | Must-Have for GA |
|----|----------|-------------|-------------|--------|-----------------|
| NFR-01 | Performance | Analysis P95 latency (no LLM) | Performance test suite | ≤ 200ms | YES |
| NFR-02 | Performance | Analysis P95 latency (LLM Tier 1) | Performance test suite | ≤ 3000ms | NO (informational) |
| NFR-03 | Performance | Daemon startup time | Timed startup test | ≤ 3s on baseline hardware | YES |
| NFR-04 | Reliability | Analysis success rate under concurrent load (10 req) | Load test | ≥ 99% | YES |
| NFR-05 | Reliability | Graceful degradation when Ollama unavailable | E2E-005 | Tier 3 response returned | YES |
| NFR-06 | Reliability | Graceful degradation when daemon unavailable | E2E-004 | Extension does not crash; user notified | YES |
| NFR-07 | Security | Daemon refuses cross-origin requests | Security test | 100% rejection rate | YES |
| NFR-08 | Security | No user content appears in log files | Security test | Zero occurrences | YES |
| NFR-09 | Security | IMAP credentials never stored outside keychain | Security test | Zero occurrences in DB/logs | YES |
| NFR-10 | Privacy | No network egress during analysis | Network capture test | Zero external connections | YES |
| NFR-11 | Operability | Diagnostics bundle contains no forbidden data | E2E-009 | Zero occurrences | YES |
| NFR-12 | Storage | SQLite DB growth per 1000 analyses | Storage test | ≤ 50MB | YES |
| NFR-13 | Compatibility | Extension works on Chrome ≥ 120, Firefox ≥ 120 | E2E suite on both | All E2E pass | YES |
| NFR-14 | Installability | Fresh install to first analysis in < 5 min | Manual timed test | ≤ 5 minutes | YES |

---

<a name="15"></a>
## 15. Architecture Decision Records (ADRs)

Each ADR MUST be in state: `PROPOSED → ACCEPTED → SUPERSEDED`.  
Any `[OWNER TO CONFIRM]` item MUST be resolved before the ADR moves to `ACCEPTED`.

---

### ADR-001: FastAPI as Daemon Framework

**Status:** ACCEPTED  
**Context:** The daemon requires a lightweight HTTP server with async support, strong typing, automatic OpenAPI schema generation, and fast startup. Python is preferred to keep the codebase unified with detector logic.  
**Decision:** Use FastAPI with Uvicorn as the ASGI server.  
**Alternatives Rejected:**
- Flask: Lacks native async and type-based request validation.
- Django: Too heavy for a local daemon; startup overhead unacceptable for NFR-03.
- aiohttp: More boilerplate; no automatic schema generation.
**Consequences:**
- (+) Automatic request/response validation; OpenAPI spec auto-generated.
- (+) Async support for concurrent detector pool without blocking.
- (-) Uvicorn adds a dependency; MUST be bundled or verified in all installers.

---

### ADR-002: SQLite as Local Persistence

**Status:** ACCEPTED  
**Context:** All data MUST remain local. Need a relational store for analyses, tactics, rules, and metrics with ACID guarantees.  
**Decision:** Use SQLite with WAL mode enabled.  
**Alternatives Rejected:**
- Postgres (local): Too heavy; requires a running server process; unacceptable for P-5.
- LiteFS: Distributed SQLite — unnecessary for single-user local app.
- Flat JSON files: No relational integrity; no efficient querying for dashboard.
- DuckDB: Excellent for analytics; less suited for OLTP-style writes per analysis.
**Consequences:**
- (+) Zero-config; single file; trivially portable.
- (+) WAL mode enables concurrent reads during writes.
- (-) Full-text search across `tactics` requires FTS5 extension (Phase 2 feature, tracked in ADR-009).
- **Action:** Enable WAL mode on every new DB: `PRAGMA journal_mode=WAL;`

---

### ADR-003: Manifest V3 for Browser Extension

**Status:** ACCEPTED  
**Context:** Chrome and Firefox are both enforcing MV3. MV2 is deprecated.  
**Decision:** Use MV3 exclusively.  
**Alternatives Rejected:**
- MV2 + compatibility shim: MV2 is sunset in Chrome; unacceptable long-term dependency.
**Consequences:**
- (+) Future-proof; store compliant.
- (-) Service Worker lifecycle constraints require daemon health state to be cached defensively.
- (-) `chrome.webRequest` blocking not available; but EgoShield does NOT block (P-1) so this is not a constraint.
- **Key implication:** Service Worker can be terminated at any time. All state MUST be persisted to `chrome.storage.local` and re-hydrated on activation.

---

### ADR-004: Ollama as Local LLM Runtime

**Status:** ACCEPTED  
**Context:** EgoShield needs natural language explanation of detected tactics. P-2 forbids any cloud inference. Local LLMs are the only compliant path.  
**Decision:** Use Ollama as the local LLM runtime, treated as an optional external dependency.  
**Alternatives Rejected:**
- llama.cpp direct: No clean HTTP API; more complex integration.
- LM Studio: GUI-focused; less programmable.
- Hugging Face Transformers (bundled): Large bundle size; GPU/CPU requirements hard to standardize.
**Consequences:**
- (+) Simple HTTP API; broad model support; active project.
- (-) Requires user to install Ollama separately; increases onboarding friction.
- (-) Minimum hardware requirements are model-dependent — MUST be documented per supported model.
- **`[OWNER TO CONFIRM]`:** Specify supported models and minimum hardware (e.g., `llama3.2:3b` requires ~4GB RAM, no GPU needed).
- **Fallback:** Three-tier arbiter fallback (Section 6.2.4) ensures EgoShield functions fully without Ollama.

---

### ADR-005: Parallel Detector Pool Architecture

**Status:** ACCEPTED  
**Context:** Multiple detectors must run per analysis. Sequential execution would fail NFR-01 (≤200ms P95).  
**Decision:** Use `ThreadPoolExecutor` with per-detector timeouts. Each detector runs independently and results are aggregated.  
**Alternatives Rejected:**
- `asyncio.gather`: Works well for I/O-bound tasks; detectors are CPU-bound (regex, NLP). Thread pool is more appropriate.
- Sequential execution: Unacceptable latency with 5+ detectors.
- Subprocess-per-detector: Too much overhead; complex IPC.
**Consequences:**
- (+) Detector isolation: one slow/crashing detector doesn't block others.
- (+) Easy to add new detectors without touching pipeline logic.
- (-) Thread overhead for very fast detectors; acceptable given target latency.
- (-) GIL limits true CPU parallelism for Python-heavy detectors; acceptable for current complexity; revisit if detector complexity grows (ADR-011 candidate).

---

### ADR-006: Detector Plugin Architecture

**Status:** ACCEPTED  
**Context:** Power users and researchers should be able to add custom detectors without modifying core code.  
**Decision:** Detectors are Python classes that subclass `DetectorBase`. Custom detectors are loaded from a `plugins/` directory within the application data directory.  
**Alternatives Rejected:**
- Entry-points (pip-installed plugins): Too complex for end users; requires reinstall to add detector.
- Remote plugins: Categorically rejected — violates S-5.
**Consequences:**
- (+) Extensible without core changes.
- (-) **Security risk:** loading arbitrary Python from disk. Mitigated by: directory restriction (application data dir only, not user-writable in multi-user installs), documentation of risk, future: plugin signing (ADR-012 candidate).
- **`[OWNER TO CONFIRM]`:** Plugin directory path and permissions model per platform.

---

### ADR-007: SHA-256 URL Hashing (No Raw URL Storage)

**Status:** ACCEPTED  
**Context:** URLs can contain PII (session tokens, user IDs, email addresses in query params). Storing raw URLs violates privacy intent and P-2 in spirit.  
**Decision:** Store only `SHA-256(full_url)` in `analyses.url_hash`. Store only `eTLD+1` in `analyses.domain`.  
**Alternatives Rejected:**
- Store full URL: PII risk unacceptable.
- Store URL path only: Still risks PII in path segments.
- Store nothing: Prevents deduplication and domain-level stats.
**Consequences:**
- (+) No URL-based re-identification possible from DB.
- (-) Cannot reconstruct which specific URL was analyzed (by design).
- (-) Dashboard cannot show "you visited X" — only "you analyzed a page on example.com."

---

### ADR-008: Extension Permission Justification

**Status:** ACCEPTED  
**Context:** Principle P-5 requires minimum permissions. Each permission must be justified.  
**Decision:** See Section 9.2 for the authorized permission set.  
**`[OWNER TO CONFIRM]`:** If host permission `<all_urls>` is technically required by the content script injection model, this ADR must document that justification explicitly.  
**Consequences:**
- Any PR that adds an extension permission MUST update this ADR or be rejected.

---

### ADR-009: SQLite Encryption (Phase 2)

**Status:** PROPOSED — Do not implement until this ADR moves to ACCEPTED  
**Context:** SQLite file at rest contains sensitive analysis history. File-level OS permissions (Section 9.4) provide basic protection; SQLCipher would provide encryption-at-rest.  
**Decision (proposed):** Adopt SQLCipher in Phase 2 post-GA.  
**Blockers before ACCEPTED:**
- Key derivation mechanism (PBKDF2 from user passphrase vs. OS keychain-stored key)
- Migration path from unencrypted existing DBs
- Bundle size / dependency impact per platform
- `[OWNER TO CONFIRM]`

---

### ADR-010: Code Signing & Distribution

**Status:** PROPOSED — MUST be ACCEPTED before GA release  
**Context:** Unsigned binaries expose users to supply chain attacks (T-5).  
**Decision (proposed):** Sign all release artifacts.  
**`[OWNER TO CONFIRM]`:**
- macOS: Apple Developer ID (requires paid Developer account)
- Windows: EV Code Signing certificate (requires legal entity verification)
- Linux: GPG-signed packages + checksums
- Extension: Chrome Web Store + Firefox AMO signing (automatic on submission)
- Key management: Where are signing keys stored? Who has access?

---

<a name="16"></a>
## 16. Glossary

| Term | Definition |
|------|-----------|
| **Arbiter** | The optional local LLM component (via Ollama) that generates natural-language explanations for detected tactics. |
| **Compounding Factor** | A multiplier applied by the Scoring Engine when multiple tactics are detected simultaneously, reflecting that co-occurrence of tactics increases overall manipulation signal. |
| **Content Script** | The MV3 extension component injected into web pages to capture content and render overlay annotations. |
| **Daemon** | The local FastAPI HTTP server process that hosts all detection, scoring, persistence, and arbiter logic. |
| **Detector** | A discrete analysis module that inspects normalized content for a specific class of manipulation tactic and returns `TacticResult` objects with evidence. |
| **Evidence Phrase** | A specific substring from the analyzed content that directly triggered a tactic detection. MUST be included in every `TacticResult`. |
| **Graceful Degradation** | The system property where failure of any optional subsystem (Ollama, a single detector, dashboard) results in reduced but functional operation rather than complete failure. |
| **Local-First** | Architecture principle: all user data, analysis, and inference happens on the user's device. No user data ever leaves the machine. |
| **NFR** | Non-Functional Requirement — requirements about *how* the system behaves (performance, security, reliability) rather than *what* it does. |
| **Overlay** | DOM-injected annotations rendered by the content script to highlight and explain detected manipulation patterns on a web page. |
| **Partial Result** | An analysis response where one or more detectors timed out; flagged as `partial_result: true` in the response and DB. |
| **PRR** | Production Readiness Review — the process of verifying a system is operationally ready for production (reliable, observable, secure, owned). |
| **SSOT** | Single Source of Truth — this document is the authoritative reference for EgoShield's architecture and operational requirements. |
| **Tactic** | A specific manipulative communication pattern (e.g., urgency inflation, gaslighting, dark pattern). |
| **Tier (Arbiter)** | The fallback tier of the LLM arbiter: Tier 1 = full validation + explanation; Tier 2 = explanation only; Tier 3 = template explanation. |
| **WAL** | Write-Ahead Logging — SQLite journal mode that enables concurrent reads during writes. MUST be enabled on all EgoShield SQLite instances. |

---

*End of EgoShield Production Engineering Specification v2.0.0*

---

> **How to transition from v1.0.0 to this document:**
> 1. Resolve all `[OWNER TO CONFIRM]` items and fill in the document header.
> 2. Walk each ADR and mark it `ACCEPTED` or open a new one for any deviations.
> 3. Reconcile the canonical SQLite schema (Section 7.1) with your current schema and write migration `002_v2_schema.sql`.
> 4. Reconcile the API contract (Section 8) with your current routes and type-annotate accordingly.
> 5. Run the CI gate checklist (Section 12.7) — use gaps as your implementation backlog.
> 6. When all pre-production human actions (page 1 table) are complete and CI is green, change `status: DRAFT` → `status: APPROVED`.
