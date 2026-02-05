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

# Local headshot override (served via a tiny local HTTP server so the backend can download it).
# You can override this path when running:
#   HEADSHOT_PATH="/path/to/headshot.png" ./test_webhook.sh
HEADSHOT_PATH_DEFAULT="/Users/henoktewolde/.cursor/projects/Users-henoktewolde-Slauson-CO/assets/images-5c472a46-0fdd-4237-aae3-e7f119a11e32.png"
HEADSHOT_PATH="${HEADSHOT_PATH:-$HEADSHOT_PATH_DEFAULT}"

# Find a free localhost port
PORT="$(python - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)"

TMP_DIR="$(mktemp -d -t slauson_headshot.XXXXXX)"
cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [[ -f "$HEADSHOT_PATH" ]]; then
  # Serve it with a stable name
  ln -sf "$HEADSHOT_PATH" "$TMP_DIR/headshot.png" 2>/dev/null || cp "$HEADSHOT_PATH" "$TMP_DIR/headshot.png"
  python -m http.server "$PORT" --bind 127.0.0.1 --directory "$TMP_DIR" >/dev/null 2>&1 &
  SERVER_PID="$!"
  HEADSHOT_URL="http://127.0.0.1:$PORT/headshot.png"
else
  echo "Warning: HEADSHOT_PATH not found: $HEADSHOT_PATH"
  echo "Falling back to headshot_url in $PAYLOAD_FILE"
  HEADSHOT_URL=""
fi

# Mode switch:
# - Default: APPEND mode (creates a NEW slide every run)
# - EDIT_MODE=1: EDIT mode (replaces the existing slide for the given notion_page_id)
#
# Examples:
#   ./test_webhook.sh
#   EDIT_MODE=1 ./test_webhook.sh
EDIT_MODE="${EDIT_MODE:-0}"

# Build payload:
# - In APPEND mode, remove notion_page_id so the backend appends.
# - In EDIT mode, keep notion_page_id and set force_replace=true to replace.
# Also inject a slide_job_id so you can visually confirm which run generated the slide.
TMP_PAYLOAD="$(mktemp -t slauson_payload.XXXXXX.json)"
python - <<'PY' > "$TMP_PAYLOAD"
import json, uuid, os
with open("test_real_payload.json", "r") as f:
    payload = json.load(f)
edit_mode = str(os.environ.get("EDIT_MODE", "0")).strip().lower() in ("1", "true", "yes", "y", "on")
if edit_mode:
    payload["force_replace"] = True
else:
    payload.pop("notion_page_id", None)
payload.setdefault("company_data", {})
payload["company_data"]["slide_job_id"] = f"local-{'edit' if edit_mode else 'new'}-{uuid.uuid4().hex[:10]}"
headshot_url = os.environ.get("HEADSHOT_URL", "").strip()
if headshot_url:
    payload["headshot_url"] = headshot_url
print(json.dumps(payload))
PY

curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  --data-binary @"$TMP_PAYLOAD" \
  -w "\n\nHTTP Status: %{http_code}\n" \
  -v

rm -f "$TMP_PAYLOAD"

echo ""
echo "Done! Check Render logs for processing details."

