# EgoShield Deployment Guide

**Version:** 3.0.0

---

## Overview

This guide covers deploying EgoShield for:
- **Development**: Local testing and debugging
- **Staging**: Pre-production validation
- **Production**: End-user deployment

---

## System Requirements

### Minimum

- Python 3.10+
- 100MB disk space
- 50MB RAM
- Chrome, Firefox, or Safari browser

### Recommended

- Python 3.12+
- SSD storage for faster SQLite
- 4GB+ RAM for LLM arbiter
- Ollama for enhanced analysis

---

## Development Deployment

### Quick Start

```bash
# Clone repository
git clone https://github.com/knarayanareddy/egoshield.git
cd egoshield

# Install dependencies
pip install -e .

# Start daemon
python -m egoshield.daemon.main

# Load browser extension
# See: docs/extension.md
```

### With LLM Support

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama daemon
ollama serve &

# Pull model
ollama pull llama3.2

# Start EgoShield (auto-detects Ollama)
python -m egoshield.daemon.main
```

### Testing

```bash
# Run all tests
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=egoshield --cov-report=html

# Open coverage report
open htmlcov/index.html
```

---

## Production Deployment

### Package Installation

#### PyPI Installation (Future)

```bash
pip install egoshield

# Run
egoshield-daemon
```

#### Source Installation

```bash
# Clone and install
git clone https://github.com/knarayanareddy/egoshield.git
cd egoshield
pip install -e .

# Create service
sudo cp scripts/egoshield.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable egoshield
sudo systemctl start egoshield
```

### Systemd Service

Create `/etc/systemd/system/egoshield.service`:

```ini
[Unit]
Description=EgoShield Cognitive Shield
After=network.target

[Service]
Type=simple
User=%u
WorkingDirectory=/opt/egoshield
ExecStart=/usr/bin/python -m egoshield.daemon.main
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

# Environment
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

For system-wide installation:

```ini
[Service]
Type=simple
User=root
Group=root
```

### Data Directory

EgoShield stores data in platform-specific locations:

| Platform | Path |
|----------|------|
| Linux | `~/.local/share/EgoShield/` |
| macOS | `~/Library/Application Support/EgoShield/` |
| Windows | `%APPDATA%/EgoShield/` |

**Directory Contents:**
```
EgoShield/
├── logs/
│   ├── daemon.log
│   ├── daemon.log.1
│   └── ...
├── egoshield.db        # SQLite database
├── plugins/            # Custom plugins (optional)
└── settings.json       # Runtime config (if any)
```

### Log Management

#### Log Rotation

Logs rotate automatically:
- Max file size: 5MB
- Max backups: 5
- Total: 25MB

#### Centralized Logging (Optional)

For production observability, redirect logs:

```bash
# Use rsyslog
echo 'if $programname == "egoshield" then /var/log/egoshield.log' | sudo tee /etc/rsyslog.d/egoshield.conf
sudo systemctl restart rsyslog
```

#### Log Analysis

```bash
# View recent logs
tail -f ~/.local/share/EgoShield/logs/daemon.log

# Search for errors
grep '"level":"ERROR"' ~/.local/share/EgoShield/logs/daemon.log

# Parse with jq
cat ~/.local/share/EgoShield/logs/daemon.log | jq '.data'
```

---

## Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . /app
RUN pip install -e .

# Create non-root user
RUN useradd -m -u 1000 egoshield
USER egoshield

EXPOSE 8765

CMD ["python", "-m", "egoshield.daemon.main"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  egoshield:
    build: .
    ports:
      - "127.0.0.1:8765:8765"
    volumes:
      - egoshield-data:/home/egoshield/.local/share/EgoShield
    restart: unless-stopped

volumes:
  egoshield-data:
```

### Run

```bash
docker-compose up -d
docker-compose logs -f
```

---

## Security Configuration

### Production Checklist

- [ ] Daemon binds to localhost only (127.0.0.1)
- [ ] CORS origin validation enabled
- [ ] Rate limiting configured
- [ ] Plugins disabled (unless explicitly needed)
- [ ] Database directory permissions set (0700)
- [ ] Log rotation configured
- [ ] No remote access exposure

### Firewall Configuration

Since the daemon only accepts localhost connections, no firewall rules needed for the API:

```bash
# Verify localhost binding
curl http://127.0.0.1:8765/health

# Verify no external access
curl http://0.0.0.0:8765/health  # Should fail
```

### SSL/TLS (Optional)

For extension-dashboard communication over HTTPS:

```python
# Generate self-signed cert
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Run with SSL
python -m egoshield.daemon.main --ssl-key key.pem --ssl-cert cert.pem
```

---

## Monitoring

### Health Check

```bash
# Simple health
curl http://127.0.0.1:8765/health

# Detailed readiness
curl http://127.0.0.1:8765/ready
```

### Metrics

Access via API:

```bash
# Get diagnostics
curl http://127.0.0.1:8765/api/v2/diagnostics

# View metrics
sqlite3 ~/.local/share/EgoShield/egoshield.db \
  "SELECT * FROM metrics ORDER BY created_at DESC LIMIT 10;"
```

### Alerting

Monitor log for errors:

```bash
# Alert on critical logs
tail -f ~/.local/share/EgoShield/logs/daemon.log | grep '"level":"CRITICAL"'
```

---

## Backup & Restore

### Backup

```bash
# Stop daemon (optional, but safe)
sudo systemctl stop egoshield

# Copy database
cp ~/.local/share/EgoShield/egoshield.db ~/backup/

# Copy logs (optional)
cp -r ~/.local/share/EgoShield/logs ~/backup/logs

# Restart daemon
sudo systemctl start egoshield
```

### Restore

```bash
# Stop daemon
sudo systemctl stop egoshield

# Restore database
cp ~/backup/egoshield.db ~/.local/share/EgoShield/

# Restart daemon
sudo systemctl start egoshield
```

---

## Upgrade

### Minor Version (3.0.x)

```bash
git pull
pip install -e .
sudo systemctl restart egoshield
```

### Major Version (x.0.0)

```bash
# Backup first!
./scripts/backup.sh

# Stop daemon
sudo systemctl stop egoshield

# Update code
git fetch origin
git checkout v3.0.0

# Migrate database (if needed)
python -m egoshield.daemon.main --migrate

# Start daemon
sudo systemctl start egoshield
```

---

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop egoshield
sudo systemctl disable egoshield

# Remove service file
sudo rm /etc/systemd/system/egoshield.service

# Remove application
pip uninstall egoshield

# Remove data (optional)
rm -rf ~/.local/share/EgoShield/

# Remove browser extension
# See browser extension settings
```