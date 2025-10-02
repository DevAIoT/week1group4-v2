#!/bin/bash

# IoT Curtain Control - Quick Start Script

echo "=================================="
echo "IoT Curtain Control System"
echo "=================================="
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed!"
    echo "Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if dependencies are installed
if [ ! -d ".venv" ]; then
    echo "📦 Installing dependencies..."
    uv sync
fi

echo "🚀 Starting server..."
echo ""
echo "Open your browser to: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

# Run the server
uv run python server/main.py 