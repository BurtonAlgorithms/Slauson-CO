# Handoff Checklist - Quick Reference

Use this checklist when transferring the project to a new company.

## Pre-Handoff (Current Company)

- [ ] Document any customizations or special configurations
- [ ] Note any API rate limits or quotas
- [ ] Document any special business logic
- [ ] Clean up any test data or temporary files

## Setup for New Company

### Google Drive Setup
- [ ] Create new Google Cloud project (or use existing)
- [ ] Enable Google Drive API
- [ ] Create OAuth credentials (Desktop app)
- [ ] Download `credentials.json`
- [ ] Run `python setup_google_oauth.py`
- [ ] Verify `token.json` created
- [ ] Create Google Drive folder for slides (optional)
- [ ] Create `SlidesGen.pdf` file in Google Drive
- [ ] Note folder ID and file name

### Canva Setup
- [ ] Create Canva app at canva.dev
- [ ] Get Client ID and Client Secret
- [ ] Run `python setup_canva_oauth.py`
- [ ] Verify `canva_tokens.json` created
- [ ] (Optional) Create/select Canva template
- [ ] Note template/design IDs

### Template Files
- [ ] Obtain slide template PDF
- [ ] Place template in project or note path
- [ ] Test template loads correctly

### Environment Variables
- [ ] Create `.env` file with all required variables
- [ ] Set `GOOGLE_DRIVE_STATIC_FILE_NAME` or `GOOGLE_DRIVE_STATIC_FILE_ID`
- [ ] Set `SLIDE_TEMPLATE_PATH`
- [ ] Set Canva credentials (if using)
- [ ] Set optional API keys (remove.bg, OpenAI, Gemini, etc.)

### Testing
- [ ] Test Google Drive connection
- [ ] Test Canva connection (if using)
- [ ] Test slide generation locally
- [ ] Test webhook endpoint locally
- [ ] Verify slides upload to Google Drive
- [ ] Verify slides upload to Canva (if using)

### Deployment
- [ ] Set up Render (or hosting platform)
- [ ] Set all environment variables in Render dashboard
- [ ] Upload template file (if needed)
- [ ] Deploy application
- [ ] Test webhook on production URL
- [ ] Verify production logs

### Documentation
- [ ] Provide `HANDOFF_GUIDE.md`
- [ ] Provide `ENVIRONMENT_VARIABLES.md`
- [ ] Provide webhook API documentation
- [ ] Document any custom business logic
- [ ] Provide contact info for questions

## Post-Handoff (New Company)

- [ ] Review all documentation
- [ ] Test full workflow end-to-end
- [ ] Set up monitoring/alerts (optional)
- [ ] Train team on webhook usage
- [ ] Document any new customizations

## Critical Files to Transfer

### Must Transfer:
- ✅ Repository code (all Python files)
- ✅ `requirements.txt`
- ✅ Template PDF file
- ✅ Documentation files

### Must NOT Transfer (Security):
- ❌ `token.json` (Google Drive OAuth - recreate)
- ❌ `canva_tokens.json` (Canva OAuth - recreate)
- ❌ `credentials.json` (Google OAuth - recreate)
- ❌ `.env` file (recreate with new values)
- ❌ Any API keys or secrets

### New Company Must Create:
- 🔄 `token.json` (via `setup_google_oauth.py`)
- 🔄 `canva_tokens.json` (via `setup_canva_oauth.py`)
- 🔄 `.env` file (with their own values)
- 🔄 `credentials.json` (from Google Cloud Console)

## Quick Commands Reference

```bash
# Setup Google Drive
python setup_google_oauth.py

# Setup Canva
export CANVA_CLIENT_ID="..."
export CANVA_CLIENT_SECRET="..."
python setup_canva_oauth.py

# Test Google Drive
python -c "from google_drive_integration import GoogleDriveIntegration; GoogleDriveIntegration()"

# Test Canva
python -c "from canva_integration import CanvaIntegration; CanvaIntegration()"

# Test slide generation
python test_astranis_slide.py

# Run webhook server locally
python webhook_listener.py
```

## Environment Variables Quick Reference

### Required:
- `GOOGLE_DRIVE_STATIC_FILE_NAME` or `GOOGLE_DRIVE_STATIC_FILE_ID`
- `SLIDE_TEMPLATE_PATH`

### For Render (Google Drive):
- `GOOGLE_DRIVE_CREDENTIALS_JSON` (full JSON from token.json)

### For Render (Canva):
- `CANVA_CLIENT_ID`
- `CANVA_CLIENT_SECRET`
- `CANVA_REFRESH_TOKEN`
- `CANVA_ACCESS_TOKEN`
- `CANVA_TOKEN_REFRESHED_AT`

### Optional:
- `GOOGLE_DRIVE_FOLDER_ID`
- `CANVA_TEMPLATE_ID`
- `CANVA_STATIC_DESIGN_ID`
- `REMOVEBG_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`


