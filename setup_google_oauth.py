"""
Setup OAuth for Google Drive API.

This script will:
1. Guide you through creating OAuth credentials (if needed)
2. Open a browser for you to authorize the application
3. Save your authorization token for future use

For detailed instructions, see: OAUTH_SETUP_GUIDE.md
"""
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes needed for Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def print_header():
    """Print setup header."""
    print("=" * 70)
    print("🔐 Google Drive OAuth Setup")
    print("=" * 70)
    print()

def print_instructions():
    """Print detailed setup instructions."""
    print("📋 SETUP INSTRUCTIONS")
    print("-" * 70)
    print()
    print("To set up Google Drive OAuth, you need to create OAuth credentials.")
    print()
    print("Step 1: Go to Google Cloud Console")
    print("   → https://console.cloud.google.com/")
    print()
    print("Step 2: Create or select a project")
    print("   → Click project dropdown → 'New Project'")
    print()
    print("Step 3: Enable Google Drive API")
    print("   → APIs & Services → Library → Search 'Google Drive API' → Enable")
    print()
    print("Step 4: Configure OAuth Consent Screen")
    print("   → APIs & Services → OAuth consent screen")
    print("   → Choose 'External' (for personal accounts)")
    print("   → Fill in app name, support email")
    print("   → Add scopes: https://www.googleapis.com/auth/drive.file")
    print("   → Add your email as a test user (IMPORTANT!)")
    print()
    print("Step 5: Create OAuth Credentials")
    print("   → APIs & Services → Credentials → Create Credentials → OAuth client ID")
    print("   → Application type: 'Desktop app'")
    print("   → Download the JSON file")
    print("   → Save it as 'credentials.json' in this directory")
    print()
    print("For detailed instructions, see: OAUTH_SETUP_GUIDE.md")
    print()
    print("=" * 70)
    print()

def check_credentials_file():
    """Check if credentials.json exists and is valid."""
    if not os.path.exists('credentials.json'):
        return False
    
    try:
        import json
        with open('credentials.json', 'r') as f:
            creds_data = json.load(f)
        
        # Check if it's a valid OAuth client JSON
        if 'installed' in creds_data or 'web' in creds_data:
            return True
        else:
            print("⚠️  Warning: credentials.json doesn't look like a valid OAuth client file.")
            print("   It should have 'installed' or 'web' keys.")
            return False
    except json.JSONDecodeError:
        print("⚠️  Warning: credentials.json is not valid JSON.")
        return False
    except Exception as e:
        print(f"⚠️  Warning: Error reading credentials.json: {e}")
        return False

def setup_oauth():
    """Set up OAuth for Google Drive."""
    print_header()
    
    # Check if we already have a valid token
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if creds and creds.valid:
                print("✅ Found existing valid token!")
                email = None
                if hasattr(creds, 'id_token') and creds.id_token:
                    email = creds.id_token.get('email')
                elif hasattr(creds, 'token') and creds.token:
                    # Try to get email from token info
                    try:
                        from google.oauth2 import id_token
                        from google.auth.transport.requests import Request
                        info = id_token.verify_oauth2_token(creds.token, Request())
                        email = info.get('email')
                    except:
                        pass
                
                if email:
                    print(f"   Authorized for: {email}")
                else:
                    print("   Token is valid and ready to use")
                print()
                
                response = input("Do you want to re-authorize? (y/N): ").strip().lower()
                if response != 'y':
                    print("✅ Using existing token. Setup complete!")
                    return creds
            elif creds and creds.expired and creds.refresh_token:
                print("⚠️  Token expired, attempting to refresh...")
                try:
                    creds.refresh(Request())
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                    print("✅ Token refreshed successfully!")
                    return creds
                except Exception as e:
                    print(f"⚠️  Could not refresh token: {e}")
                    print("   Will need to re-authorize...")
                    print()
        except Exception as e:
            print(f"⚠️  Error loading existing token: {e}")
            print("   Will need to re-authorize...")
            print()
    
    # Check for credentials.json
    if not check_credentials_file():
        print_instructions()
        print("❌ 'credentials.json' not found or invalid.")
        print()
        print("Please follow the instructions above to create credentials.json")
        print("Then run this script again.")
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
        
        return None
    
    # Start OAuth flow
    print("🚀 Starting OAuth flow...")
    print()
    print("A browser window will open for you to sign in and authorize.")
    print("Make sure you're signed in to the Google account you want to use.")
    print()
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES
        )
        print("📂 Loaded credentials.json")
        print("🌐 Opening browser for authorization...")
        print()
        
        creds = flow.run_local_server(port=0, open_browser=True)
        
        # Get user email if possible
        email = None
        try:
            if hasattr(creds, 'id_token') and creds.id_token:
                email = creds.id_token.get('email')
        except:
            pass
        
        # Save the credentials
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        
        print()
        print("=" * 70)
        print("✅ OAuth setup complete!")
        print("=" * 70)
        print()
        print("✅ Token saved to: token.json")
        if email:
            print(f"✅ Authorized for: {email}")
        else:
            print("✅ Authorization successful!")
        print()
        print("📝 Next steps:")
        print("   • Your token will be used automatically by the application")
        print("   • Tokens expire after ~1 hour but refresh automatically")
        print("   • For production (Render/Railway), copy token.json content to")
        print("     GOOGLE_DRIVE_CREDENTIALS_JSON environment variable")
        print()
        
        return creds
        
    except FileNotFoundError:
        print("❌ Error: credentials.json not found!")
        print("   Please make sure credentials.json is in the current directory.")
        return None
    except Exception as e:
        print(f"❌ Error during OAuth flow: {e}")
        print()
        print("Common issues:")
        print("  • credentials.json is invalid or corrupted")
        print("  • Your email is not added as a test user in OAuth consent screen")
        print("  • Google Drive API is not enabled in your project")
        print("  • Network/firewall blocking the callback")
        print()
        print("See OAUTH_SETUP_GUIDE.md for detailed troubleshooting.")
        return None

if __name__ == '__main__':
    try:
        creds = setup_oauth()
        if creds:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


