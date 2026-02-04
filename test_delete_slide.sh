#!/bin/bash
set -euo pipefail

# Delete a slide from the Google Drive master PDF using Slide Job ID.
#
# Notes:
# - `delete_slide` mode still goes through the same payload validation, so we include
#   the required company fields (name/description/address).
# - `notion_page_id` is OPTIONAL for deletion as long as the Slide Job ID exists in
#   `slide_job_index.json` on Drive. If you include it, deletion is faster/more explicit.
#
# Usage:
#   ./test_delete_slide.sh
#
# Optional overrides:
#   WEBHOOK_URL="http://127.0.0.1:5001/webhook/onboarding" ./test_delete_slide.sh
#   SLIDE_JOB_ID="a1b2c3d4-20250131143022-A7F9K2B1" ./test_delete_slide.sh
#   NOTION_PAGE_ID="..." ./test_delete_slide.sh

WEBHOOK_URL="${WEBHOOK_URL:-http://127.0.0.1:5001/webhook/onboarding}"

# Optional
NOTION_PAGE_ID="${NOTION_PAGE_ID:-}"

# Slide Job ID:
# - If provided, we delete by job id (no notion_page_id required).
# - If NOT provided, we auto-resolve from Google Drive `slide_job_index.json`.
SLIDE_JOB_ID="${SLIDE_JOB_ID:-}"

if [ -z "$SLIDE_JOB_ID" ]; then
  echo "SLIDE_JOB_ID not set; resolving from Google Drive slide_job_index.json..."
  SLIDE_JOB_ID="$(python - "$NOTION_PAGE_ID" <<'PY'
import contextlib
import json
import sys

def die(msg: str):
  print(msg, file=sys.stderr)
  raise SystemExit(2)

notion_page_id = (sys.argv[1] if len(sys.argv) > 1 else "").strip() or None

# google_drive_integration prints some messages to stdout on import/init in this repo.
# Redirect those to stderr so stdout contains ONLY the resolved slide_job_id.
with contextlib.redirect_stdout(sys.stderr):
  from google_drive_integration import GoogleDriveIntegration

  drive = GoogleDriveIntegration()
  folder_id = drive.find_folder_id_by_name("Slauson Deck (Portco Slides)")
  file_id = drive.find_file_id_by_name(
    "slide_job_index.json",
    parent_folder_id=folder_id,
    mime_type="application/json",
  )
  raw = drive.download_file(file_id)

data = json.loads(raw.decode("utf-8"))
entries = data.get("entries", {}) if isinstance(data, dict) else {}

if notion_page_id:
  info = entries.get(notion_page_id)
  if not isinstance(info, dict) or not info.get("slide_job_id"):
    die(f"No slide_job_id found in index for notion_page_id={notion_page_id}")
  print(info["slide_job_id"])
else:
  # If only one entry exists, default to it (nice for local testing).
  jobs = []
  for pid, info in entries.items():
    if isinstance(info, dict) and info.get("slide_job_id"):
      jobs.append((pid, info["slide_job_id"]))
  if len(jobs) == 1:
    print(jobs[0][1])
  else:
    die(
      "SLIDE_JOB_ID not provided and index has multiple entries. "
      "Set SLIDE_JOB_ID=... (or set NOTION_PAGE_ID=... to resolve the right one)."
    )
PY
)"
  echo "Resolved slide_job_id: $SLIDE_JOB_ID"
  echo ""
fi

echo "Deleting slide via webhook..."
echo "  url:         $WEBHOOK_URL"
echo "  slide_job_id: $SLIDE_JOB_ID"
if [ -n "$NOTION_PAGE_ID" ]; then
  echo "  notion_page_id: $NOTION_PAGE_ID"
fi
echo ""

if [ -n "$NOTION_PAGE_ID" ]; then
  curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{
      \"notion_page_id\": \"${NOTION_PAGE_ID}\",
      \"company_data\": {
        \"name\": \"TechFlow Solutions\",
        \"description\": \"delete test\",
        \"address\": \"123 Innovation Drive, San Francisco, CA 94105\",
        \"delete_slide\": true,
        \"slide_job_id\": \"${SLIDE_JOB_ID}\"
      }
    }" \
    -w "\n\nHTTP Status: %{http_code}\n"
else
  curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{
      \"company_data\": {
        \"name\": \"TechFlow Solutions\",
        \"description\": \"delete test\",
        \"address\": \"123 Innovation Drive, San Francisco, CA 94105\",
        \"delete_slide\": true,
        \"slide_job_id\": \"${SLIDE_JOB_ID}\"
      }
    }" \
    -w "\n\nHTTP Status: %{http_code}\n"
fi

