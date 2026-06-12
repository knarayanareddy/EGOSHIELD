# EgoShield Developer Guide

**Version:** 3.0.0

---

## Prerequisites

- Python 3.10 or higher
- Git
- Chrome/Firefox/Safari browser (for extension development)

### Recommended Tools

- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [Ruff](https://github.com/astral-sh/ruff) - Fast linter and formatter
- [mypy](https://mypy-lang.org/) - Static type checker
- [Playwright](https://playwright.dev/) - E2E testing

---

## Setup Development Environment

### 1. Clone the Repository

```bash
git clone https://github.com/knarayanareddy/egoshield.git
cd egoshield
```

### 2. Create Virtual Environment

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate

# Or using standard venv
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or with uv
uv pip install -e ".[dev]"
```

### 4. Verify Installation

```bash
# Check that the package is installed
python -c "from egoshield.daemon import __version__; print(__version__)"

# Run tests
python -m pytest tests/ -v
```

---

## Project Structure

```
egoshield/
├── daemon/                    # Main Python package
│   ├── __init__.py           # Package exports
│   ├── main.py               # CLI entry point
│   ├── api/                  # FastAPI routes
│   │   ├── __init__.py
│   │   ├── routes.py         # Main API routes
│   │   └── schemas.py        # Pydantic models
│   ├── arbiter/              # LLM integration
│   │   └── ollama.py
│   ├── db/                   # Database layer
│   │   ├── connection.py     # Database manager
│   │   ├── models.py         # Repository classes
│   │   └── schema.sql        # Schema definition
│   ├── detectors/            # Manipulation detectors
│   │   ├── base.py           # Abstract base class
│   │   ├── dark_pattern.py
│   │   ├── emotional_manipulation.py
│   │   ├── gaslighting.py
│   │   ├── social_engineering.py
│   │   ├── urgency_inflation.py
│   │   └── plugin_manager.py # ADR-006
│   ├── scoring/              # Scoring logic
│   │   └── engine.py
│   ├── services/             # Business logic
│   │   ├── analysis.py
│   │   ├── rules.py
│   │   └── settings.py
│   └── utils/                # Utilities
│       ├── content.py
│       ├── logging.py
│       ├── project_paths.py
│       └── security.py
├── extension/                # Browser extension
├── plugins/                  # Custom plugins
├── tests/                    # Test suite
├── docs/                     # Documentation
└── migrations/               # SQL migrations
```

---

## Running the Daemon

### Development Mode

```bash
# Run with debug logging
python -m egoshield.daemon.main --log-level DEBUG

# Run on custom port
python -m egoshield.daemon.main --port 8765 --host 127.0.0.1

# Run with extension ID restriction
python -m egoshield.daemon.main --extension-id abc123xyz
```

### With Ollama Integration

```bash
# Start Ollama in background
ollama serve &

# Pull a model
ollama pull llama3.2

# Run EgoShield (will auto-detect Ollama)
python -m egoshield.daemon.main
```

---

## Running Tests

### All Tests

```bash
python -m pytest tests/ -v
```

### By Type

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# E2E tests
python -m pytest tests/e2e/ -v
```

### With Coverage

```bash
python -m pytest tests/ --cov=egoshield --cov-report=html
```

### Specific Test

```bash
python -m pytest tests/unit/test_plugins.py::TestPluginSystem::test_plugin_discovery -v
```

---

## Code Quality

### Formatting

```bash
# Format code with ruff
ruff format .

# Check formatting
ruff format --check .
```

### Linting

```bash
# Run all linting
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Type Checking

```bash
# Run mypy
mypy daemon/

# With specific config
mypy daemon/ --config-file pyproject.toml
```

### Pre-commit Hooks

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
set -e

echo "Running pre-commit checks..."
ruff format --check .
ruff check .
mypy daemon/
python -m pytest tests/unit/ -q
echo "All checks passed!"
```

---

## Adding a New Detector

### 1. Create the Detector Class

Create `daemon/detectors/custom_detector.py`:

```python
"""
EgoShield Custom Detector
Detects custom manipulation patterns
"""

import re
from typing import List
from .base import DetectorBase, NormalizedContent, TacticResult


class CustomDetector(DetectorBase):
    """
    Detects custom manipulation patterns.
    """
    
    name = "custom"
    version = "1.0.0"
    severity_weight = 0.6  # Adjust based on severity
    timeout_ms = 1500      # Max execution time
    
    PATTERNS = {
        "custom_pattern": {
            "patterns": [
                r"(?i)your\\s+custom\\s+regex\\s+pattern",
            ],
            "severity_base": 0.65,
            "tactic_name": "Custom Manipulation"
        }
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        results: List[TacticResult] = []
        text = normalized.cleaned_text
        
        if not text or len(text) < 10:
            return results
        
        for pattern_type, pattern_data in self.PATTERNS.items():
            all_evidence = []
            
            for pattern in pattern_data["patterns"]:
                try:
                    evidence = self._find_evidence_in_text(text, pattern)
                    if evidence:
                        all_evidence.extend(evidence)
                except re.error:
                    continue
            
            if all_evidence:
                # Deduplicate
                seen = set()
                unique_evidence = []
                for e in all_evidence:
                    if e.lower() not in seen:
                        seen.add(e.lower())
                        unique_evidence.append(e)
                
                severity = self._calculate_severity(
                    pattern_data["severity_base"],
                    len(unique_evidence)
                )
                
                results.append(self._create_result(
                    tactic_name=pattern_data["tactic_name"],
                    severity=severity,
                    evidence_phrases=unique_evidence[:10],
                    matched_patterns=[pattern_type]
                ))
        
        return results
```

### 2. Register in DETECTOR_REGISTRY

Edit `daemon/detectors/__init__.py`:

```python
from .custom_detector import CustomDetector

DETECTOR_REGISTRY = {
    # ... existing detectors ...
    "custom": CustomDetector,
}
```

### 3. Add Tests

Create `tests/unit/test_custom_detector.py`:

```python
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from egoshield.daemon.detectors.custom_detector import CustomDetector
from egoshield.daemon.detectors.base import NormalizedContent


class TestCustomDetector:
    def test_detects_custom_pattern(self):
        detector = CustomDetector()
        
        content = NormalizedContent(
            original_text="Your custom regex pattern detected here",
            cleaned_text="Your custom regex pattern detected here",
            tokens=["your", "custom", "regex", "pattern", "detected", "here"],
            sentences=["Your custom regex pattern detected here"],
            paragraphs=["Your custom regex pattern detected here"],
            word_count=6,
            char_count=40
        )
        
        results = detector.detect(content)
        
        assert len(results) > 0
        assert results[0].tactic_name == "Custom Manipulation"
```

### 4. Test the Detector

```bash
python -m pytest tests/unit/test_custom_detector.py -v
```

---

## Browser Extension Development

### Loading the Extension

1. Open `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select `extension/` directory

### Debugging

- **Content script logs**: Open DevTools on any page, look at console
- **Background logs**: Open `chrome://extensions/`, click "service worker" link
- **Popup logs**: Right-click extension icon, select "Inspect popup"

### Hot Reload

Changes to extension files require manual reload:
1. Make changes to files
2. Go to `chrome://extensions/`
3. Click the refresh button on the EgoShield extension

---

## Debugging Tips

### Daemon Issues

```bash
# Check if daemon is running
curl http://127.0.0.1:8765/health

# View recent logs
tail -f ~/.local/share/EgoShield/logs/daemon.log

# Check database
sqlite3 ~/.local/share/EgoShield/egoshield.db ".schema"
```

### Test Failures

```bash
# Run with full traceback
python -m pytest tests/ -v --tb=long

# Run with pdb
python -m pytest tests/ --pdb
```

### Import Errors

```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify package installation
pip show egoshield
```

---

## Contributing

### Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Format code: `ruff format . && ruff check --fix .`
6. Commit: `git commit -am 'Add my feature'`
7. Push: `git push origin feature/my-feature`
8. Open a Pull Request

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Chrome Extension Development](https://developer.chrome.com/docs/extensions/mv3/)