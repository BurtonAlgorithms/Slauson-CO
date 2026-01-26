#!/usr/bin/env python3
"""
Master OAuth Setup Script

This script guides you through setting up OAuth for both Google Drive and Canva APIs.
It's designed to work even if you don't have access to the GitHub repository.

Usage:
    python setup_oauth.py

For detailed instructions, see: OAUTH_SETUP_GUIDE.md
"""
import os
import sys

def print_header():
    """Print main header."""
    print("=" * 70)
    print("🔐 OAuth Setup Wizard")
    print("=" * 70)
    print()
    print("This wizard will help you set up OAuth authentication for:")
    print("  • Google Drive API")
    print("  • Canva API")
    print()
    print("You can set up one or both services.")
    print()

def check_prerequisites():
    """Check if prerequisites are met."""
    print("📋 Checking prerequisites...")
    print()
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append(f"❌ Python 3.8+ required (you have {sys.version_info.major}.{sys.version_info.minor})")
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check for required packages
    required_packages = {
        'google-auth-oauthlib': 'Google OAuth',
        'google-auth': 'Google OAuth',
        'requests': 'Canva OAuth',
        'dotenv': 'Environment variables',
    }
    
    for package, name in required_packages.items():
        try:
            if package == 'dotenv':
                __import__('dotenv')
            elif package == 'google-auth-oauthlib':
                __import__('google_auth_oauthlib')
            elif package == 'google-auth':
                __import__('google.auth')
            elif package == 'requests':
                __import__('requests')
            print(f"✅ {name} package installed")
        except ImportError:
            issues.append(f"❌ {name} package not installed (pip install {package})")
    
    print()
    
    if issues:
        print("⚠️  Some prerequisites are missing:")
        for issue in issues:
            print(f"   {issue}")
        print()
        response = input("Continue anyway? (y/N): ").strip().lower()
        if response != 'y':
            return False
    
    return True

def setup_google_oauth():
    """Set up Google Drive OAuth."""
    print("=" * 70)
    print("📁 Google Drive OAuth Setup")
    print("=" * 70)
    print()
    
    try:
        from setup_google_oauth import setup_oauth
        creds = setup_oauth()
        return creds is not None
    except ImportError as e:
        print(f"❌ Error: Could not import Google OAuth setup: {e}")
        print("   Make sure setup_google_oauth.py is in the current directory.")
        return False
    except Exception as e:
        print(f"❌ Error during Google OAuth setup: {e}")
        import traceback
        traceback.print_exc()
        return False

def setup_canva_oauth():
    """Set up Canva OAuth."""
    print("=" * 70)
    print("🎨 Canva OAuth Setup")
    print("=" * 70)
    print()
    
    try:
        from setup_canva_oauth import setup_oauth
        success = setup_oauth()
        return success
    except ImportError as e:
        print(f"❌ Error: Could not import Canva OAuth setup: {e}")
        print("   Make sure setup_canva_oauth.py is in the current directory.")
        return False
    except Exception as e:
        print(f"❌ Error during Canva OAuth setup: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_summary():
    """Show setup summary."""
    print()
    print("=" * 70)
    print("📊 Setup Summary")
    print("=" * 70)
    print()
    
    # Check Google Drive
    if os.path.exists('token.json'):
        print("✅ Google Drive: token.json found")
    else:
        print("❌ Google Drive: token.json not found")
    
    # Check Google credentials
    if os.path.exists('credentials.json'):
        print("✅ Google Drive: credentials.json found")
    else:
        print("⚠️  Google Drive: credentials.json not found (needed for OAuth)")
    
    # Check Canva
    if os.path.exists('canva_tokens.json'):
        print("✅ Canva: canva_tokens.json found")
    else:
        print("❌ Canva: canva_tokens.json not found")
    
    # Check .env
    if os.path.exists('.env'):
        print("✅ Environment: .env file found")
        # Check for Canva credentials
        from dotenv import load_dotenv
        load_dotenv()
        canva_id = os.getenv('CANVA_CLIENT_ID')
        canva_secret = os.getenv('CANVA_CLIENT_SECRET')
        if canva_id and canva_secret:
            print("✅ Canva: Credentials found in .env")
        else:
            print("⚠️  Canva: Credentials not found in .env")
    else:
        print("⚠️  Environment: .env file not found")
    
    print()

def main():
    """Main setup wizard."""
    print_header()
    
    # Check prerequisites
    if not check_prerequisites():
        print("Setup cancelled.")
        sys.exit(1)
    
    # Ask what to set up
    print("What would you like to set up?")
    print()
    print("1. Google Drive OAuth only")
    print("2. Canva OAuth only")
    print("3. Both Google Drive and Canva")
    print("4. Show current setup status")
    print("5. Exit")
    print()
    
    choice = input("Enter your choice (1-5): ").strip()
    print()
    
    if choice == '1':
        success = setup_google_oauth()
        if success:
            print("\n✅ Google Drive OAuth setup complete!")
        else:
            print("\n❌ Google Drive OAuth setup failed.")
            sys.exit(1)
    
    elif choice == '2':
        success = setup_canva_oauth()
        if success:
            print("\n✅ Canva OAuth setup complete!")
        else:
            print("\n❌ Canva OAuth setup failed.")
            sys.exit(1)
    
    elif choice == '3':
        print("Setting up both services...")
        print()
        
        google_success = setup_google_oauth()
        print()
        
        canva_success = setup_canva_oauth()
        print()
        
        if google_success and canva_success:
            print("✅ Both OAuth setups complete!")
        else:
            if not google_success:
                print("❌ Google Drive OAuth setup failed.")
            if not canva_success:
                print("❌ Canva OAuth setup failed.")
            sys.exit(1)
    
    elif choice == '4':
        show_summary()
        return
    
    elif choice == '5':
        print("Exiting...")
        sys.exit(0)
    
    else:
        print("Invalid choice. Please run the script again.")
        sys.exit(1)
    
    # Show summary
    show_summary()
    
    # Final instructions
    print("=" * 70)
    print("📝 Next Steps")
    print("=" * 70)
    print()
    print("For local development:")
    print("  • Your tokens are saved and will be used automatically")
    print()
    print("For production (Render/Railway):")
    print("  • See OAUTH_SETUP_GUIDE.md for environment variable setup")
    print("  • Copy token values to your deployment platform")
    print()
    print("For detailed instructions, see: OAUTH_SETUP_GUIDE.md")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

