# EgoShield Architecture Document

**Version:** 3.0.0  
**Last Updated:** 2026-06-12

---

## Overview

EgoShield is a local-first, privacy-preserving cognitive shield that protects users from manipulation tactics in web content and emails. The system consists of a browser extension and a local daemon that work together to analyze and annotate potentially manipulative content.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              User's Browser                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EgoShield Extension                           │   │
│  │  ┌─────────────┐  ┌──────────────────────┐  ┌───────────────┐   │   │
│  │  │  Popup UI   │  │    Content Script    │  │  Background   │   │   │
│  │  │             │  │                      │  │    Service    │   │   │
│  │  │ - Stats     │  │ - DOM observation    │  │               │   │   │
│  │  │ - Settings  │  │ - Inline highlights  │  │ - Message hub │   │   │
│  │  │ - History   │  │ - Tooltip injection  │  │ - API calls   │   │   │
│  │  └─────────────┘  └──────────────────────┘  └───────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │ HTTP/JSON (localhost:8765)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EgoShield Daemon                                 │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        Analysis Pipeline                          │   │
│  │                                                                   │   │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │   │
│  │   │  Content    │───▶│  Detection  │───▶│      Scoring        │  │   │
│  │   │ Normalizer  │    │    Pool     │    │      Engine         │  │   │
│  │   └─────────────┘    └──────┬──────┘    └──────────┬──────────┘  │   │
│  │                             │                       │             │   │
│  │                   ┌─────────┴─────────┐             │             │   │
│  │                   ▼                   ▼             │             │   │
│  │              ┌────────┐         ┌────────┐          │             │   │
│  │              │ Built- │         │Plugins │          │             │   │
│  │              │  in    │         │(ADR-006)          │             │   │
│  │              │Detectors         │                    │             │   │
│  │              └────────┘         └────────┘          │             │   │
│  │                                                        │             │   │
│  │        ┌──────────────────────────────────────────────┘             │   │
│  │        │                                                        │   │
│  │        ▼                                                        ▼   │
│  │  ┌─────────────┐                                        ┌─────────┐ │
│  │  │   Scoring   │                                        │   LLM   │ │
│  │  │   Engine    │                                        │ Arbiter │ │
│  │  └──────┬──────┘                                        └────┬────┘ │
│  │         │                                                   │      │
│  └─────────┼───────────────────────────────────────────────────┼──────┘
│            │                                                   │
│            ▼                                                   ▼
│  ┌───────────────────────────────────────────────────────────────┐
│  │                        SQLite Database                        │
│  │  ┌──────────┐  ┌────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │  │analyses  │  │ tactics │  │ user_rules │  │    settings    │  │
│  │  └──────────┘  └────────┘  └──────────┘  └─────────────────┘  │
│  │  ┌──────────┐  ┌────────┐  ┌─────────────────────────────────┐│
│  │  │metrics   │  │domain  │  │         schema_meta             ││
│  │  │          │  │_stats  │  │                                 ││
│  │  └──────────┘  └────────┘  └─────────────────────────────────┘│
│  └───────────────────────────────────────────────────────────────┘
└───────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Browser Extension

#### Content Script (`content.js`)
- Observes DOM mutations using MutationObserver
- Normalizes visible text content
- Injects `<span class="ego-annotation">` elements around detected manipulation phrases
- Appends tooltips to annotation spans

#### Background Service (`background.js`)
- Single message listener for all API communication
- Handles `analyzeContent`, `getOverlayState`, `getHistory`, `updateSettings`
- Caches recent analysis results

#### Popup UI (`popup.html`, `popup.js`)
- Displays current page analysis summary
- Shows severity band and tactic count
- Provides access to settings and history

### 2. Analysis Pipeline

#### Content Normalizer (`utils/content.py`)
```python
class ContentNormalizer:
    def normalize(self, text: str) -> NormalizedContent:
        # 1. Strip HTML tags
        # 2. Tokenize into words
        # 3. Split into sentences
        # 4. Identify paragraphs
        # 5. Calculate statistics
```

#### Detection Pool (`detectors/base.py`)
```python
class DetectionPool:
    def run_all(
        self,
        normalized: NormalizedContent,
        timeout_ms: int = 2000
    ) -> tuple[List[TacticResult], List[str]]:
        # Uses ThreadPoolExecutor with built-in timeout handling
        # Returns (results, timed_out_detector_names)
```

#### Built-in Detectors

| Detector | Tactics Detected | Severity Weight |
|----------|-----------------|-----------------|
| DarkPatternDetector | Fake urgency, hidden costs, confirm shaming | 0.75 |
| EmotionalManipulationDetector | Fear appeals, guilt induction, love bombing | 0.80 |
| GaslightingDetector | Reality denial, self-doubt, isolation | 0.90 |
| UrgencyInflationDetector | Countdown pressure, artificial deadlines | 0.70 |
| SocialEngineeringDetector | Authority impersonation, fake scarcity | 0.85 |

