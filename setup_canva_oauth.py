"""
One-time OAuth setup script for Canva API.
This script will:
1. Open a browser for you to log in to Canva
2. Get access token + refresh token
3. Store them for future use
"""
import os
import json
import secrets
import hashlib
import base64
import urllib.parse
import webbrowser
import http.server
import socketserver
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from config import Config

# Load environment variables
load_dotenv()

# OAuth configuration
CANVA_AUTH_URL = "https://www.canva.com/api/oauth/authorize"
# Try different token endpoints - Canva might use a different path
CANVA_TOKEN_URLS = [
    "https://api.canva.com/rest/v1/oauth/token",  # REST API endpoint
    "https://www.canva.com/api/oauth/token",      # Alternative endpoint
    "https://api.canva.com/v1/oauth2/token",     # Original (seems to not exist)
]
CANVA_TOKEN_URL = CANVA_TOKEN_URLS[0]  # Start with REST API endpoint
# IMPORTANT: This redirect URI must match EXACTLY what you configured in your Canva app
# Use a non-localhost URL by default and set CANVA_REDIRECT_URI to your public callback URL.
REDIRECT_URI = os.getenv("CANVA_REDIRECT_URI", "https://oauth.example.com/canva/callback")
SCOPES = [
    "design:content:read",
    "design:content:write",
    "design:meta:read",
    "brandtemplate:meta:read",
    "brandtemplate:content:read",
    "asset:read",
    "asset:write",
]

TOKEN_FILE = "canva_tokens.json"


def generate_pkce():
    """Generate PKCE code verifier and challenge."""
    # Generate code verifier (random string)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
    code_verifier = code_verifier.rstrip('=')
    
    # Generate code challenge (SHA256 hash of verifier)
    code_challenge = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode('utf-8')
    code_challenge = code_challenge.rstrip('=')
    
    return code_verifier, code_challenge


