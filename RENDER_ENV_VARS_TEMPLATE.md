# Render Environment Variables - Fill-In Template

Copy this template and fill in your values in the Render dashboard.

---

## Required Variables

### Google Drive

```bash
GOOGLE_DRIVE_STATIC_FILE_NAME=SlidesGen.pdf
# OR if you know the file ID:
# GOOGLE_DRIVE_STATIC_FILE_ID=your_file_id_here

GOOGLE_DRIVE_FOLDER_ID=your_folder_id_here
# (Optional - only if you want slides in a specific folder)
```

### Slide Template

```bash
SLIDE_TEMPLATE_PATH=/app/SLAUSON&CO.Template.pdf
# (Adjust path based on where template is stored in Render)
```

### Google Drive OAuth

```bash
GOOGLE_DRIVE_CREDENTIALS_JSON='PASTE_ENTIRE_CONTENTS_OF_TOKEN_JSON_HERE'
```

**To get this value:**
1. Run `python setup_google_oauth.py` locally
2. Open `token.json`
3. Copy the entire JSON (all on one line)
4. Paste here

**Example format:**
```json
{"token":"ya29.a0Aa7pCA_...","refresh_token":"1//04AGutvUWys0KCgYIARAAGAQSNwF-...","token_uri":"https://oauth2.googleapis.com/token","client_id":"729051733822-...","client_secret":"GOCSPX-...","scopes":["https://www.googleapis.com/auth/drive.file"],"universe_domain":"googleapis.com","account":"","expiry":"2025-12-28T23:58:34.474431Z"}
```

---

## Canva Variables (If Using Canva)

### Canva App Credentials

```bash
CANVA_CLIENT_ID=OC-AZrV8Py...
# (Get from canva.dev - your app's Client ID)

CANVA_CLIENT_SECRET=your_client_secret_here
# (Get from canva.dev - your app's Client Secret)
```

### Canva OAuth Tokens

```bash
CANVA_REFRESH_TOKEN=eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2Iiwi...
# (Copy from canva_tokens.json after running setup_canva_oauth.py)

CANVA_ACCESS_TOKEN=eyJraWQiOiIyMzY4ZjRhYi00N2ZiLTQwN2MtYjM5Ni00NzgxODcwMjZkN2UiLCJhbGciOiJSUzI1NiJ9...
# (Copy from canva_tokens.json after running setup_canva_oauth.py)

CANVA_TOKEN_REFRESHED_AT=1766962736.598428
# (Copy from canva_tokens.json - Unix timestamp)
```

**To get these values:**
1. Run `python setup_canva_oauth.py` locally
2. Open `canva_tokens.json`
3. Copy each value:
   - `refresh_token` → `CANVA_REFRESH_TOKEN`
   - `access_token` → `CANVA_ACCESS_TOKEN`
   - `token_refreshed_at` → `CANVA_TOKEN_REFRESHED_AT`

### Canva Template (Optional)

```bash
CANVA_TEMPLATE_ID=your_template_id_here
# (Optional - only if using Canva templates)

CANVA_STATIC_DESIGN_ID=your_design_id_here
# (Optional - for reference/logging)
```

---

## Optional Variables

### Background Removal APIs

```bash
REMOVEBG_API_KEY=your_removebg_api_key
# (Optional - for background removal)

OPENAI_API_KEY=your_openai_api_key
# (Optional - backup for background removal)
```

### AI/LLM

```bash
GEMINI_API_KEY=your_gemini_api_key
# (Optional - for map generation and headshot processing)
```

### Notion Integration

```bash
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
NOTION_TEMPLATE_PAGE_ID=your_notion_template_page_id
# (Optional - only if using Notion integration)
```

### DocSend

```bash
DOCSEND_API_KEY=your_docsend_api_key
DOCSEND_INDIVIDUAL_DECK_ID=your_individual_deck_id
DOCSEND_MASTER_DECK_ID=your_master_deck_id
# (Optional - only if using DocSend API)
```

---

## Quick Setup Checklist

1. [ ] Set `GOOGLE_DRIVE_STATIC_FILE_NAME` or `GOOGLE_DRIVE_STATIC_FILE_ID`
2. [ ] Set `SLIDE_TEMPLATE_PATH`
3. [ ] Run `python setup_google_oauth.py` locally
4. [ ] Copy `token.json` contents → Set `GOOGLE_DRIVE_CREDENTIALS_JSON` in Render
5. [ ] (If using Canva) Run `python setup_canva_oauth.py` locally
6. [ ] (If using Canva) Copy values from `canva_tokens.json` → Set in Render
7. [ ] Set optional API keys if needed
8. [ ] Deploy and test

---

## Notes

- **All tokens must be from the NEW company's accounts** (not the old company)
- **Tokens auto-refresh** - you don't need to update them manually
- **If tokens get revoked**, re-run the setup scripts and update in Render
- **Never commit tokens to git** - they're already in `.gitignore`

