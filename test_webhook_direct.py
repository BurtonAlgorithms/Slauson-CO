#!/usr/bin/env python3
"""
Direct Webhook Test Script
Test the webhook endpoint directly without Zapier
"""

import requests
import json
import sys

# Configuration
WEBHOOK_URL = "http://localhost:5001/webhook/onboarding"  # Default port is 5001, change if using ngrok or production

# Example test data matching your Zapier payload format
test_payload = {
    "company_data__name": "Astranis",
    "company_data__description": "Astranis Space Technologies is a private American satellite manufacturer and service provider that aims to connect the unconnected. They are known for pioneering a new class of MicroGEO satellites—smaller, cheaper, and faster to build than traditional geostationary satellites.",
    "company_data__address": "Los Angeles, CA",
    "company_data__investment_date": "2024-01-15",
    "company_data__investment_round": "PRE-SEED",
    "company_data__quarter": "Q2",
    "company_data__year": "2024",
    "company_data__founders": "John Gedmark, Ryan McLinko",
    "company_data__co_investors": "Blackrock, Fidelity",
    "company_data__background": "Astranis Space Technologies is a private American satellite manufacturer and service provider that aims to connect the unconnected. They are known for pioneering a new class of MicroGEO satellites—smaller, cheaper, and faster to build than traditional geostationary satellites.",
    "headshot_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400",  # Test image URL
    "logo_url": "https://images.unsplash.com/photo-1611262588024-d12430b98920?w=400&h=400&fit=crop",  # Placeholder logo - replace with actual Astranis logo URL when available
    "notion_page_id": "test-page-id-12345",
    "notion_created_time": "2024-01-01T00:00:00Z",
    "notion_last_edited": "2024-01-01T00:00:00Z",
    "status": "pending"
}

def test_webhook():
    """Test the webhook endpoint directly"""
    print("=" * 60)
    print("Testing Webhook Directly")
    print("=" * 60)
    print(f"\nURL: {WEBHOOK_URL}")
    print(f"\nPayload:")
    print(json.dumps(test_payload, indent=2))
    print("\n" + "=" * 60)
    
    try:
        print("\nSending POST request...")
        response = requests.post(
            WEBHOOK_URL,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minute timeout for processing
        )
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"\nResponse JSON:")
            print(json.dumps(response_data, indent=2))
        except:
            print(f"\nResponse Text:")
            print(response.text)
        
        if response.status_code == 200:
            print("\n✅ SUCCESS! Webhook processed successfully")
            if isinstance(response_data, dict):
                if response_data.get("success"):
                    print(f"   - Google Drive Link: {response_data.get('google_drive_link', 'N/A')}")
                    print(f"   - DocSend Link: {response_data.get('docsend_link', 'N/A')}")
                else:
                    print(f"   - Errors: {response_data.get('errors', [])}")
        else:
            print(f"\n❌ ERROR: Status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ CONNECTION ERROR: Could not connect to server")
        print("   Make sure the server is running:")
        print("   python webhook_listener.py")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\n⏱️  TIMEOUT: Request took too long (>5 minutes)")
        print("   The server might still be processing. Check server logs.")
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Allow custom URL via command line
    if len(sys.argv) > 1:
        WEBHOOK_URL = sys.argv[1]
        print(f"Using custom URL: {WEBHOOK_URL}")
    
    test_webhook()

