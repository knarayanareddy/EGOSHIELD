#!/bin/bash
# EgoShield Setup Script
# Installs and configures EgoShield daemon

set -e

echo "=========================================="
echo "  EgoShield Setup Script"
echo "=========================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source ./venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create data directory
DATA_DIR="$HOME/.local/share/EgoShield"
echo ""
echo "Creating data directory at $DATA_DIR..."
mkdir -p "$DATA_DIR"
mkdir -p "$DATA_DIR/logs"
mkdir -p "$DATA_DIR/plugins"

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "To start the daemon:"
echo "  source venv/bin/activate"
echo "  python -m daemon.main"
echo ""
echo "The daemon will listen on http://127.0.0.1:8765"
echo ""
echo "To use with the browser extension:"
echo "  1. Load the extension from extension/ directory"
echo "  2. Ensure the daemon is running"
echo ""
echo "Optional: Install Ollama for LLM explanations:"
echo "  curl -fsSL https://ollama.com/install.sh | sh"
echo "  ollama pull llama3.2:3b"
echo ""