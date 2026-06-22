#!/bin/bash
echo "========================================"
echo "  爆款拆解机 - 启动服务器"
echo "========================================"
echo ""

cd "$(dirname "$0")/backend"

# Activate venv
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate

# Install deps
pip install -q -r requirements.txt

echo ""
echo "Starting server at http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python main.py
