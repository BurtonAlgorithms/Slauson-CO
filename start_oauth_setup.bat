@echo off
REM OAuth Setup Launcher for Windows

cd /d "%~dp0"

REM Create virtual environment if it doesn't exist
if not exist "venv_oauth" (
    echo Creating virtual environment (first time only)...
    python -m venv venv_oauth
    if errorlevel 1 (
        echo Error: Failed to create virtual environment.
        echo Please make sure Python is installed.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv_oauth\Scripts\activate.bat

REM Check if Flask is installed, if not, install it
python -c "import flask" 2>nul
if errorlevel 1 (
    echo Installing required packages (Flask, etc.)...
    echo This may take a minute the first time...
    pip install --quiet flask google-auth google-auth-oauthlib python-dotenv requests
    if errorlevel 1 (
        echo Error: Failed to install required packages.
        pause
        exit /b 1
    )
    echo Packages installed successfully!
)

REM Open the HTML page first (it will check if server is running)
start oauth_setup.html

REM Wait a moment for browser to open
timeout /t 1 /nobreak >nul

REM Start the server
echo Starting OAuth setup server...
echo Server will be available at: http://localhost:8080
python oauth_setup_web.py
pause