### 3. Scoring Engine (`scoring/engine.py`)

```python
def compute_composite_score(
    tactics: List[TacticResult],
    partial_result: bool
) -> tuple[float, str, int]:
    """
    Computes composite score from all detected tactics.
    
    Formula: 1 - Π(1 - severity_i * weight_i)
    
    Returns: (composite_score, severity_band, tactic_count)
    """
```

### 4. LLM Arbiter (`arbiter/ollama.py`)

The arbiter provides deeper analysis for high-severity content:

- **Tier 1**: Score < threshold (no LLM call)
- **Tier 2**: Score >= threshold (template explanation)
- **Tier 3**: High confidence (Ollama generated explanation)

### 5. Database Layer (`db/`)

#### Schema Version 2

```sql
-- Analyses (main records)
CREATE TABLE analyses (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    url_hash TEXT NOT NULL,           -- SHA-256, NOT raw URL
    domain TEXT NOT NULL,             -- eTLD+1 only
    composite_score REAL NOT NULL,
    severity_band TEXT NOT NULL,
    tactic_count INTEGER NOT NULL,
    partial_result INTEGER NOT NULL,  -- Detector timeout flag
    arbiter_tier INTEGER,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL          -- created_at + retention_days
);

-- Tactics (per-analysis findings)
CREATE TABLE tactics (
    id TEXT PRIMARY KEY,
    analysis_id TEXT REFERENCES analyses(id),
    detector_name TEXT NOT NULL,
    tactic_name TEXT NOT NULL,
    severity REAL NOT NULL,
    evidence_phrases TEXT NOT NULL,   -- JSON array
    explanation TEXT
);
```

---

## Data Flow

### Content Analysis Flow

```
1. User visits webpage
       │
       ▼
2. Content script extracts visible text
       │
       ▼
3. Background sends to daemon API
       │
       ▼
4. Analysis Service:
   a. Normalize content
   b. Run detection pool (parallel)
   c. Calculate composite score
   d. (Optional) Invoke LLM arbiter
   e. Persist to database
       │
       ▼
5. Return analysis response
       │
       ▼
6. Content script:
   a. Inject inline highlights
   b. Show toast notification
   c. Update popup stats
```

---

## Security Model

### Network Security

- **Localhost-only binding**: Daemon binds to `127.0.0.1:8765`
- **Origin validation**: CORS middleware validates extension origins
- **No remote access**: Designed for local-only operation

### Data Privacy

| Data Type | Stored? | Rationale |
|-----------|---------|-----------|
| Raw URL | ❌ No | Only SHA-256 hash stored |
| Page content | ❌ No | Evidence phrases only |
| Email body | ❌ No | Tactics extracted, not content |
| Credentials | ❌ No | Never processed |
| User rules | ✅ Yes | User-controlled preferences |

### Logging Security

Structured logging automatically redacts:
- `content`, `body`, `text`
- `password`, `credential`, `token`
- `url`, `raw_url`

---

## Performance Considerations

### Timeout Handling

- **Detector timeout**: 2000ms per detector
- **LLM timeout**: 8000ms default
- **Thread pool**: Uses `future.result(timeout)` for proper Unix signal handling

### Database Optimization

- **WAL mode**: Enables concurrent reads during writes
- **Indexes**: On `domain`, `created_at`, `expires_at`
- **Retention purge**: Automatic deletion of expired records

### Memory Management

- Content limited to 50KB by default
- Evidence phrases limited to 10 per tactic
- Recent analyses limited to 50 by default query

---

## Extension Points

### ADR-006: Dynamic Plugin Loading

Custom detectors can be loaded from a `plugins/` directory:

```python
class PluginManager:
    def load_plugins(self) -> List[Type[DetectorBase]]:
        # Scans plugins/ for detector_*.py files
        # Validates class inheritance
        # Returns loaded detector classes
```

### Custom Scoring Weights

Settings can override detector severity weights:

```python
# In settings service
VALID_SETTINGS = {
    'detector_weights': 'json',  # Override severity weights
}
```

---

## Deployment Architecture

### Development

```
egoshield/
├── daemon/          # Source code
├── extension/       # Browser extension
└── tests/           # Test suite
```

### Production

```
~/.local/share/EgoShield/
├── logs/            # Rotating log files (25MB max)
├── egoshield.db     # SQLite database
└── plugins/         # Custom plugins (optional)
```

---

## Version History

| Version | Key Changes |
|---------|-------------|
| 1.0.0 | Initial release |
| 2.0.0 | Fixed 10 critical bugs, added tests |
| 3.0.0 | Robust path resolution, ADR-006 plugin system |