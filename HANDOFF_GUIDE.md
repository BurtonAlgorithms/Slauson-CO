# Project Handoff Guide - Slauson Automation

This guide walks through transferring the Slauson automation system to a new company, including setting up new Google Drive and Canva accounts.

## Prerequisites

- Access to the new company's Google Drive account
- Access to the new company's Canva account (or ability to create one)
- Python 3.8+ installed
- Git installed

---

## Step 1: Clone/Download the Repository

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd slauson-automation
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Step 2: Set Up Google Drive OAuth (New Company)

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
3. If prompted, configure OAuth consent screen:
   - User Type: **External** (unless you have Google Workspace)
   - App name: "Slauson Automation" (or your company name)
   - User support email: Your email
   - Developer contact: Your email
   - Click "Save and Continue"
   - Scopes: Add `https://www.googleapis.com/auth/drive.file`
   - Click "Save and Continue"
   - Test users: Add the Google account email that will use this
   - Click "Save and Continue"

4. Create OAuth Client ID:
   - Application type: **Desktop app**
   - Name: "Slauson Automation Desktop"
   - Click "Create"
   - **Download the JSON file** (save as `credentials.json` in project root)

### 2.3 Run OAuth Setup Script

1. Place `credentials.json` in the project root directory
2. Run the setup script:
   ```bash
   python setup_google_oauth.py
   ```
3. This will:
   - Open a browser window
   - Ask you to sign in with the **new company's Google account**
   - Ask for permissions to access Google Drive
   - Save tokens to `token.json`

4. Verify `token.json` was created:
   ```bash
   ls -la token.json
   ```

### 2.4 Test Google Drive Access

```bash
python -c "from google_drive_integration import GoogleDriveIntegration; drive = GoogleDriveIntegration(); print('✓ Google Drive connected!')"
```

---

## Step 3: Set Up Canva OAuth (New Company)

### 3.1 Create Canva App

