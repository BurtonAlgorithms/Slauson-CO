#!/bin/bash

# Start webhook server with virtual environment
# Usage: ./start_server.sh [port]

cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo "Note: no ./venv found; using current Python environment ($(python --version 2>/dev/null || echo 'python not found'))."
fi

# Get port from argument or use default
PORT=${1:-5001}

# Start the webhook server
echo "Starting Slauson Automation Webhook Server..."
echo "=============================================="
echo ""
echo "Server will run on: http://localhost:$PORT"
echo ""
echo "For Zapier testing, start ngrok in another terminal:"
echo "  ngrok http $PORT"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

PORT=$PORT python webhook_listener.py
