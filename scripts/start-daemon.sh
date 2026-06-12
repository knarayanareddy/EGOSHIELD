#!/bin/bash
# EgoShield Daemon Start Script

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Activate virtual environment if it exists
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Change to project directory
cd "$PROJECT_DIR"

# Set Python path
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Start the daemon
echo "Starting EgoShield Daemon..."
python3 -m daemon.main --port 8765