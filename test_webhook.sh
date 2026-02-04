#!/bin/bash

# Test webhook with realistic payload
# Usage: ./test_webhook.sh

WEBHOOK_URL="http://localhost:5001/webhook/onboarding"
PAYLOAD_FILE="test_real_payload.json"

echo "Testing webhook at: $WEBHOOK_URL"
echo "Using payload from: $PAYLOAD_FILE"
echo ""
echo "Sending request..."
echo ""

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d @$PAYLOAD_FILE \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -v

echo ""
echo "Done! Check Render logs for processing details."

