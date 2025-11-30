# How to View the Canva Slide

## The Problem

The Canva slide is generated on the Render server in a temporary directory (`/tmp/...`), which is not directly accessible. However, I've updated the webhook to return the PDF in the response!

---

## ✅ Solution: PDF is Now in Webhook Response

The webhook now returns the PDF as **base64-encoded data** in the response. You can download it easily!

---

## Method 1: Use the Test Script (Easiest)

I created a script that tests the webhook and automatically downloads the slide:

```bash
cd ~/slauson-automation
./test_and_download.sh
```

This will:
1. ✅ Send test data to webhook
2. ✅ Save response to `webhook_response.json`
3. ✅ Automatically extract and save the PDF

The slide will be saved as: `TechFlow_Solutions_slide.pdf` (or similar)

---

## Method 2: Manual Download

### Step 1: Test the Webhook

```bash
cd ~/slauson-automation
curl -X POST https://sauson-automation-3.onrender.com/webhook/onboarding \
  -H "Content-Type: application/json" \
  -d @test_real_payload.json \
  -o response.json
```

### Step 2: Extract the PDF

```bash
python3 download_slide.py response.json
```

This will save the PDF file locally.

---

## Method 3: From Zapier Response

When Zapier triggers the webhook:

1. **In Zapier:**
   - Add a "Code by Zapier" step after the webhook
   - Or use "Formatter" to extract the PDF

2. **Or check the webhook response:**
   - The response includes `pdf_base64` field
   - Decode it to get the PDF

---

## Method 4: View in Browser (Future Enhancement)

I can add a download endpoint to Render:

```
https://sauson-automation-3.onrender.com/download/slide/<company_name>
```

Would you like me to add this?

---

## Current Response Format

The webhook now returns:

```json
{
  "success": true,
  "canva_slide_path": "/tmp/.../slide.pdf",
  "pdf_base64": "JVBERi0xLjQKJeLjz9MK...",  // ← PDF as base64
  "pdf_filename": "TechFlow_Solutions_slide.pdf",  // ← Filename
  ...
}
```

---

## Quick Test

Run this to test and download:

```bash
cd ~/slauson-automation
./test_and_download.sh
```

Then open the PDF file that gets created!

---

## Troubleshooting

### No PDF in Response?

1. Check Render logs for errors
2. Verify Canva integration is working
3. Check if `pdf_base64` is in the response JSON

### PDF Won't Open?

1. Make sure it's a valid PDF (check file size > 0)
2. Try opening with different PDF viewer
3. Check if base64 decoding worked correctly

---

**Try the test script now: `./test_and_download.sh`** 🚀

