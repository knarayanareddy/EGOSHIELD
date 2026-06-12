# ADR-006: Dynamic Plugin Loading for Custom Detectors

**Status:** Accepted  
**Date:** 2024-03-15  
**Deciders:** EgoShield Team

---

## Context

Power users may want to add custom manipulation pattern detectors beyond the built-in 5. We needed to decide:
- **Option A**: No customization (locked to built-in detectors)
- **Option B**: Configuration file based patterns (limited flexibility)
- **Option C**: Dynamic Python plugin loading (full flexibility, security concerns)
- **Option D**: Official plugin marketplace (complexity)

---

## Decision

**We chose Option C: Dynamic Python Plugin Loading with Security Controls**

Custom detector plugins can be loaded from a designated `plugins/` directory.

---

## Security Controls

### Disabled by Default

Plugins are disabled until explicitly enabled:

```python
# Default settings
plugins_enabled = 'false'  # Must be explicitly enabled
plugins_path = ''          # Empty until configured
```

### File Naming Convention

Only files matching `detector_*.py` are considered:

```
plugins/
├── detector_custom.py   ✓ Loaded
├── detector_foo.py      ✓ Loaded
├── my_script.py         ✗ Ignored
├── utils.py             ✗ Ignored
```

### Class Inheritance Validation

Loaded classes must inherit from `DetectorBase`:

```python
class MyDetector(DetectorBase):  # ✓ Valid
    pass

class NotADetector:               # ✗ Rejected
    pass
```

### Path Traversal Prevention

Files cannot escape the plugins directory:

```python
def _load_plugin_file(self, file_path: Path) -> Optional[Type[DetectorBase]]:
    resolved = file_path.resolve()
    plugins_dir = self._plugins_path.resolve()
    
    if not str(resolved).startswith(str(plugins_dir)):
        raise PluginLoadingError("Security violation")
```

---

## Plugin Interface

### Required Structure

```python
# plugins/detector_mytheme.py
import re
from typing import List
from daemon.detectors.base import DetectorBase, NormalizedContent, TacticResult

class MyThemeDetector(DetectorBase):
    name = "mytheme"           # Unique identifier
    version = "1.0.0"          # Semver
    severity_weight = 0.5      # Impact on score (0-1)
    timeout_ms = 1000          # Max execution time
    
    PATTERNS = {
        "pattern_id": {        # Internal pattern name
            "patterns": [
                r"(?i)regex\\s+pattern\\s+1",
                r"(?i)regex\\s+pattern\\s+2",
            ],
            "severity_base": 0.6,  # Base severity
            "tactic_name": "Human Readable Name"
        }
    }
    
    def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
        # Implementation here
        ...
```

### Example Implementation

```python
def detect(self, normalized: NormalizedContent) -> List[TacticResult]:
    results = []
    text = normalized.cleaned_text
    
    for pattern_type, pattern_data in self.PATTERNS.items():
        evidence = []
        for pattern in pattern_data["patterns"]:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            evidence.extend([m.group() for m in matches])
        
        if evidence:
            results.append(self._create_result(
                tactic_name=pattern_data["tactic_name"],
                severity=self._calculate_severity(
                    pattern_data["severity_base"],
                    len(evidence)
                ),
                evidence_phrases=list(set(evidence))[:10],
                matched_patterns=[pattern_type]
            ))
    
    return results
```

---

## Configuration

### Enable Plugins

```bash
# Via API
curl -X PUT http://127.0.0.1:8765/api/v2/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "plugins_enabled", "value": "true"}'

# Optional: set custom path
curl -X PUT http://127.0.0.1:8765/api/v2/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "plugins_path", "value": "/home/user/my-plugins"}'
```

### Restart Required

Plugin changes require daemon restart to take effect.

---

## Plugin Manager API

```python
from daemon.detectors.plugin_manager import get_plugin_manager

manager = get_plugin_manager()

# Check status
status = manager.get_status_dict()
# {'enabled': True, 'plugins_path': '/path', 'loaded_count': 2, ...}

# Reload plugins
manager.reload()

# Get loaded classes
classes = manager.load_plugins()
```

---

## Consequences

### Positive

- Full Python flexibility for complex detectors
- Users can create domain-specific patterns
- Extensible without modifying core code
- Community sharing of useful plugins

### Negative

- Security risk if users load untrusted plugins
- Requires Python knowledge to create plugins
- Potential performance impact with many plugins

---

## Recommendations for Users

1. **Only load plugins from trusted sources**
2. **Review plugin code before enabling**
3. **Keep plugins directory separate from system Python**
4. **Disable plugins when not needed**

---

## Future Considerations

- **Plugin signing**: Cryptographic verification of plugin authenticity
- **Sandboxing**: Isolated execution environment for plugins
- **Marketplace**: Curated repository of verified plugins
- **Version pinning**: Ensure compatibility with specific daemon versions

---

## Related Decisions

- [ADR-001: Local-First Architecture](adr-001-local-first-architecture.md)