1. Go to [Canva Developers](https://www.canva.dev/)
2. Sign in with the **new company's Canva account**
3. Click "Create an app"
4. Fill in app details:
   - App name: "Slauson Automation" (or your company name)
   - Description: "Automated slide generation"
  - Redirect URI: `https://oauth.example.com/canva/callback`
5. Note your **Client ID** and **Client Secret**

### 3.2 Run Canva OAuth Setup

1. Set environment variables:
   ```bash
   export CANVA_CLIENT_ID="your_client_id_here"
   export CANVA_CLIENT_SECRET="your_client_secret_here"
   ```

2. Or add to `.env` file:
   ```bash
   CANVA_CLIENT_ID=your_client_id_here
   CANVA_CLIENT_SECRET=your_client_secret_here
   ```

3. Run the setup script:
   ```bash
   python setup_canva_oauth.py
   ```

4. This will:
   - Open a browser window
   - Ask you to sign in with the **new company's Canva account**
   - Ask for permissions
   - Save tokens to `canva_tokens.json`

5. Verify `canva_tokens.json` was created:
   ```bash
   ls -la canva_tokens.json
   ```

### 3.3 (Optional) Create Canva Template

If you want to use a Canva template:

1. Go to [Canva](https://www.canva.com/)
2. Create or select a template design
3. Copy the design ID from the URL:
   - URL format: `https://www.canva.com/design/DESIGN_ID/edit`
   - Example: `DAG8qHDm-w0` is the design ID
4. Save this for later

---

## Step 4: Create/Upload Required Files

### 4.1 Slide Template PDF

1. Create or obtain your slide template PDF
2. Place it in the project root or a known location
3. Note the full path (e.g., `/path/to/SLAUSON&CO.Template.pdf`)

### 4.2 Google Drive Folder (Optional)

1. Create a folder in Google Drive for slides
2. Right-click the folder > "Get link" > "Copy link"
3. Extract the folder ID from the URL:
   - URL format: `https://drive.google.com/drive/folders/FOLDER_ID`
   - Example: `1aBcD3EfGhIjKlMnOpQrStUvWxYz` is the folder ID

### 4.3 Google Drive Static PDF (For DocSend)

1. Create a PDF file in Google Drive (e.g., `SlidesGen.pdf`)
2. This will be the file that all slides are appended to
3. Note the filename (e.g., `"SlidesGen.pdf"`)

---

## Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Google Drive
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_DRIVE_STATIC_FILE_NAME=SlidesGen.pdf
# OR use file ID directly:
# GOOGLE_DRIVE_STATIC_FILE_ID=your_file_id_here

# Slide Template (Required)
SLIDE_TEMPLATE_PATH=/full/path/to/your/template.pdf

# Canva (Optional - only if using Canva templates)
CANVA_CLIENT_ID=your_canva_client_id
CANVA_CLIENT_SECRET=your_canva_client_secret
CANVA_TEMPLATE_ID=your_template_id_here  # Optional
CANVA_STATIC_DESIGN_ID=your_design_id_here  # Optional, for reference

# Background Removal APIs (Optional)
REMOVEBG_API_KEY=your_removebg_key
OPENAI_API_KEY=your_openai_key

# AI/LLM (Optional)
GEMINI_API_KEY=your_gemini_key

# Notion Integration (Optional)
NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id
NOTION_TEMPLATE_PAGE_ID=your_template_page_id

# DocSend (Optional)
DOCSEND_API_KEY=your_docsend_key
DOCSEND_INDIVIDUAL_DECK_ID=your_individual_deck_id
DOCSEND_MASTER_DECK_ID=your_master_deck_id
```

---

## Step 6: Test the Setup

### 6.1 Test Google Drive

```bash
python -c "
from google_drive_integration import GoogleDriveIntegration
drive = GoogleDriveIntegration()
print('✓ Google Drive connected!')
"
```

### 6.2 Test Canva

```bash
python -c "
from canva_integration import CanvaIntegration
canva = CanvaIntegration()
print('✓ Canva connected!')
"
```

### 6.3 Test Slide Generation

```bash
python test_astranis_slide.py
```

This should:
- Generate a test slide
- Upload to Google Drive
- (If Canva is configured) Upload to Canva

---

## Step 7: Deploy to Render (or Your Hosting Platform)

### 7.1 Set Environment Variables in Render

Go to your Render dashboard > Environment Variables and set:

#### Required:
```bash
GOOGLE_DRIVE_STATIC_FILE_NAME=SlidesGen.pdf
SLIDE_TEMPLATE_PATH=/app/SLAUSON&CO.Template.pdf  # Or wherever you place it
```

#### Google Drive OAuth (Required):
```bash
GOOGLE_DRIVE_CREDENTIALS_JSON='{"token":"...","refresh_token":"...","token_uri":"https://oauth2.googleapis.com/token","client_id":"...","client_secret":"...","scopes":["https://www.googleapis.com/auth/drive.file"],"universe_domain":"googleapis.com","account":"","expiry":"..."}'
```

**To get this value:**
1. Copy the entire contents of `token.json` (from Step 2.3)
2. Paste as a single-line JSON string in Render

#### Canva OAuth (If using Canva):
```bash
CANVA_CLIENT_ID=your_client_id
CANVA_CLIENT_SECRET=your_client_secret
CANVA_REFRESH_TOKEN=your_refresh_token_from_canva_tokens.json
CANVA_ACCESS_TOKEN=your_access_token_from_canva_tokens.json
CANVA_TOKEN_REFRESHED_AT=timestamp_from_canva_tokens.json
```

**To get Canva tokens:**
1. Copy values from `canva_tokens.json` (from Step 3.2)
2. Set them in Render

#### Optional APIs:
```bash
REMOVEBG_API_KEY=your_key
OPENAI_API_KEY=your_key
GEMINI_API_KEY=your_key
NOTION_API_KEY=your_key
NOTION_DATABASE_ID=your_id
```

### 7.2 Upload Template File

1. In Render, go to your service settings
2. Upload the template PDF file, or
3. Include it in your repository (if it's not too large)

### 7.3 Deploy

1. Connect your repository to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python webhook_listener.py`
4. Deploy!

---

## Step 8: Verify Everything Works

### 8.1 Test Webhook

Send a test webhook request:

```bash
curl -X POST https://your-render-url.onrender.com/webhook/onboarding \
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

### 8.2 Check Results

1. **Google Drive**: Check that the slide was uploaded/appended to `SlidesGen.pdf`
2. **Canva**: Check that a new design was created (if Canva is configured)
3. **Logs**: Check Render logs for any errors

---

## Step 9: Security Checklist

- [ ] `.env` file is in `.gitignore` (should already be)
- [ ] `token.json` is in `.gitignore` (should already be)
- [ ] `canva_tokens.json` is in `.gitignore` (should already be)
- [ ] `credentials.json` is in `.gitignore` (should already be)
- [ ] All sensitive values are set as environment variables in Render
- [ ] No API keys or tokens are committed to the repository
- [ ] OAuth redirect URIs are configured correctly

---

## Step 10: Documentation for New Company

Provide the new company with:

1. **This handoff guide**
2. **Environment Variables Reference** (`ENVIRONMENT_VARIABLES.md`)
3. **Webhook API Documentation** (how to send requests)
4. **Troubleshooting Guide** (common issues and solutions)

---

## Troubleshooting

### Google Drive Issues

**Error: "OAuth credentials not configured"**
- Make sure `token.json` exists (local) or `GOOGLE_DRIVE_CREDENTIALS_JSON` is set (Render)
- Re-run `python setup_google_oauth.py`

**Error: "Token expired"**
- Tokens auto-refresh, but if it fails, re-run setup

### Canva Issues

**Error: "Invalid access token"**
- Re-run `python setup_canva_oauth.py`
- Or update `CANVA_REFRESH_TOKEN` in Render

**Error: "Template not found"**
- Check `CANVA_TEMPLATE_ID` is correct
- Or remove it if not using Canva templates

### File Not Found Issues

**Error: "SLIDE_TEMPLATE_PATH not set"**
- Set `SLIDE_TEMPLATE_PATH` to the full path of your template PDF
- Make sure the file exists at that path

**Error: "Google Drive file not found"**
- Check `GOOGLE_DRIVE_STATIC_FILE_NAME` matches exactly (case-sensitive)
- Or use `GOOGLE_DRIVE_STATIC_FILE_ID` with the exact file ID

---

## Quick Reference: Key Files

- `token.json` - Google Drive OAuth tokens (local only, not in git)
- `canva_tokens.json` - Canva OAuth tokens (local only, not in git)
- `credentials.json` - Google OAuth credentials (local only, not in git)
- `.env` - Environment variables (local only, not in git)
- `webhook_listener.py` - Main webhook handler
- `canva_integration.py` - Canva API integration
- `google_drive_integration.py` - Google Drive API integration
- `html_slide_generator.py` - Slide generation logic

---

## Support

If you encounter issues:
1. Check the logs (Render dashboard or local terminal)
2. Verify all environment variables are set correctly
3. Test each component individually (Google Drive, Canva, etc.)
4. Review the troubleshooting section above

---

## Next Steps After Handoff

1. **Test the full workflow** with a real webhook
2. **Set up monitoring** (if needed)
3. **Document any customizations** made for the new company
4. **Train the team** on how to use the webhook API
5. **Set up alerts** for errors (optional)


