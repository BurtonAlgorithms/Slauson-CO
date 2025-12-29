# Complete Handoff Guide - Slauson Automation

This document provides complete instructions for transferring the Slauson automation system to a new company, including all environment variables and setup steps.

---

## Overview

This system automatically generates portfolio slides from webhook data and uploads them to:
- **Google Drive** (as a merged PDF - `SlidesGen.pdf`)
- **Canva** (as a multi-page design)
- **DocSend** (via Google Drive sync)

---

## Step 1: Initial Setup

### 1.1 Clone Repository

```bash
git clone <repository-url>
cd slauson-automation
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Step 2: Google Drive Setup

### 2.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Google Drive API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"

### 2.2 Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure OAuth consent screen (if first time):
   - User Type: **External**
   - App name: "Slauson Automation"
   - User support email: `your-email@company.com`
   - Developer contact: `your-email@company.com`
   - Click "Save and Continue"
   - Scopes: Add `https://www.googleapis.com/auth/drive.file`
   - Click "Save and Continue"
   - Test users: Add the Google account email that will use this
   - Click "Save and Continue"

4. Create OAuth Client ID:
   - Application type: **Desktop app**
   - Name: "Slauson Automation Desktop"
   - Click "Create"
   - **Download the JSON file** → Save as `credentials.json` in project root

### 2.3 Run OAuth Setup

```bash
python setup_google_oauth.py
```

This will:
- Open browser for Google sign-in
- Ask for Drive permissions
- Save tokens to `token.json`

### 2.4 Create Google Drive Folder (Optional)

1. Create a folder in Google Drive for slides
2. Right-click folder > "Get link" > Copy link
3. Extract folder ID from URL: `https://drive.google.com/drive/folders/FOLDER_ID`
4. Save folder ID for later

### 2.5 Create Static PDF File

1. Create a PDF file named `SlidesGen.pdf` in Google Drive
2. This file will receive all merged slides
3. Note the exact filename (case-sensitive)

---

## Step 3: Canva Setup

### 3.1 Create Canva App

