#!/bin/bash
# OAuth Setup Launcher for Mac

cd "$(dirname "$0")"

PYTHON_BIN=""
if [ -x "$HOME/opt/miniconda3/bin/python3" ]; then
    PYTHON_BIN="$HOME/opt/miniconda3/bin/python3"
elif [ -x "$HOME/miniconda3/bin/python3" ]; then
    PYTHON_BIN="$HOME/miniconda3/bin/python3"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    PYTHON_BIN="/opt/homebrew/bin/python3"
elif [ -x "/usr/local/bin/python3" ]; then
    PYTHON_BIN="/usr/local/bin/python3"
elif [ -x "/usr/bin/python3" ]; then
    PYTHON_BIN="/usr/bin/python3"
else
    PYTHON_BIN="python3"
fi

echo "Using Python: $PYTHON_BIN"

VENV_DIR="$HOME/.slauson_oauth_venv"
PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"
USE_VENV=1

# Create virtual environment if it doesn't exist
if [ ! -x "$PY" ]; then
    echo "Creating virtual environment (first time only)..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to create virtual environment. Falling back to user install."
        USE_VENV=0
    fi
fi

if [ "$USE_VENV" -eq 0 ]; then
    PY="$PYTHON_BIN"
    PIP="$PYTHON_BIN -m pip"
else
    # Ensure pip exists in venv
    "$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1
fi

# Check if Flask is installed, if not, install it
if ! "$PY" -c "import flask" 2>/dev/null; then
    echo "Installing required packages (Flask, etc.)..."
    echo "This may take a minute the first time..."
    if [ "$USE_VENV" -eq 1 ]; then
        "$PIP" install --quiet flask google-auth google-auth-oauthlib python-dotenv requests
    else
        $PIP install --user --quiet flask google-auth google-auth-oauthlib python-dotenv requests \
            || $PIP install --user --quiet --break-system-packages flask google-auth google-auth-oauthlib python-dotenv requests
    fi
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install required packages."
        exit 1
    fi
    echo "Packages installed successfully!"
fi

# Open the HTML page first (it will check if server is running)
if [ -f "OPEN_THIS_FILE.html" ]; then
    open -a "Safari" "OPEN_THIS_FILE.html" >/dev/null 2>&1 || open "OPEN_THIS_FILE.html"
elif [ -f "oauth_setup.html" ]; then
    open -a "Safari" "oauth_setup.html" >/dev/null 2>&1 || open "oauth_setup.html"
fi

# Wait a moment for browser to open
sleep 1

# Start the server
echo "Starting OAuth setup server..."
echo "Server will be available at: http://localhost:8080"

# Ensure a local CA bundle to avoid permission issues with cert files
CERT_BUNDLE="oauth_cacert.pem"
if [ ! -f "$CERT_BUNDLE" ]; then
    curl -fsSL https://curl.se/ca/cacert.pem -o "$CERT_BUNDLE" >/dev/null 2>&1
fi

SSL_CERT_FILE="$CERT_BUNDLE" REQUESTS_CA_BUNDLE="$CERT_BUNDLE" "$PY" oauth_setup_web.py

