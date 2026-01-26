#!/bin/bash
# OAuth Setup Launcher for Linux

cd "$(dirname "$0")"

# Create virtual environment if it doesn't exist
if [ ! -d "venv_oauth" ]; then
    echo "Creating virtual environment (first time only)..."
    python3 -m venv venv_oauth
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        echo "Please make sure Python 3 is installed."
        exit 1
    fi
fi

# Activate virtual environment
source venv_oauth/bin/activate

# Check if Flask is installed, if not, install it
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing required packages (Flask, etc.)..."
    echo "This may take a minute the first time..."
    pip install --quiet flask google-auth google-auth-oauthlib python-dotenv requests
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install required packages."
        exit 1
    fi
    echo "Packages installed successfully!"
fi

# Open the HTML page first (it will check if server is running)
xdg-open oauth_setup.html 2>/dev/null || sensible-browser oauth_setup.html 2>/dev/null || firefox oauth_setup.html 2>/dev/null

# Wait a moment for browser to open
sleep 1

# Start the server
echo "Starting OAuth setup server..."
echo "Server will be available at: http://localhost:8080"
python oauth_setup_web.py

