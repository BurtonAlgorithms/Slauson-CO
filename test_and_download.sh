#!/bin/bash

# Test webhook and automatically download the slide
# Usage: ./test_and_download.sh

WEBHOOK_URL="https://sauson-automation-3.onrender.com/webhook/onboarding"
PAYLOAD_FILE="test_real_payload.json"
RESPONSE_FILE="webhook_response.json"

echo "🚀 Testing webhook..."
echo ""

# Send request and save response
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d @$PAYLOAD_FILE \
  -o $RESPONSE_FILE \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -s

echo ""
echo "📥 Response saved to: $RESPONSE_FILE"
echo ""

# Check if PDF is in response
if grep -q "pdf_base64" "$RESPONSE_FILE"; then
    echo "✅ PDF found in response!"
    echo "📥 Downloading slide..."
    python3 download_slide.py "$RESPONSE_FILE"
else
    echo "❌ No PDF in response. Check $RESPONSE_FILE for errors."
    cat "$RESPONSE_FILE" | python3 -m json.tool
fi

