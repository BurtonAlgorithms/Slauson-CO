# Complete OAuth Setup Guide

This guide will help you set up OAuth authentication for **Google Drive** and **Canva** APIs, even if you don't have access to the GitHub repository. Follow these steps to get your own OAuth credentials working.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Drive OAuth Setup](#google-drive-oauth-setup)
3. [Canva OAuth Setup](#canva-oauth-setup)
4. [Using Your Credentials](#using-your-credentials)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, make sure you have:

- ✅ A Google account (Gmail or Google Workspace)
- ✅ A Canva account (free or Pro)
- ✅ Python 3.8+ installed
- ✅ Basic command-line knowledge

---

## Google Drive OAuth Setup

### Step 1: Create a Google Cloud Project

1. **Go to**: [Google Cloud Console](https://console.cloud.google.com/)
2. **Sign in** with your Google account
3. **Create a new project** (or select an existing one):
   - Click the project dropdown at the top
   - Click "New Project"
   - Name it (e.g., "Slauson Automation")
   - Click "Create"

### Step 2: Enable Google Drive API

1. In your project, go to **"APIs & Services"** → **"Library"**
2. **Search for**: "Google Drive API"
3. **Click** on "Google Drive API"
4. **Click** "Enable"

### Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services"** → **"OAuth consent screen"**
2. **Choose user type**:
   - **External** (for personal Gmail accounts)
   - **Internal** (for Google Workspace accounts)
3. **Fill in app information**:
   - App name: `Slauson Automation` (or your choice)
   - User support email: Your email
   - Developer contact: Your email
4. **Click "Save and Continue"**
5. **Add scopes** (if prompted):
   - Click "Add or Remove Scopes"
   - Search for: `https://www.googleapis.com/auth/drive.file`
   - Check the box
   - Click "Update" → "Save and Continue"
6. **Add test users** (IMPORTANT for testing):
   - Click "+ ADD USERS"
   - Add your email address
   - Click "Add"
   - Click "Save and Continue"
7. **Review and go back to dashboard**

### Step 4: Create OAuth Credentials

1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"Create Credentials"** → **"OAuth client ID"**
3. **Application type**: Select **"Desktop app"**
4. **Name**: `Slauson Automation Desktop` (or your choice)
5. **Click "Create"**
6. **Download the credentials**:
   - A popup will show your Client ID and Client Secret
   - Click the **download icon** (⬇️) to download JSON
   - **Save the file as `credentials.json`** in your project directory

### Step 5: Run OAuth Setup Script

1. **Make sure you have `credentials.json`** in your project directory
2. **Run the setup script**:
   ```bash
   python setup_google_oauth.py
   ```
3. **A browser will open**:
   - Sign in with your Google account
   - Click "Allow" to grant permissions
   - You'll see "Authorization Successful!"
4. **The script will create `token.json`** automatically

### ✅ Google Drive OAuth Complete!

You should now have:
- ✅ `credentials.json` - OAuth client credentials
- ✅ `token.json` - Your authorization token

---

## Canva OAuth Setup

### Step 1: Create a Canva App

1. **Go to**: [Canva Developers](https://www.canva.com/developers/)
2. **Sign in** with your Canva account
3. **Click "Create an app"** (or go to [App Dashboard](https://www.canva.com/developers/apps))
4. **Fill in app details**:
   - App name: `Slauson Automation` (or your choice)
   - Description: (optional)
   - App website: (optional, can use `http://localhost`)
5. **Click "Create app"**

### Step 2: Configure OAuth Settings

1. In your app dashboard, go to **"OAuth"** or **"Authentication"** section
2. **Add redirect URI**:
   - Click "Add redirect URI"
   - Enter: `https://oauth.example.com/canva/callback`
   - Click "Save"
3. **Note your credentials**:
   - **Client ID**: (starts with `OC-`, e.g., `OC-AZrV8PyvUWAe`)
   - **Client Secret**: (long string)
   - **Copy these values** - you'll need them!

### Step 3: Set Up Environment Variables

1. **Create or edit `.env` file** in your project directory:
   ```bash
   # Canva OAuth Credentials
   CANVA_CLIENT_ID=OC-XXXXXXXXXXXXX
   CANVA_CLIENT_SECRET=your_client_secret_here
  CANVA_REDIRECT_URI=https://oauth.example.com/canva/callback
   ```

2. **Replace**:
   - `OC-XXXXXXXXXXXXX` with your actual Client ID
   - `your_client_secret_here` with your actual Client Secret
   - Keep the redirect URI as shown (or match what you configured in Canva)

### Step 4: Run Canva OAuth Setup Script

1. **Make sure `.env` is configured** with your Canva credentials
2. **Run the setup script**:
   ```bash
   python setup_canva_oauth.py
   ```
3. **A browser will open**:
   - Sign in with your Canva account
   - Click "Allow" to grant permissions
   - You'll see "Authorization Successful!"
4. **The script will create `canva_tokens.json`** automatically

### ✅ Canva OAuth Complete!

You should now have:
- ✅ `.env` file with `CANVA_CLIENT_ID` and `CANVA_CLIENT_SECRET`
- ✅ `canva_tokens.json` - Your authorization tokens

---

## Using Your Credentials

### For Local Development

Your credentials are stored in:
- **Google**: `token.json`
- **Canva**: `canva_tokens.json`

The code will automatically use these files when running locally.

### For Production (Render/Railway)

You need to set **environment variables** in your deployment platform:

#### Google Drive (Render/Railway)

1. **Get your token JSON**:
   ```bash
   cat token.json
   ```
2. **Copy the entire JSON** (all on one line)
3. **In Render/Railway dashboard**:
   - Go to your service → Environment
   - Add variable: `GOOGLE_DRIVE_CREDENTIALS_JSON`
   - Paste the entire JSON as the value
   - Save

#### Canva (Render/Railway)

1. **Get your token values**:
   ```bash
   cat canva_tokens.json
   ```
2. **In Render/Railway dashboard**, add these variables:
   - `CANVA_CLIENT_ID` = Your Client ID (from `.env`)
   - `CANVA_CLIENT_SECRET` = Your Client Secret (from `.env`)
   - `CANVA_REFRESH_TOKEN` = Value from `refresh_token` field in `canva_tokens.json`
   - `CANVA_ACCESS_TOKEN` = Value from `access_token` field in `canva_tokens.json`
   - `CANVA_TOKEN_REFRESHED_AT` = Current timestamp:
     ```bash
     python3 -c "import time; print(time.time())"
     ```
   - `CANVA_REDIRECT_URI` = `https://oauth.example.com/canva/callback` (or your configured URI)

---

## Troubleshooting

### Google Drive OAuth

**Problem**: "access_denied" error
- **Solution**: Make sure your email is added as a test user in OAuth consent screen

**Problem**: "credentials.json not found"
- **Solution**: Download the OAuth client JSON from Google Cloud Console and save as `credentials.json`

**Problem**: "Invalid credentials"
- **Solution**: Make sure you downloaded the correct credentials (Desktop app type)

**Problem**: Token expired
- **Solution**: Run `python setup_google_oauth.py` again to refresh

### Canva OAuth

**Problem**: "CANVA_CLIENT_ID not set"
- **Solution**: Make sure `.env` file has `CANVA_CLIENT_ID` and `CANVA_CLIENT_SECRET`

**Problem**: "Redirect URI mismatch"
- **Solution**: Make sure the redirect URI in Canva app matches `CANVA_REDIRECT_URI` in `.env`

**Problem**: "Token exchange failed"
- **Solution**: 
  1. Check that Client ID and Secret are correct
  2. Verify redirect URI matches exactly
  3. Make sure you're using the correct Canva account

**Problem**: "No authorization code received"
- **Solution**: 
  1. Make sure you clicked "Allow" in the browser
  2. Don't close the browser window too quickly
  3. Check that the local server port (3001) is not blocked by firewall

### General Issues

**Problem**: Scripts don't run
- **Solution**: Make sure Python 3.8+ is installed and you're in the project directory

**Problem**: Browser doesn't open
- **Solution**: Manually copy the authorization URL from the terminal and paste in browser

**Problem**: Port already in use
- **Solution**: 
  - For Google: The script will automatically find an available port
- For Canva: Change `CANVA_REDIRECT_URI` in `.env` to your configured URL (e.g., `https://oauth.example.com/canva/callback`)

---

## Quick Reference

### Files You'll Create

| File | Purpose | When Created |
|------|---------|--------------|
| `credentials.json` | Google OAuth client | Download from Google Cloud Console |
| `token.json` | Google authorization token | Created by `setup_google_oauth.py` |
| `.env` | Environment variables | You create this manually |
| `canva_tokens.json` | Canva authorization tokens | Created by `setup_canva_oauth.py` |

### Environment Variables Needed

**For Local Development** (`.env` file):
```bash
# Canva
CANVA_CLIENT_ID=OC-XXXXXXXXXXXXX
CANVA_CLIENT_SECRET=your_secret_here
CANVA_REDIRECT_URI=https://oauth.example.com/canva/callback

# Optional: Other API keys
GEMINI_API_KEY=your_key_here
REMOVEBG_API_KEY=your_key_here
# ... etc
```

**For Production** (Render/Railway environment variables):
- `GOOGLE_DRIVE_CREDENTIALS_JSON` (entire token.json as JSON string)
- `CANVA_CLIENT_ID`
- `CANVA_CLIENT_SECRET`
- `CANVA_REFRESH_TOKEN`
- `CANVA_ACCESS_TOKEN`
- `CANVA_TOKEN_REFRESHED_AT`
- `CANVA_REDIRECT_URI`

---

## Next Steps

After completing OAuth setup:

1. ✅ Test locally: Run your application and verify it can access Google Drive and Canva
2. ✅ Deploy to production: Set environment variables in Render/Railway
3. ✅ Monitor tokens: Access tokens expire after ~4 hours but refresh automatically
4. ✅ Update tokens: If refresh fails, re-run the setup scripts

---

## Support

If you encounter issues not covered here:

1. **Check the error message** - It usually tells you what's wrong
2. **Verify credentials** - Make sure all IDs and secrets are correct
3. **Check redirect URIs** - They must match exactly
4. **Review OAuth consent screens** - Make sure test users are added (Google) and scopes are correct

---

**Last Updated**: 2025-01-XX
**Version**: 1.0

