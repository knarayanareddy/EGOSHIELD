#!/bin/bash
# Run EgoShield tests

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "=========================================="
echo "  Running EgoShield Tests"
echo "=========================================="

# Run unit tests
echo ""
echo ">>> Unit Tests"
pytest tests/unit/ -v

# Run integration tests
echo ""
echo ">>> Integration Tests"
pytest tests/integration/ -v

# Run E2E tests
echo ""
echo ">>> E2E Tests"
pytest tests/e2e/ -v

echo ""
echo "=========================================="
echo "  Tests Complete"
echo "=========================================="