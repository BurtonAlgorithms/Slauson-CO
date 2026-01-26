#!/usr/bin/env python3
"""
Web-based OAuth Setup Interface

This creates a simple web interface for OAuth setup.
Users just open http://localhost:8080 in their browser - no terminal needed!

Usage:
    python oauth_setup_web.py

Then open http://localhost:8080 in your browser.
"""
import os
import sys
import json
import time
import webbrowser
import threading
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from urllib.parse import urlparse, parse_qs
import http.server
import socketserver
import queue
import secrets
import hashlib
import base64
import urllib.parse

app = Flask(__name__)

# Google OAuth
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

GOOGLE_SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Canva OAuth
CANVA_AUTH_URL = "https://www.canva.com/api/oauth/authorize"
CANVA_TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
CANVA_SCOPES = [
    "design:content:read",
    "design:content:write",
    "design:meta:read",
    "brandtemplate:meta:read",
    "brandtemplate:content:read",
    "asset:read",
    "asset:write",
]
DEFAULT_CANVA_REDIRECT_URI = os.getenv(
    "CANVA_REDIRECT_URI",
    "https://oauth.example.com/canva/callback",
)

# Store OAuth state
oauth_state = {
    'google': {'status': 'not_started', 'message': ''},
    'canva': {'status': 'not_started', 'message': ''},
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>OAuth Setup - Easy Mode</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        .header h1 { font-size: 32px; margin-bottom: 10px; }
        .header p { opacity: 0.9; font-size: 16px; }
        .content { padding: 40px; }
        .section {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            border: 2px solid #e9ecef;
        }
        .section h2 {
            color: #333;
            margin-bottom: 15px;
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.pending { background: #fff3cd; color: #856404; }
        .status.not-started { background: #e2e3e5; color: #383d41; }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            margin-top: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        .btn:active { transform: translateY(0); }
        .btn:disabled { opacity: 0.6; cursor: not-allowed; }
        .instructions {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border-left: 4px solid #667eea;
        }
        .instructions ol { margin-left: 20px; }
        .instructions li { margin: 10px 0; line-height: 1.6; }
        .instructions code {
            background: #f1f3f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }
        .file-upload {
            margin: 15px 0;
            padding: 20px;
            border: 2px dashed #667eea;
            border-radius: 8px;
            text-align: center;
            background: #f8f9ff;
        }
        .file-upload input[type="file"] {
            margin: 10px 0;
        }
        .env-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 14px;
            margin: 10px 0;
            font-family: 'Courier New', monospace;
        }
        .message {
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
        .message.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .message.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .message.info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .hidden { display: none; }
        .loading { text-align: center; padding: 20px; }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 OAuth Setup</h1>
            <p>Easy setup for Google Drive and Canva - No terminal needed!</p>
        </div>
        <div class="content">
            <!-- Google Drive Section -->
            <div class="section">
                <h2>
                    📁 Google Drive
                    <span class="status" id="google-status">Not Started</span>
                </h2>
                <div id="google-message"></div>
                
                <div id="google-step1">
                    <div class="instructions">
                        <strong>Step 1: Get your credentials file</strong>
                        <ol>
                            <li>Go to <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
                            <li>Create a project (or select existing)</li>
                            <li>Enable "Google Drive API"</li>
                            <li>Go to "Credentials" → "Create Credentials" → "OAuth client ID"</li>
                            <li>Choose "Desktop app" and download the JSON file</li>
                        </ol>
                    </div>
                    <div class="file-upload">
                        <p><strong>Upload your credentials.json file:</strong></p>
                        <input type="file" id="google-credentials-file" accept=".json">
                        <button class="btn" onclick="uploadGoogleCredentials()">Upload Credentials</button>
                    </div>
                </div>
                
                <div id="google-step2" class="hidden">
                    <div class="message success">
                        ✅ Credentials uploaded! Click the button below to authorize.
                    </div>
                    <button class="btn" onclick="startGoogleOAuth()">Authorize Google Drive</button>
                </div>
            </div>
            
            <!-- Canva Section -->
            <div class="section">
                <h2>
                    🎨 Canva
                    <span class="status" id="canva-status">Not Started</span>
                </h2>
                <div id="canva-message"></div>
                
                <div id="canva-step1">
                    <div class="instructions">
                        <strong>Step 1: Get your Canva credentials</strong>
                        <ol>
                            <li>Go to <a href="https://www.canva.com/developers/" target="_blank">Canva Developers</a></li>
                            <li>Create an app</li>
                            <li>Go to "OAuth" settings</li>
                            <li>Add redirect URI: <code>https://oauth.example.com/canva/callback</code></li>
                            <li>Copy your Client ID (starts with OC-) and Client Secret</li>
                        </ol>
                    </div>
                    <div class="instructions">
                        <strong>Step 2: Enter your credentials</strong>
                    </div>
                    <input type="text" class="env-input" id="canva-client-id" placeholder="CANVA_CLIENT_ID (e.g., OC-XXXXXXXXXXXXX)">
                    <input type="text" class="env-input" id="canva-client-secret" placeholder="CANVA_CLIENT_SECRET">
                    <input type="text" class="env-input" id="canva-redirect-uri" value="https://oauth.example.com/canva/callback" placeholder="CANVA_REDIRECT_URI">
                    <button class="btn" onclick="saveCanvaCredentials()">Save Canva Credentials</button>
                </div>
                
                <div id="canva-step2" class="hidden">
                    <div class="message success">
                        ✅ Credentials saved! Click the button below to authorize.
                    </div>
                    <button class="btn" onclick="startCanvaOAuth()">Authorize Canva</button>
                </div>
            </div>
            
            <!-- Summary -->
            <div class="section">
                <h2>📊 Setup Status</h2>
                <div id="summary">
                    <p>Complete both OAuth setups above to finish.</p>
                </div>
                <button class="btn" onclick="checkStatus()" style="background: #28a745;">Check Status</button>
            </div>
        </div>
    </div>
    
    <script>
        function updateStatus(service, status, message) {
            const statusEl = document.getElementById(service + '-status');
            const messageEl = document.getElementById(service + '-message');
            
            statusEl.textContent = status;
            statusEl.className = 'status ' + status.toLowerCase().replace(' ', '-');
            
            if (message) {
                messageEl.innerHTML = '<div class="message ' + (status === 'Success' ? 'success' : 'info') + '">' + message + '</div>';
            }
        }
        
        function uploadGoogleCredentials() {
            const fileInput = document.getElementById('google-credentials-file');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a file first!');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            fetch('/api/upload-google-credentials', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('google-step1').classList.add('hidden');
                    document.getElementById('google-step2').classList.remove('hidden');
                    updateStatus('google', 'Pending', 'Credentials uploaded successfully!');
                } else {
                    alert('Error: ' + data.error);
                }
            })
            .catch(error => {
                alert('Error: ' + error);
            });
        }
        
        function startGoogleOAuth() {
            updateStatus('google', 'Pending', 'Opening browser for authorization...');
            
            fetch('/api/start-google-oauth', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = data.auth_url;
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }
        
        function saveCanvaCredentials() {
            const clientId = document.getElementById('canva-client-id').value;
            const clientSecret = document.getElementById('canva-client-secret').value;
            const redirectUri = document.getElementById('canva-redirect-uri').value;
            
            if (!clientId || !clientSecret) {
                alert('Please fill in Client ID and Client Secret!');
                return;
            }
            
            fetch('/api/save-canva-credentials', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    client_id: clientId,
                    client_secret: clientSecret,
                    redirect_uri: redirectUri
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('canva-step1').classList.add('hidden');
                    document.getElementById('canva-step2').classList.remove('hidden');
                    updateStatus('canva', 'Pending', 'Credentials saved successfully!');
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }
        
        function startCanvaOAuth() {
            updateStatus('canva', 'Pending', 'Opening browser for authorization...');
            
            fetch('/api/start-canva-oauth', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.open(data.auth_url, '_blank');
                    updateStatus('canva', 'Pending', 'Please complete authorization in the popup window. The page will check for completion automatically...');
                    
                    // Poll for completion
                    let attempts = 0;
                    const maxAttempts = 60; // 60 seconds
                    const pollInterval = setInterval(function() {
                        fetch('/api/status')
                        .then(response => response.json())
                        .then(status => {
                            if (status.canva) {
                                clearInterval(pollInterval);
                                updateStatus('canva', 'Success', '✅ Canva OAuth setup complete!');
                                checkStatus();
                            } else {
                                attempts++;
                                if (attempts >= maxAttempts) {
                                    clearInterval(pollInterval);
                                    updateStatus('canva', 'Pending', 'Still waiting for authorization... Click "Check Status" to verify.');
                                }
                            }
                        });
                    }, 1000);
                } else {
                    alert('Error: ' + data.error);
                }
            });
        }
        
        function checkStatus() {
            fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                let summary = '<ul style="list-style: none; padding: 0;">';
                summary += '<li style="margin: 10px 0;">📁 Google Drive: ' + (data.google ? '✅ Complete' : '❌ Not set up') + '</li>';
                summary += '<li style="margin: 10px 0;">🎨 Canva: ' + (data.canva ? '✅ Complete' : '❌ Not set up') + '</li>';
                summary += '</ul>';
                
                if (data.google && data.canva) {
                    summary += '<div class="message success" style="margin-top: 15px;"><strong>🎉 All set! OAuth setup is complete!</strong></div>';
                }
                
                document.getElementById('summary').innerHTML = summary;
            });
        }
        
        // Check status on load
        window.onload = function() {
            checkStatus();
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/upload-google-credentials', methods=['POST'])
def upload_google_credentials():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if file and file.filename.endswith('.json'):
        try:
            # Save as credentials.json
            file.save('credentials.json')
            
            # Validate it's a valid OAuth client file
            with open('credentials.json', 'r') as f:
                data = json.load(f)
                if 'installed' not in data and 'web' not in data:
                    os.remove('credentials.json')
                    return jsonify({'success': False, 'error': 'Invalid credentials file. Should have "installed" or "web" key.'})
            
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({'success': False, 'error': 'Invalid file type. Please upload a JSON file.'})

@app.route('/api/start-google-oauth', methods=['POST'])
def start_google_oauth():
    if not os.path.exists('credentials.json'):
        return jsonify({'success': False, 'error': 'credentials.json not found. Please upload it first.'})
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GOOGLE_SCOPES)
        flow.redirect_uri = 'http://localhost:8080/google-callback'
        
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        return jsonify({'success': True, 'auth_url': auth_url})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/google-callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        return "Error: No authorization code received", 400
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', GOOGLE_SCOPES)
        flow.redirect_uri = 'http://localhost:8080/google-callback'
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save token
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head><title>Success!</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Google Drive OAuth Complete!</h1>
                <p>You can close this window and return to the setup page.</p>
                <script>setTimeout(function(){ window.close(); }, 3000);</script>
            </body>
            </html>
        """)
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/save-canva-credentials', methods=['POST'])
def save_canva_credentials():
    data = request.json
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')
    redirect_uri = data.get('redirect_uri', DEFAULT_CANVA_REDIRECT_URI)
    
    if not client_id or not client_secret:
        return jsonify({'success': False, 'error': 'Client ID and Secret are required'})
    
    # Save to .env file
    env_content = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_content = f.readlines()
    
    # Update or add Canva credentials
    updated = False
    new_content = []
    for line in env_content:
        if line.startswith('CANVA_CLIENT_ID='):
            new_content.append(f'CANVA_CLIENT_ID={client_id}\n')
            updated = True
        elif line.startswith('CANVA_CLIENT_SECRET='):
            new_content.append(f'CANVA_CLIENT_SECRET={client_secret}\n')
            updated = True
        elif line.startswith('CANVA_REDIRECT_URI='):
            new_content.append(f'CANVA_REDIRECT_URI={redirect_uri}\n')
            updated = True
        else:
            new_content.append(line)
    
    if not updated:
        new_content.append(f'\n# Canva OAuth\n')
        new_content.append(f'CANVA_CLIENT_ID={client_id}\n')
        new_content.append(f'CANVA_CLIENT_SECRET={client_secret}\n')
        new_content.append(f'CANVA_REDIRECT_URI={redirect_uri}\n')
    
    with open('.env', 'w') as f:
        f.writelines(new_content)
    
    return jsonify({'success': True})

# Global variable to store Canva callback server
canva_callback_server = None
canva_code_queue = None

def start_canva_callback_server(redirect_uri):
    """Start a local server to receive Canva OAuth callback."""
    global canva_callback_server, canva_code_queue
    from urllib.parse import urlparse
    parsed_uri = urlparse(redirect_uri)
    port = parsed_uri.port or 3001
    path = parsed_uri.path or '/oauth/redirect'
    
    canva_code_queue = queue.Queue()
    
    class CanvaCallbackHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urlparse(self.path)
            if parsed_path.path in [path, '/callback', '/oauth/redirect']:
                query_params = parse_qs(parsed_path.query)
                code = query_params.get('code', [None])[0]
                error = query_params.get('error', [None])[0]
                
                if error:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f'''
                        <html>
                        <body style="font-family: Arial; text-align: center; padding: 50px;">
                            <h1 style="color: red;">❌ Error: {error}</h1>
                            <p>You can close this window.</p>
                        </body>
                        </html>
                    '''.encode())
                    if canva_code_queue:
                        canva_code_queue.put(('error', error))
                    return
                
                if code:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write('''
                        <html>
                        <body style="font-family: Arial; text-align: center; padding: 50px;">
                            <h1 style="color: green;">✅ Authorization received!</h1>
                            <p>Processing... You can close this window.</p>
                            <script>setTimeout(function(){ window.close(); }, 2000);</script>
                        </body>
                        </html>
                    '''.encode())
                    if canva_code_queue:
                        canva_code_queue.put(('code', code))
                    # Process token in background
                    threading.Thread(target=lambda: process_canva_token(code), daemon=True).start()
                    return
            
            self.send_response(404)
            self.end_headers()
        
        def log_message(self, format, *args):
            pass  # Suppress server logs
    
    handler = CanvaCallbackHandler
    canva_callback_server = socketserver.TCPServer(("", port), handler)
    canva_callback_server.timeout = 300
    
    # Start server in background
    def run_server():
        canva_callback_server.handle_request()
        canva_callback_server.server_close()
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    return canva_callback_server

@app.route('/api/start-canva-oauth', methods=['POST'])
def start_canva_oauth():
    from dotenv import load_dotenv
    load_dotenv()
    
    client_id = os.getenv('CANVA_CLIENT_ID')
    client_secret = os.getenv('CANVA_CLIENT_SECRET')
    redirect_uri = os.getenv('CANVA_REDIRECT_URI', DEFAULT_CANVA_REDIRECT_URI)
    
    if not client_id or not client_secret:
        return jsonify({'success': False, 'error': 'Canva credentials not found. Please save them first.'})
    
    # Generate PKCE
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode('utf-8').rstrip('=')
    
    # Store for later
    with open('.canva_pkce.json', 'w') as f:
        json.dump({
            'code_verifier': code_verifier, 
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret
        }, f)
    
    # Start callback server in background
    start_canva_callback_server(redirect_uri)
    
    # Generate auth URL
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': ' '.join(CANVA_SCOPES),
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }
    auth_url = f"{CANVA_AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    return jsonify({'success': True, 'auth_url': auth_url})

def process_canva_token(code):
    """Process Canva authorization code and save tokens."""
    try:
        # Load PKCE and credentials
        with open('.canva_pkce.json', 'r') as f:
            pkce_data = json.load(f)
        
        # Exchange code for token
        import requests
        data = {
            'grant_type': 'authorization_code',
            'client_id': pkce_data['client_id'],
            'client_secret': pkce_data['client_secret'],
            'code': code,
            'redirect_uri': pkce_data['redirect_uri'],
            'code_verifier': pkce_data['code_verifier'],
        }
        
        response = requests.post(CANVA_TOKEN_URL, data=data)
        if response.status_code != 200:
            print(f"Error exchanging token: {response.text}")
            return False
        
        tokens = response.json()
        tokens['token_refreshed_at'] = time.time()
        
        # Save tokens
        with open('canva_tokens.json', 'w') as f:
            json.dump(tokens, f, indent=2)
        
        # Clean up
        if os.path.exists('.canva_pkce.json'):
            os.remove('.canva_pkce.json')
        
        return True
    except Exception as e:
        print(f"Error processing Canva token: {e}")
        return False

# Canva callback is handled by the background server started in start_canva_oauth
# The server listens on the redirect URI port and processes the callback

@app.route('/api/status')
def status():
    google = os.path.exists('token.json')
    canva = os.path.exists('canva_tokens.json')
    return jsonify({'google': google, 'canva': canva})

if __name__ == '__main__':
    print("=" * 70)
    print("🌐 OAuth Setup Web Interface")
    print("=" * 70)
    print()
    print("Starting web server...")
    print("Open your browser and go to: http://localhost:8080")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    print()
    
    # Try to open browser automatically
    try:
        threading.Timer(1.5, lambda: webbrowser.open('http://localhost:8080')).start()
    except:
        pass
    
    app.run(host='0.0.0.0', port=8080, debug=False)

