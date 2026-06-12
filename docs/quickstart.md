# EgoShield Quick Start Guide

## Installation

### 1. Install Python Dependencies

```bash
cd egoshield
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start the Daemon

```bash
python -m daemon.main
```

The daemon will start on `http://127.0.0.1:8765`

### 3. Install Browser Extension

**Chrome:**
1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `egoshield/extension/` folder

**Firefox:**
1. Open `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `egoshield/extension/manifest.json`

### 4. (Optional) Install Ollama for LLM Explanations

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Or on Windows, download from https://ollama.com/download

# Pull the recommended model
ollama pull llama3.2:3b

# Verify it's running
ollama list
```

## Usage

### Basic Analysis

1. Open any webpage
2. The extension will automatically analyze the content
3. Manipulative patterns will be highlighted with annotations
4. Click the EgoShield icon in the toolbar to:
   - See the current score and detected patterns
   - Toggle analysis on/off for the current domain
   - Mark a domain as trusted

### Dashboard

Open `http://127.0.0.1:8766` in your browser to access the dashboard where you can:
- View analysis history
- See tactic distribution charts
- Manage trusted domains and suppressed tactics
- Export diagnostics

### API Usage

```bash
# Check daemon health
curl http://127.0.0.1:8765/health

# Analyze content
curl -X POST http://127.0.0.1:8765/api/v2/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "url_hash": "abc123...",
    "domain": "example.com",
    "content_type": "page",
    "content": "Your text content here..."
  }'

# Get rules
curl http://127.0.0.1:8765/api/v2/rules

# Get settings
curl http://127.0.0.1:8765/api/v2/settings
```

## Configuration

### Change Port

```bash
python -m daemon.main --port 9000
```

### Change Log Level

```bash
python -m daemon.main --log-level DEBUG
```

### Update Settings via API

```bash
# Increase retention to 180 days
curl -X PUT http://127.0.0.1:8765/api/v2/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "retention_days", "value": "180"}'

# Disable overlay
curl -X PUT http://127.0.0.1:8765/api/v2/settings \
  -H "Content-Type: application/json" \
  -d '{"key": "overlay_enabled", "value": "false"}'
```

## Troubleshooting

### Daemon won't start

Check if port 8765 is already in use:
```bash
lsof -i :8765  # macOS/Linux
netstat -ano | findstr :8765  # Windows
```

### Extension shows "Daemon Unavailable"

1. Make sure the daemon is running
2. Check the daemon logs at `~/.local/share/EgoShield/logs/daemon.log`
3. Try restarting the daemon

### Ollama not working

1. Verify Ollama is running: `curl http://localhost:11434/api/tags`
2. Check the model is installed: `ollama list`
3. Restart Ollama: `ollama serve`

### No annotations appearing

1. Check if the domain is trusted (trusted domains are skipped)
2. Verify overlay is enabled in settings
3. The page might not contain enough text to analyze (minimum 50 characters)

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
# Lint
ruff check daemon/

# Type check
mypy daemon/

# Format
ruff format daemon/
```