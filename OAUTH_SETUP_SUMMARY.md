# OAuth Setup - Summary

This document summarizes the OAuth setup system that allows anyone to set up their own Google Drive and Canva OAuth authentication, even without access to the GitHub repository.

---

## 📁 Files Created/Updated

### Documentation
1. **OAUTH_SETUP_GUIDE.md** - Comprehensive step-by-step guide
   - Complete instructions for Google Drive OAuth
   - Complete instructions for Canva OAuth
   - Troubleshooting section
   - Production deployment instructions

2. **OAUTH_QUICK_START.md** - Quick reference guide
   - 5-minute setup instructions
   - Quick troubleshooting tips

3. **OAUTH_SETUP_SUMMARY.md** - This file
   - Overview of the OAuth setup system

### Scripts
1. **setup_oauth.py** - Master setup wizard (NEW)
   - Interactive wizard for both OAuth setups
   - Checks prerequisites
   - Guides users through setup
   - Shows setup status

2. **setup_google_oauth.py** - Google Drive OAuth setup (IMPROVED)
   - Better error handling
   - Interactive instructions
   - Checks for existing tokens
   - Validates credentials.json
   - More user-friendly output

3. **setup_canva_oauth.py** - Canva OAuth setup (IMPROVED)
   - Better error handling
   - Interactive instructions
   - Checks for existing tokens
   - Validates .env configuration
   - Port availability checking
   - More user-friendly output

---

## 🎯 How It Works

### For Users Without GitHub Access

Users can:

1. **Get the setup files** (via email, shared folder, etc.):
   - `setup_oauth.py` (or individual setup scripts)
   - `OAUTH_SETUP_GUIDE.md`
   - `OAUTH_QUICK_START.md`

2. **Follow the guide** to create their own OAuth credentials:
   - Google Cloud Console → Create OAuth credentials
   - Canva Developers → Create app

3. **Run the setup scripts**:
   ```bash
   python setup_oauth.py
   ```

4. **Get their own tokens**:
   - `token.json` (Google Drive)
   - `canva_tokens.json` (Canva)

### For Production Deployment

Users can:

1. **Set up locally** using the scripts
2. **Copy token values** to production environment variables
3. **Deploy** with their own credentials

---

## 🚀 Usage

### Quick Start

```bash
# Run the interactive wizard
python setup_oauth.py
```

### Individual Setup

```bash
# Google Drive only
python setup_google_oauth.py

# Canva only
python setup_canva_oauth.py
```

### What Each Script Does

**setup_oauth.py** (Master Wizard):
- Checks prerequisites
- Asks what to set up (Google, Canva, or both)
- Calls appropriate setup scripts
- Shows summary

**setup_google_oauth.py**:
- Checks for existing `token.json`
- Validates `credentials.json`
- Opens browser for OAuth flow
- Saves `token.json`

**setup_canva_oauth.py**:
- Checks for existing `canva_tokens.json`
- Validates `.env` configuration
- Opens browser for OAuth flow
- Saves `canva_tokens.json`

---

## 📋 Prerequisites

Users need:

1. **Python 3.8+**
2. **Required packages**:
   ```bash
   pip install google-auth-oauthlib google-auth requests python-dotenv
   ```
3. **Accounts**:
   - Google account (Gmail or Workspace)
   - Canva account (free or Pro)

---

## 🔑 What Users Need to Create

### Google Drive

1. **Google Cloud Project** (free)
2. **OAuth credentials** (free)
   - Download as `credentials.json`
3. **Authorization token** (created by script)
   - Saved as `token.json`

### Canva

1. **Canva Developer App** (free)
   - Get Client ID and Secret
2. **Environment variables** (`.env` file)
   - `CANVA_CLIENT_ID`
   - `CANVA_CLIENT_SECRET`
   - `CANVA_REDIRECT_URI`
3. **Authorization tokens** (created by script)
   - Saved as `canva_tokens.json`

---

## 📝 Files Created by Users

| File | Source | Purpose |
|------|--------|---------|
| `credentials.json` | Google Cloud Console | OAuth client credentials |
| `token.json` | `setup_google_oauth.py` | Google authorization token |
| `.env` | User creates | Canva credentials |
| `canva_tokens.json` | `setup_canva_oauth.py` | Canva authorization tokens |

---

## 🌐 Production Deployment

### Render/Railway Environment Variables

**Google Drive**:
- `GOOGLE_DRIVE_CREDENTIALS_JSON` = entire `token.json` content (as JSON string)

**Canva**:
- `CANVA_CLIENT_ID` = from `.env`
- `CANVA_CLIENT_SECRET` = from `.env`
- `CANVA_REFRESH_TOKEN` = from `canva_tokens.json`
- `CANVA_ACCESS_TOKEN` = from `canva_tokens.json`
- `CANVA_TOKEN_REFRESHED_AT` = current timestamp
- `CANVA_REDIRECT_URI` = from `.env`

See `OAUTH_SETUP_GUIDE.md` for detailed instructions.

---

## ✨ Key Features

1. **Standalone** - Works without GitHub repository
2. **Interactive** - Guides users through setup
3. **Error Handling** - Clear error messages and troubleshooting
4. **Validation** - Checks prerequisites and existing tokens
5. **Documentation** - Comprehensive guides included
6. **User-Friendly** - Clear instructions and helpful prompts

---

## 📚 Documentation Structure

```
OAUTH_QUICK_START.md      → Quick 5-minute setup
OAUTH_SETUP_GUIDE.md      → Complete detailed guide
OAUTH_SETUP_SUMMARY.md    → This overview
```

Users can start with `OAUTH_QUICK_START.md` and refer to `OAUTH_SETUP_GUIDE.md` for details.

---

## 🔄 Token Refresh

Both Google and Canva tokens refresh automatically:

- **Google**: Tokens expire after ~1 hour, refresh automatically
- **Canva**: Access tokens expire after ~4 hours, refresh automatically

If refresh fails, users can re-run the setup scripts.

---

## 🎓 For New Users

**Recommended path**:

1. Read `OAUTH_QUICK_START.md` (5 minutes)
2. Run `python setup_oauth.py` (interactive wizard)
3. Follow on-screen instructions
4. Refer to `OAUTH_SETUP_GUIDE.md` if issues arise

**Alternative path** (for experienced users):

1. Read `OAUTH_SETUP_GUIDE.md`
2. Create credentials manually
3. Run individual setup scripts

---

## ✅ Success Criteria

Setup is successful when:

- ✅ `token.json` exists (Google Drive)
- ✅ `canva_tokens.json` exists (Canva)
- ✅ Application can authenticate with both services
- ✅ No errors in setup scripts

---

## 🆘 Support

If users encounter issues:

1. Check `OAUTH_SETUP_GUIDE.md` troubleshooting section
2. Verify all prerequisites are met
3. Check error messages for specific issues
4. Ensure credentials are correct and valid

---

**Last Updated**: 2025-01-XX
**Version**: 1.0