def get_authorization_url(client_id: str, code_challenge: str, redirect_uri: str = None) -> str:
    """Generate the authorization URL."""
    redirect_uri_to_use = redirect_uri or REDIRECT_URI
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri_to_use,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    
    return f"{CANVA_AUTH_URL}?{urllib.parse.urlencode(params)}"


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """Handle OAuth callback."""
    
    def __init__(self, *args, code_queue=None, **kwargs):
        self.code_queue = code_queue
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET request from OAuth callback."""
        parsed_path = urlparse(self.path)
        
        # Handle various callback paths (Canva may redirect to different paths)
        callback_paths = ["/callback", "/oauth/redirect", "/return-nav"]
        if parsed_path.path in callback_paths:
            query_params = parse_qs(parsed_path.query)
            code = query_params.get("code", [None])[0]
            error = query_params.get("error", [None])[0]
            
            if error:
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(f"""
                    <html>
                    <body>
                        <h1>❌ OAuth Error</h1>
                        <p>Error: {error}</p>
                        <p>You can close this window.</p>
                    </body>
                    </html>
                """.encode())
                if self.code_queue:
                    self.code_queue.put(("error", error))
                return
            
            if code:
                # Get the actual redirect URI that was used (from the request)
                actual_redirect_uri = f"http://{self.headers.get('Host', '127.0.0.1:3001')}{parsed_path.path}"
                print(f"   Actual redirect URI used: {actual_redirect_uri}")
                
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("""
                    <html>
                    <body>
                        <h1>✅ Authorization Successful!</h1>
                        <p>You can close this window.</p>
                    </body>
                    </html>
                """.encode())
                if self.code_queue:
                    # Pass both code and actual redirect URI
                    self.code_queue.put(("code", code, actual_redirect_uri))
                return
        
        # Default response
        self.send_response(404)
        self.end_headers()


def exchange_code_for_token(client_id: str, client_secret: str, code: str, code_verifier: str, redirect_uri: str = None) -> dict:
    """Exchange authorization code for access token."""
    # Use provided redirect URI or fall back to default
    redirect_uri_to_use = redirect_uri or REDIRECT_URI
    
    data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri_to_use,
        "code_verifier": code_verifier,
    }
    
    import requests
    print(f"   Redirect URI: {redirect_uri_to_use}")
    print(f"   Code length: {len(code)}")
    print(f"   Code verifier length: {len(code_verifier)}")
    
    # Use only the official REST OAuth token endpoint
    token_endpoints = [
        "https://api.canva.com/rest/v1/oauth/token",
    ]
    
    last_error = None
    for token_url in token_endpoints:
        print(f"   Trying endpoint: {token_url}")
        
        # REST API endpoint requires form-urlencoded for token exchange (not JSON)
        # Only use form-urlencoded for OAuth token exchange
        try:
            response = requests.post(
                token_url,
                data=data  # form-urlencoded (required for OAuth token exchange)
            )
            if response.status_code == 200:
                print(f"   ✓ Token exchange successful!")
                return response.json()
            elif response.status_code == 404:
                print(f"   Endpoint not found (404), trying next...")
                last_error = f"404: {response.text[:200]}"
                continue
            else:
                error_text = response.text[:300]
                print(f"   Token exchange failed with status {response.status_code}: {error_text}")
                last_error = f"{response.status_code}: {error_text}"
                continue
        except Exception as e:
            print(f"   Error: {e}")
            last_error = str(e)
            continue
    
    # If all endpoints failed
    raise Exception(f"All token endpoints failed. Last error: {last_error}")


def save_tokens(tokens: dict):
    """Save tokens to file."""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)
    print(f"✓ Tokens saved to {TOKEN_FILE}")


def print_header():
    """Print setup header."""
    print("=" * 70)
    print("🔐 Canva OAuth Setup")
    print("=" * 70)
    print()

def print_instructions():
    """Print detailed setup instructions."""
    print("📋 SETUP INSTRUCTIONS")
    print("-" * 70)
    print()
    print("To set up Canva OAuth, you need to create a Canva app and get credentials.")
    print()
    print("Step 1: Create a Canva App")
    print("   → Go to: https://www.canva.com/developers/")
    print("   → Sign in with your Canva account")
    print("   → Click 'Create an app'")
    print("   → Fill in app name and details")
    print()
    print("Step 2: Configure OAuth Settings")
    print("   → In your app dashboard, go to 'OAuth' or 'Authentication'")
    print("   → Add redirect URI: https://oauth.example.com/canva/callback")
    print("   → Note your Client ID (starts with OC-) and Client Secret")
    print()
    print("Step 3: Add to .env file")
    print("   → Create or edit .env file in this directory")
    print("   → Add these lines:")
    print("     CANVA_CLIENT_ID=OC-XXXXXXXXXXXXX")
    print("     CANVA_CLIENT_SECRET=your_client_secret_here")
    print("     CANVA_REDIRECT_URI=https://oauth.example.com/canva/callback")
    print()
    print("For detailed instructions, see: OAUTH_SETUP_GUIDE.md")
    print()
    print("=" * 70)
    print()

def check_existing_tokens():
    """Check if we already have valid tokens."""
    if os.path.exists(TOKEN_FILE):
        try:
            import json
            with open(TOKEN_FILE, 'r') as f:
                tokens = json.load(f)
            
            if tokens.get('access_token') and tokens.get('refresh_token'):
                print("✅ Found existing tokens!")
                print(f"   Token file: {TOKEN_FILE}")
                print()
                
                response = input("Do you want to re-authorize? (y/N): ").strip().lower()
                if response != 'y':
                    print("✅ Using existing tokens. Setup complete!")
                    return True
        except Exception as e:
            print(f"⚠️  Warning: Error reading existing tokens: {e}")
            print()
    
    return False

def setup_oauth():
    """Main OAuth setup function."""
    print_header()
    
    # Check for existing tokens
    if check_existing_tokens():
        return True
    
    # Check for credentials in .env
    client_id = Config.CANVA_CLIENT_ID
    client_secret = Config.CANVA_CLIENT_SECRET
    redirect_uri = os.getenv("CANVA_REDIRECT_URI", REDIRECT_URI)
    
    if not client_id or not client_secret:
        print_instructions()
        print("❌ Error: CANVA_CLIENT_ID and CANVA_CLIENT_SECRET must be set in .env")
        print()
        print("Please follow the instructions above to set up your .env file.")
        print()
        
        # Check if .env exists
        if not os.path.exists('.env'):
            print("💡 Tip: Create a .env file in this directory with:")
            print("   CANVA_CLIENT_ID=OC-XXXXXXXXXXXXX")
            print("   CANVA_CLIENT_SECRET=your_secret_here")
            print("   CANVA_REDIRECT_URI=https://oauth.example.com/canva/callback")
            print()
        
        # Offer to open the guide
        response = input("Would you like to see the full setup guide? (Y/n): ").strip().lower()
        if response != 'n':
            guide_path = os.path.join(os.path.dirname(__file__), 'OAUTH_SETUP_GUIDE.md')
            if os.path.exists(guide_path):
                print(f"\n📖 Opening guide: {guide_path}")
                try:
                    import subprocess
                    import platform
                    if platform.system() == 'Darwin':  # macOS
                        subprocess.run(['open', guide_path])
                    elif platform.system() == 'Windows':
                        subprocess.run(['start', guide_path], shell=True)
                    else:  # Linux
                        subprocess.run(['xdg-open', guide_path])
                except:
                    print(f"   Please open manually: {guide_path}")
            else:
                print("   Guide not found. Please see the instructions above.")
        
        return False
    
    print("✅ Found Canva credentials in .env")
    print(f"   Client ID: {client_id[:20]}...")
    print(f"   Redirect URI: {redirect_uri}")
    print()
    print("This will:")
    print("1. Open a browser for you to log in to Canva")
    print("2. Get access token + refresh token")
    print("3. Store them for future use")
    print()
    
    # Generate PKCE
    code_verifier, code_challenge = generate_pkce()
    print("✓ Generated PKCE code challenge")
    
    # Get authorization URL (use redirect URI from env if set)
    redirect_uri_to_use = os.getenv("CANVA_REDIRECT_URI", REDIRECT_URI)
    
    auth_url = get_authorization_url(client_id, code_challenge, redirect_uri_to_use)
    print(f"✓ Generated authorization URL")
    print(f"   Using redirect URI: {redirect_uri_to_use}")
    print()
    
    # Parse redirect URI to get port/host for local callback
    from urllib.parse import urlparse
    parsed_uri = urlparse(redirect_uri_to_use)
    host = parsed_uri.hostname or ""
    port = parsed_uri.port

    # This script runs a local callback server. If redirect URI is not local,
    # tell the user to use the web UI or set a localhost redirect.
    if host not in ("localhost", "127.0.0.1"):
        print("❌ Redirect URI is not local.")
        print(f"   Current CANVA_REDIRECT_URI: {redirect_uri_to_use}")
        print("   This script can only receive callbacks on localhost.")
        print("   Fix: set CANVA_REDIRECT_URI to a localhost URL and try again:")
        print("     CANVA_REDIRECT_URI=http://127.0.0.1:3001/oauth/redirect")
        print("   Or use the web UI/hosted OAuth flow for non-local URLs.")
        return False

    if not port:
        # Default port if not specified
        port = 3001
    
    # Check if port is available
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_in_use = sock.connect_ex(('127.0.0.1', port)) == 0
    sock.close()
    
    if port_in_use:
        print(f"⚠️  Warning: Port {port} is already in use.")
        print(f"   Make sure no other application is using this port.")
        print(f"   Or change CANVA_REDIRECT_URI in .env to use a different port.")
        print()
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    # Start local server to receive callback
    import queue
    code_queue = queue.Queue()
    
    handler = lambda *args, **kwargs: OAuthCallbackHandler(*args, code_queue=code_queue, **kwargs)
    try:
        httpd = socketserver.TCPServer(("", port), handler)
    except OSError as e:
        print(f"❌ Error: Could not start server on port {port}: {e}")
        print(f"   Port may be in use. Try changing CANVA_REDIRECT_URI in .env")
        return False
    
    print("🌐 Opening browser for Canva login...")
    print(f"   URL: {auth_url[:100]}...")
    print()
    print("⏳ Waiting for authorization...")
    print("   (Please log in to Canva in the browser and click 'Allow')")
    print("   (You can close this window after authorization)")
    print()
    
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"   Please open this URL manually:")
        print(f"   {auth_url}")
        print()
    
    # Wait for callback
    httpd.timeout = 300  # 5 minutes timeout
    try:
        httpd.handle_request()
    except Exception as e:
        print(f"❌ Error waiting for callback: {e}")
        httpd.server_close()
        return False
    finally:
        httpd.server_close()
    
    # Get code from queue
    try:
        result = code_queue.get(timeout=1)
        # Handle both error (2 values) and code (3 values) cases
        if len(result) == 2:
            result_type, result_value = result
            actual_redirect_uri = REDIRECT_URI  # Use default if not provided
        else:
            result_type, result_value, actual_redirect_uri = result
    except queue.Empty:
        print("❌ No authorization code received")
        return False
    
    if result_type == "error":
        print(f"❌ OAuth error: {result_value}")
        return False
    
    code = result_value
    print("✓ Received authorization code")
    print(f"   Using redirect URI: {actual_redirect_uri}")
    print()
    
    # Exchange code for token
    print("🔄 Exchanging code for access token...")
    try:
        tokens = exchange_code_for_token(client_id, client_secret, code, code_verifier, actual_redirect_uri)
        
        if "access_token" not in tokens:
            print(f"❌ No access token in response: {tokens}")
            return False
        
        print("✓ Got access token and refresh token")
        print()
        
        # Save tokens with timestamp
        import time
        tokens['token_refreshed_at'] = time.time()
        save_tokens(tokens)
        
        print("=" * 70)
        print("✅ OAuth setup complete!")
        print("=" * 70)
        print()
        print("✅ Tokens saved to: canva_tokens.json")
        print()
        print("📝 Next steps:")
        print("   • Your tokens will be used automatically by the application")
        print("   • Access tokens expire after ~4 hours but refresh automatically")
        print("   • For production (Render/Railway), set these environment variables:")
        print("     - CANVA_CLIENT_ID")
        print("     - CANVA_CLIENT_SECRET")
        print("     - CANVA_REFRESH_TOKEN (from canva_tokens.json)")
        print("     - CANVA_ACCESS_TOKEN (from canva_tokens.json)")
        print("     - CANVA_TOKEN_REFRESHED_AT (current timestamp)")
        print("     - CANVA_REDIRECT_URI")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error exchanging code for token: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    try:
        success = setup_oauth()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