1. Go to [Canva Developers](https://www.canva.dev/)
2. Sign in with your Canva account
3. Click "Create an app"
4. Fill in:
   - App name: "Slauson Automation"
   - Description: "Automated slide generation"
   - Redirect URI: `http://localhost:8080/callback`
5. **Save your Client ID and Client Secret**

### 3.2 Run Canva OAuth Setup

```bash
export CANVA_CLIENT_ID="your_client_id_here"
export CANVA_CLIENT_SECRET="your_client_secret_here"
python setup_canva_oauth.py
```

Or add to `.env` file:
```bash
CANVA_CLIENT_ID=your_client_id_here
CANVA_CLIENT_SECRET=your_client_secret_here
```

Then run:
```bash
python setup_canva_oauth.py
```

This will:
- Open browser for Canva sign-in
- Ask for permissions
- Save tokens to `canva_tokens.json`

### 3.3 (Optional) Create Canva Template

If using Canva templates:
1. Go to [Canva](https://www.canva.com/)
2. Create or select a template design
3. Copy design ID from URL: `https://www.canva.com/design/DESIGN_ID/edit`
4. Save design ID for later

---

## Step 4: Prepare Template Files

### 4.1 Slide Template PDF

1. Obtain your slide template PDF
2. Place it in project root or note the full path
3. Example: `/path/to/SLAUSON&CO.Template.pdf`

---

## Step 5: Environment Variables - Complete List

### 5.1 Local Development (.env file)

Create a `.env` file in the project root:

```bash
# ============================================
# REQUIRED - Google Drive
# ============================================
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_DRIVE_STATIC_FILE_NAME=SlidesGen.pdf
# OR use file ID directly:
# GOOGLE_DRIVE_STATIC_FILE_ID=your_file_id_here

# ============================================
# REQUIRED - Slide Template
# ============================================
SLIDE_TEMPLATE_PATH=/full/path/to/your/template.pdf

# ============================================
# REQUIRED - Canva (if using Canva)
# ============================================
CANVA_CLIENT_ID=your_canva_client_id
CANVA_CLIENT_SECRET=your_canva_client_secret
CANVA_TEMPLATE_ID=your_template_id_here  # Optional
CANVA_STATIC_DESIGN_ID=your_design_id_here  # Optional, for reference

# ============================================
# OPTIONAL - Background Removal APIs
# ============================================
REMOVEBG_API_KEY=your_removebg_api_key
OPENAI_API_KEY=your_openai_api_key

# ============================================
# OPTIONAL - AI/LLM
# ============================================
GEMINI_API_KEY=your_gemini_api_key

# ============================================
# OPTIONAL - Notion Integration
# ============================================
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
NOTION_TEMPLATE_PAGE_ID=your_notion_template_page_id

# ============================================
# OPTIONAL - DocSend
# ============================================
DOCSEND_API_KEY=your_docsend_api_key
DOCSEND_INDIVIDUAL_DECK_ID=your_individual_deck_id
DOCSEND_MASTER_DECK_ID=your_master_deck_id
```

### 5.2 Render Deployment - Environment Variables

Go to Render Dashboard > Your Service > Environment and set these:

#### Required Variables:

```bash
# Google Drive - Static File
GOOGLE_DRIVE_STATIC_FILE_NAME=SlidesGen.pdf
# OR
GOOGLE_DRIVE_STATIC_FILE_ID=your_file_id_here

# Slide Template
SLIDE_TEMPLATE_PATH=/app/SLAUSON&CO.Template.pdf
# (Adjust path based on where you place the template in Render)

# Google Drive Folder (Optional)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
```

#### Google Drive OAuth (Required for Render):

**After running `python setup_google_oauth.py`, copy the entire contents of `token.json` and set as:**

```bash
GOOGLE_DRIVE_CREDENTIALS_JSON='{"token":"ya29.YOUR_ACCESS_TOKEN_HERE","refresh_token":"1//04YOUR_REFRESH_TOKEN_HERE","token_uri":"https://oauth2.googleapis.com/token","client_id":"YOUR_CLIENT_ID.apps.googleusercontent.com","client_secret":"GOCSPX-YOUR_CLIENT_SECRET","scopes":["https://www.googleapis.com/auth/drive.file"],"universe_domain":"googleapis.com","account":"","expiry":"2025-12-28T23:58:34.474431Z"}'
```

**How to get this value:**
1. Run `python setup_google_oauth.py` locally (with new company's Google account)
2. Open `token.json` file
3. Copy the **entire JSON content** (all on one line)
4. Paste into Render's `GOOGLE_DRIVE_CREDENTIALS_JSON` environment variable
5. Render will handle quote escaping automatically

#### Canva OAuth (Required if using Canva):

```bash
CANVA_CLIENT_ID=OC-AZrV8Py...
CANVA_CLIENT_SECRET=your_client_secret
CANVA_REFRESH_TOKEN=eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2Iiwia2lkIjoiZmQ1YmU1MTMtZjAzNy00M2NkLTg3OGEtNjQ1OWJmMGEwNzA4IiwiY3R5IjoiSldUIiwianRpIjoiRUY1aVpTQzAxZGpNMVU1V0V2bWJVdyIsImNsaWVudF9pZCI6Ik9DLUFaclY4UHl2VVdBZSIsImF0X2xlYXN0IjoxMjA5NjAwMDAwfQ.R_ibVIStCAcGHU9nBH45x4JIgwRe5KBiZeVbZHzduEQh6kIew5ILMmKhVo5wbj4kN6Z5yiafj1ANg4Sd00OIVIX5HyKjM8TDV8WPNZf_RhtvQI874Qs31BMY4B61B276XyuFZQNt3ymJHIbr1kP4PI3cDvhfBS_HGhFPvt7J7Iar3orqlMQ1rhjDXRWGp4XP2sMfmxWGo0N0pTx9rT1dtiNQldiYyoxEAulBWU1ybphaFJuniRJ1n3owHs3ybyS5BPS5Y9pq4KZptSMH-cZSJkt5WmuKTEYiEUGCoeefDKbeFDreG7YKuGZ5AXl9ddEhGHatAMYtmfPKtuC0TEc2hQ.q6syYaEXZMZKQym1ym125w.ksnK-kUKQpOq9V1A3jkv2tk_bsl5fbbBluFMqEzH02Ivt5XstwfG_ZqwVIoxuvSLKN0whxGW4OHojvYtvcA83TFVl8lvnEvvA_eDxuiNY9Xcw9fQhvLjZh2J3BbkMhRgU9TgY8ILmZziGQool7ywkhgKoVkmA0C4XjKiIyXmmmisPTzSoRpIuBVSjt-ewtMPgWJYeJSmw9s5ehdoSijRkaXVeBYKXS1DIVptaFAl3WYs3RlkqZP0IqV9wu25eJ93gFBx3VMvNs2jGbBKosVW64jk-eQhCWUciL_M60W8CTO4IPP0bC1DVFh7Koj4V7BiM_xXoR0jokFNMwuM6_aJDbj82YQJpWs7urm46v9IZXYCa-ZDxbMHraQY3WSVpBzRRI3p9ZiAqlTkuDxa7DiznLFShjt-gT6LLpP7M_1rXlE7I6H_EM2cohoVbUELRBD-QHnwXDFaTx5GIBrP_7Lu1qweAX0d9-Jcm7ZpTLnKT9JpVitSg5I-WmQxX2LYSfPpQquf-7gsZZIMk1nDDi_IVbm202stKlDNP6hL_tbBThrd5boYoP8jDVDMLiox8vcGJxHSY0P9jmKHnR7FKBZ7O5yPqFVmfUjr80uL_MRuuKMxXYFY3qzWvRC9TsLCGwEjB1G7gDdeuugS2Uafx7kJw6M-mfANkU5PURr88pUGSiZxn-X9ZPKct2OULPJlE7bNPIWvuPJC1yEOeIGh4Bmxvb9qat9PfH_F49FNbxkbT8f0IBEOUciSdEjJXoOL4KtDasyhc7Gpxyu90HuMnCJ9LjxyEnDKY8JcAZgF6UIIF_aOLM4_2aGUFrKWsPwby2j2CKvNHwLwWWDkynozHNyOUZRQQLkwCpxb-v3UxdSuoJTpu34eGB2tHzl-yGVcmqU3qZzVpRrvnQ53vEBskcZkwT7GkxWIkTt8SKjsedKyw8cknK-btqycWUAQsRZpkOEAShoSlbBVo37Dknacf-maa6mjU98t8a2unnwwpCN3dy9u_fzvbtI-X1hCYDJLNO5zRWzKGTtCeNSBcLYHsFb0rcRT0yF0Y9HOoaBGu_H9FYlR-yKczOwUG0xjhkETW23Iy8Q6Td-lqC0sBmJid5dhL83gARB0LbCvL07bhWTQ3vE2F_-NJXGZtF25TstDy1dwmemet43Cw1zc1q0j8iQcCgnMW-Td-P-VavwPyjtCD4t86-55QaqqS539O-trJDjIFpy8t8VFaHlsNktBjZuRehi8V7BAJ2PuV07MUZyLnv0lnXmij0OwESovm-O6p8PxL09SjY9TH4gza68q-vMVLZyjK4CElIsew2nH9d3i3Hl0MUV8dw8Y186DsBASd-bMg7ZqgGRWePSscQ86Iqn_bSzUEJY65New7G-KRAEJCxyM4yP2youwiWuhvcKrAPDflZcVEtckWJQ2Kg-sODszWPQq1eR8tANq575NMZ8r9G9dpxZG2ZxfSZ53Rl3-c9fZ.sQV-h9m72HkKCOc3Hdk5Og
CANVA_ACCESS_TOKEN=eyJraWQiOiIyMzY4ZjRhYi00N2ZiLTQwN2MtYjM5Ni00NzgxODcwMjZkN2UiLCJhbGciOiJSUzI1NiJ9.eyJqdGkiOiJUZTM4cWZkR0NhOEtHZ2NwYkVyRHhnIiwiY2xpZW50X2lkIjoiT0MtQVpyVjhQeXZVV0FlIiwiYXVkIjoiaHR0cHM6Ly93d3cuY2FudmEuY29tIiwiaWF0IjoxNzY2OTYyNzM2LCJuYmYiOjE3NjY5NjI3MzYsImV4cCI6MTc2Njk3NzEzNiwic3ViIjoib1VYdUtsNUNPRXdJWXJGY0loTGxlOCIsImJyYW5kIjoib0JYdUtEYkFGV2ZQT0xVc1F0d29PbyIsIm9yZ2FuaXphdGlvbiI6bnVsbCwic2NvcGVzIjpbImRlc2lnbjpjb250ZW50OnJlYWQiLCJkZXNpZ246Y29udGVudDp3cml0ZSIsImRlc2lnbjptZXRhOnJlYWQiLCJicmFuZHRlbXBsYXRlOm1ldGE6cmVhZCIsImJyYW5kdGVtcGxhdGU6Y29udGVudDpyZWFkIiwiYXNzZXQ6cmVhZCIsImFzc2V0OndyaXRlIl0sImJ1bmRsZXMiOlsiUFJPMiJdLCJjb2RlX2lkIjoiaTFuVFJsaUtmREliN01tRTlOVzd4ZyIsImFjdF9hcyI6InUiLCJhY3giOiJrNnFxTW5xTExOTEEySk5JUVpnbVY4cURDYzhPSkdEd3A1YU1BX2VGV2hmMTRpQk13dmpUa3pGRDhrS3FJMTkyX1BSQTIzLUNtNEhPOTVwSEZiczR0X2pjRGNMRVVqR3pXenFsR00yR1UwQklsZHZzdm5XLWpBakVBVEJaa0JKTkhleTdKdyJ9.HSPtHGtIoo5fXsvvOl-r4RIVbSNU7oondU4-afcSjWYEkaHkpJVA7F8SgqdsbID7PqMPcL1U2sO1eWs9ZJT8KcZHPRhAasfMIHDZ3NBpgCrtD1kt90C6nvVRo1B7XtJYjSg5FcmyUmTxzlGUS82k2baybbNzXdI_GyBQ5IHKktBaCQZ9wvJ8mvaS0M4n4KAE9U55qs9oaokDaFUy4sV0g3gpsp4ycBA8rZRXxRlQ_iUFFfwKJq_GUK2VzDlTmlRtmpgUIc7ZbBK6ZCRKqU-5I15slSGK-DPU0WZfKHvbj5QMG3WxCxo_qHvJzsXJ-9swXw_gMmkOarxeWWGYG5GqGw
CANVA_TOKEN_REFRESHED_AT=1766962736.598428
```

**How to get Canva token values:**
1. Run `python setup_canva_oauth.py` locally (with new company's Canva account)
2. Open `canva_tokens.json` file
3. Copy each value:
   - `refresh_token` → `CANVA_REFRESH_TOKEN` (long encrypted string starting with `eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2Iiwi...`)
   - `access_token` → `CANVA_ACCESS_TOKEN` (JWT token starting with `eyJraWQiOiIyMzY4ZjRhYi00N2ZiLTQwN2MtYjM5Ni00NzgxODcwMjZkN2UiLCJhbGciOiJSUzI1NiJ9...`)
   - `token_refreshed_at` → `CANVA_TOKEN_REFRESHED_AT` (Unix timestamp like `1766962736.598428`)

**Example format (from your setup):**
- `CANVA_REFRESH_TOKEN`: Starts with `eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2Iiwi...` (very long string)
- `CANVA_ACCESS_TOKEN`: Starts with `eyJraWQiOiIyMzY4ZjRhYi00N2ZiLTQwN2MtYjM5Ni00NzgxODcwMjZkN2UiLCJhbGciOiJSUzI1NiJ9...` (JWT format)
- `CANVA_TOKEN_REFRESHED_AT`: Number like `1766962736.598428`

#### Optional Variables (for Render):

```bash
# Background Removal
REMOVEBG_API_KEY=your_removebg_key
OPENAI_API_KEY=your_openai_key

# AI/LLM
GEMINI_API_KEY=your_gemini_key

# Notion
NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id

# DocSend
DOCSEND_API_KEY=your_docsend_key
```

---

## Step 6: Testing

### 6.1 Test Locally

```bash
# Test Google Drive
python -c "from google_drive_integration import GoogleDriveIntegration; GoogleDriveIntegration()"

# Test Canva
python -c "from canva_integration import CanvaIntegration; CanvaIntegration()"

# Test slide generation
python test_astranis_slide.py
```

### 6.2 Test Webhook

```bash
curl -X POST http://localhost:5001/webhook/onboarding \
  -H "Content-Type: application/json" \
  -d '{
    "company_data": {
      "name": "Test Company",
      "description": "Test description",
      "address": "San Francisco, CA",
      "location": "San Francisco, CA",
      "investment_date": "2024-01-15",
      "investment_round": "SERIES A",
      "founders": ["Founder 1"],
      "co_investors": ["Investor 1"],
      "background": "Test background"
    },
    "headshot": "base64_encoded_image_or_url",
    "logo": "base64_encoded_image_or_url"
  }'
```

---

## Step 7: Deploy to Render

### 7.1 Render Service Setup

1. **Service Type**: Web Service
2. **Build Command**: `pip install -r requirements.txt`
3. **Start Command**: `python webhook_listener.py`
4. **Environment**: Python 3

### 7.2 Set All Environment Variables

Copy all variables from **Step 5.2** above into Render dashboard.

### 7.3 Upload Template File

1. Option A: Include template in repository (if not too large)
2. Option B: Upload via Render file system
3. Option C: Store in a cloud bucket and download on startup

### 7.4 Deploy

1. Connect repository
2. Set environment variables
3. Deploy
4. Check logs for errors

---

## Step 8: Verification Checklist

After deployment, verify:

- [ ] Google Drive connection works
- [ ] Canva connection works (if using)
- [ ] Webhook endpoint responds
- [ ] Test webhook creates slide
- [ ] Slide appears in Google Drive (`SlidesGen.pdf`)
- [ ] Slide appears in Canva (if using)
- [ ] No authentication errors in logs

---

## Important Notes

### Files That Must Be Created (Not Transferred)

The new company must create these locally:

1. **`token.json`** - Created by `python setup_google_oauth.py`
2. **`canva_tokens.json`** - Created by `python setup_canva_oauth.py`
3. **`credentials.json`** - Downloaded from Google Cloud Console
4. **`.env`** - Created manually with their values

### Files That Must NOT Be Transferred

❌ **DO NOT** transfer these files (security risk):
- `token.json`
- `canva_tokens.json`
- `credentials.json`
- `.env`

These contain OAuth tokens and API keys specific to each company.

### Token Refresh

- **Google Drive tokens**: Auto-refresh when expired
- **Canva tokens**: Auto-refresh every 4 hours (if `CANVA_REFRESH_TOKEN` is set in Render)
- If tokens get revoked, re-run the setup scripts

---

## Troubleshooting

### "Token lineage has been revoked"
- **Solution**: Re-run `python setup_canva_oauth.py` and update tokens in Render

### "OAuth credentials not configured"
- **Solution**: Run `python setup_google_oauth.py` or set `GOOGLE_DRIVE_CREDENTIALS_JSON` in Render

### "SLIDE_TEMPLATE_PATH not set"
- **Solution**: Set `SLIDE_TEMPLATE_PATH` to full path of template PDF

### "Google Drive file not found"
- **Solution**: Check `GOOGLE_DRIVE_STATIC_FILE_NAME` matches exactly (case-sensitive)

### Rate Limiting (429)
- **Solution**: Wait a few minutes, then retry

---

## Support Resources

- **Handoff Guide**: `HANDOFF_GUIDE.md` - Detailed step-by-step instructions
- **Environment Variables**: `ENVIRONMENT_VARIABLES.md` - Complete reference
- **Canva Fix**: `RENDER_CANVA_FIX.md` - Troubleshooting Canva auth
- **Checklist**: `HANDOFF_CHECKLIST.md` - Quick reference checklist

---

## Quick Command Reference

```bash
# Setup Google Drive
python setup_google_oauth.py

# Setup Canva
export CANVA_CLIENT_ID="..."
export CANVA_CLIENT_SECRET="..."
python setup_canva_oauth.py

# Test connections
python -c "from google_drive_integration import GoogleDriveIntegration; GoogleDriveIntegration()"
python -c "from canva_integration import CanvaIntegration; CanvaIntegration()"

# Run webhook server
python webhook_listener.py
```

---

## Next Steps After Handoff

1. Test full workflow with real data
2. Set up monitoring/alerts (optional)
3. Train team on webhook API usage
4. Document any customizations
5. Set up backup/recovery procedures (optional)

