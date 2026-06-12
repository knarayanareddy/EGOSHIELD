# EgoShield v3.0.0

**Local-first, privacy-preserving cognitive shield**

EgoShield is a browser extension and local daemon that protects users from dark patterns, manipulation tactics, and social engineering in web content and emails.

---

## Features

- **5 Built-in Manipulation Detectors**: Dark patterns, emotional manipulation, gaslighting, urgency inflation, and social engineering
- **Dynamic Plugin System (ADR-006)**: Extend detection with custom plugins
- **Local LLM Arbiter**: Optional Ollama integration for deep analysis
- **Real-time Inline Annotations**: Highlight manipulation tactics in web pages
- **Privacy-First Architecture**: All processing happens locally; no data leaves your machine
- **Comprehensive Observability**: Structured NDJSON logging with rotation

---

## Quick Start

### Prerequisites

- Python 3.10+
- Chrome/Firefox/Safari browser
- (Optional) Ollama for LLM-based analysis

### Installation

```bash
# Clone the repository
git clone https://github.com/knarayanareddy/egoshield.git
cd egoshield

# Install the package
pip install -e .

# Run the daemon
python -m egoshield.daemon.main
```

### Browser Extension

1. Open `chrome://extensions/` (or your browser's equivalent)
2. Enable "Developer mode"
3. Click "Load unpacked" and select `extension/`
4. The EgoShield icon will appear in your toolbar

### Enable LLM Analysis (Optional)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2

# Restart the daemon - LLM arbiter will auto-detect
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Popup UI   │  │ Content Script│  │ Background   │       │
│  │              │  │   (Overlay)   │  │   Service    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          └─────────────────┴─────────────────┘
                            │ HTTP/JSON
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    EgoShield Daemon                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Analysis   │  │   Scoring    │  │   LLM        │       │
│  │   Service    │  │   Engine     │  │   Arbiter    │       │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘       │
│         │                                   │               │
│  ┌──────▼──────────────────────────────────▼───────┐       │
│  │              Detection Pool                     │       │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │       │
│  │  │ Dark   │ │Emotional│ │Gaslight│ │Urgency │   │       │
│  │  │Pattern │ │Manip.  │ │        │ │Inflation│   │       │
│  │  └────────┘ └────────┘ └────────┘ └────────┘   │       │
│  │                   + Plugin Detectors           │       │
│  └─────────────────────────────────────────────────┘       │
│                            │                               │
│  ┌─────────────────────────▼───────────────────────────┐  │
│  │              SQLite Database (WAL Mode)              │  │
│  │  analyses │ tactics │ user_rules │ settings │ metrics │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Settings

Configure via the API or dashboard:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `retention_days` | int | 90 | Days to keep analysis history |
| `llm_threshold` | float | 0.30 | Score threshold for LLM analysis |
| `llm_timeout_ms` | int | 8000 | LLM request timeout |
| `detector_timeout_ms` | int | 2000 | Detector execution timeout |
| `max_content_bytes` | int | 50000 | Max content size to analyze |
| `plugins_enabled` | bool | false | Enable custom plugins |
| `plugins_path` | string | "" | Path to plugins directory |

### API Endpoints

```bash
# Health check
curl http://127.0.0.1:8765/health

# Analyze content
curl -X POST http://127.0.0.1:8765/api/v2/analyze \
  -H "Content-Type: application/json" \
  -d '{"content": "...", "url": "...", "domain": "example.com", "content_type": "page"}'

# Get settings
curl http://127.0.0.1:8765/api/v2/settings

# Update settings
curl -X PUT http://127.0.0.1:8765/api/v2/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "plugins_enabled", "value": "true"}'
```

---

## Custom Plugins (ADR-006)

### Creating a Plugin

1. Create a file in your plugins directory with `detector_` prefix:

```python
# plugins/detector_mytheme.py
import re
from typing import List
from daemon.detectors.base import DetectorBase, NormalizedContent, TacticResult

class MyThemeDetector(DetectorBase):
    name = "mytheme"
    version = "1.0.0"
    severity_weight = 0.5
    timeout_ms = 1000
    
    PATTERNS = {
        "custom_pattern": {
            "patterns": [r"(?i)your\s+custom\s+pattern"],
            "severity_base": 0.6,
            "tactic_name": "Custom Manipulation"
        }
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        # Implementation
        ...
```

2. Enable plugins in settings:

```bash
curl -X PUT http://127.0.0.1:8765/api/v2/settings \
  -d '{"key": "plugins_enabled", "value": "true"}'
```

3. Restart the daemon

### Security Notes

- Plugins are **disabled by default** for security
- Only files matching `detector_*.py` are loaded
- Plugin code executes in a restricted context
- Only load plugins from trusted sources

---

## Development

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v

# E2E tests only
python -m pytest tests/e2e/ -v
```

### Code Quality

```bash
# Format with ruff
ruff format .

# Lint with ruff
ruff check .

# Type checking with mypy
mypy daemon/
```

---

## Project Structure

```
egoshield/
├── daemon/                    # Main Python package
│   ├── main.py               # Entry point
│   ├── api/                  # FastAPI routes
│   ├── arbiter/              # LLM arbiter (Ollama)
│   ├── db/                   # SQLite database layer
│   ├── detectors/            # Manipulation pattern detectors
│   │   ├── base.py           # Base class for detectors
│   │   ├── dark_pattern.py
│   │   ├── emotional_manipulation.py
│   │   ├── gaslighting.py
│   │   ├── social_engineering.py
│   │   ├── urgency_inflation.py
│   │   └── plugin_manager.py # ADR-006 dynamic loading
│   ├── scoring/              # Composite scoring engine
│   ├── services/             # Business logic services
│   └── utils/                # Utilities
│       ├── content.py        # Content normalization
│       ├── logging.py        # Structured logging
│       ├── project_paths.py  # Path resolution
│       └── security.py       # Security utilities
├── extension/                # Browser extension
│   ├── manifest.json
│   ├── js/
│   │   ├── background.js
│   │   ├── content.js
│   │   └── popup.js
│   ├── css/
│   └── popup.html
├── plugins/                  # Custom detector plugins
│   └── detector_example.py
├── migrations/               # Database migrations
├── tests/                    # Test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                     # Documentation
├── dashboard.html           # Dashboard UI
├── setup.py                 # Package setup
├── pyproject.toml           # Project metadata
└── requirements.txt         # Dependencies
```

---

## Severity Bands

| Band | Score Range | Action |
|------|-------------|--------|
| **LOW** | 0.00 - 0.29 | Informational |
| **MEDIUM** | 0.30 - 0.59 | Caution |
| **HIGH** | 0.60 - 0.79 | Warning |
| **CRITICAL** | 0.80 - 1.00 | Immediate attention |

---

## Privacy & Security

### Data Handling

- **No raw URLs stored**: Only SHA-256 hashes
- **No content stored**: Only analysis metadata and tactic names
- **No external transmission**: All processing is local
- **Structured logging**: PII/sensitive data automatically redacted

### Security Features

- Localhost-only binding (127.0.0.1)
- Origin validation for CORS
- Rate limiting (10 req/min default)
- WAL mode for concurrent database access

---

## License

MIT License - See LICENSE file for details.

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Submit a pull request