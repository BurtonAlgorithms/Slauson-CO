#!/usr/bin/env python3
"""
Download Canva slide from webhook response.
Usage: python download_slide.py <response_json_file>
"""

import json
import base64
import sys
import os

def download_slide_from_response(response_file):
    """Extract and save PDF from webhook response."""
    with open(response_file, 'r') as f:
        response = json.load(f)
    
    if "pdf_base64" in response:
        pdf_bytes = base64.b64decode(response["pdf_base64"])
        filename = response.get("pdf_filename", "slide.pdf")
        
        with open(filename, 'wb') as f:
            f.write(pdf_bytes)
        
        print(f"✅ Slide saved to: {filename}")
        print(f"📄 File size: {len(pdf_bytes)} bytes")
        return filename
    else:
        print("❌ No PDF found in response")
        if "errors" in response:
            print("Errors:", response["errors"])
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_slide.py <response_json_file>")
        print("\nExample:")
        print("  1. Save webhook response to response.json")
        print("  2. Run: python download_slide.py response.json")
        sys.exit(1)
    
    response_file = sys.argv[1]
    if not os.path.exists(response_file):
        print(f"❌ File not found: {response_file}")
        sys.exit(1)
    
    download_slide_from_response(response_file)

