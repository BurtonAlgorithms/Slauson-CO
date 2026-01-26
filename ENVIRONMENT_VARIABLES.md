# Environment Variables Reference

This document lists all environment variables needed for the Slauson automation system.

## Required Variables

### Google Drive (Required)
- `GOOGLE_DRIVE_CREDENTIALS_JSON` - JSON string of OAuth credentials (or use `token.json` file)
- `GOOGLE_DRIVE_FOLDER_ID` - (Optional) Folder ID where PDFs should be uploaded

### Slide Generation (Required)
- `SLIDE_TEMPLATE_PATH` - Path to your slide template PDF (e.g., `/path/to/SLAUSON&CO.Template.pdf`)

## Optional but Recommended

### Google Drive Static File (For DocSend)
- `GOOGLE_DRIVE_STATIC_FILE_NAME` - Name of the PDF file to append to (e.g., `"SlidesGen.pdf"`)
  - **OR**
- `GOOGLE_DRIVE_STATIC_FILE_ID` - Direct file ID of the PDF (if you know it)

**Note:** If you set `GOOGLE_DRIVE_STATIC_FILE_NAME="SlidesGen.pdf"`, the system will search for a file with that exact name in your Google Drive and append new slides to it.

### Canva Integration (Optional)
- `CANVA_CLIENT_ID` - Canva OAuth Client ID
- `CANVA_CLIENT_SECRET` - Canva OAuth Client Secret
- `CANVA_TEMPLATE_ID` - Canva template design ID (if using Canva templates)
- `CANVA_STATIC_DESIGN_ID` - (Optional) Design ID to append slides to (for reference/logging)

**Note:** Canva OAuth tokens are stored in `canva_tokens.json` locally, or can be set via:
- `CANVA_REFRESH_TOKEN` - (For Render) Refresh token for auto-refresh
- `CANVA_ACCESS_TOKEN` - (For Render) Access token
- `CANVA_TOKEN_REFRESHED_AT` - (For Render) Timestamp of last refresh

### Background Removal APIs (Optional)
- `REMOVEBG_API_KEY` - remove.bg API key (for background removal)
- `OPENAI_API_KEY` - OpenAI API key (backup for background removal)

### AI/LLM (Optional)
- `GEMINI_API_KEY` - Google Gemini API key (for map generation and headshot processing)

### Notion Integration (Optional)
- `NOTION_API_KEY` - Notion API key
- `NOTION_DATABASE_ID` - Notion database ID
- `NOTION_TEMPLATE_PAGE_ID` - Notion template page ID

### DocSend (Optional)
- `DOCSEND_API_KEY` - DocSend API key
- `DOCSEND_INDIVIDUAL_DECK_ID` - Individual deck ID
- `DOCSEND_MASTER_DECK_ID` - Master deck ID

## Example .env File

```bash
# Google Drive (Required)
GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
GOOGLE_DRIVE_STATIC_FILE_NAME=SlidesGen.pdf

# Slide Template (Required)
SLIDE_TEMPLATE_PATH=/Users/yourname/slauson-automation/SLAUSON&CO.Template.pdf

# Canva (Optional)
CANVA_CLIENT_ID=your_client_id
CANVA_CLIENT_SECRET=your_client_secret
CANVA_TEMPLATE_ID=your_template_id

# Background Removal (Optional)
REMOVEBG_API_KEY=your_removebg_key
OPENAI_API_KEY=your_openai_key

# AI/LLM (Optional)
GEMINI_API_KEY=your_gemini_key

# Notion (Optional)
NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id
```

## For Render Deployment

When deploying to Render, set these in the Render dashboard under "Environment":

1. All the variables above
2. For Canva token persistence (optional):
   - `CANVA_REFRESH_TOKEN` - Get from `canva_tokens.json` after running `setup_canva_oauth.py`
   - `CANVA_ACCESS_TOKEN` - Get from `canva_tokens.json`
   - `CANVA_TOKEN_REFRESHED_AT` - Timestamp (Unix epoch)

## Quick Setup Checklist

- [ ] Set `GOOGLE_DRIVE_STATIC_FILE_NAME="SlidesGen.pdf"` (or use file ID)
- [ ] Set `SLIDE_TEMPLATE_PATH` to your template PDF path
- [ ] (Optional) Set Canva OAuth credentials if using Canva
- [ ] (Optional) Set API keys for background removal if needed
- [ ] (Optional) Set `GEMINI_API_KEY` for map generation


