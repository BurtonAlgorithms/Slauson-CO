# OAuth Quick Start Guide

**Quick setup guide for Google Drive and Canva OAuth authentication.**

---

## 🚀 Quick Setup (5 minutes)

### Option 1: Use the Setup Wizard (Recommended)

Run the interactive setup wizard:

```bash
python setup_oauth.py
```

This will guide you through setting up both Google Drive and Canva OAuth.

---

### Option 2: Manual Setup

#### Google Drive OAuth

1. **Get credentials from Google Cloud Console**:
   - Go to https://console.cloud.google.com/
   - Create project → Enable Google Drive API
   - Create OAuth credentials (Desktop app)
   - Download as `credentials.json`

2. **Run setup**:
   ```bash
   python setup_google_oauth.py
   ```

#### Canva OAuth

1. **Create Canva app**:
   - Go to https://www.canva.com/developers/
   - Create app → Get Client ID and Secret

2. **Add to `.env` file**:
   ```bash
   CANVA_CLIENT_ID=OC-XXXXXXXXXXXXX
   CANVA_CLIENT_SECRET=your_secret_here
  CANVA_REDIRECT_URI=https://oauth.example.com/canva/callback
   ```

3. **Run setup**:
   ```bash
   python setup_canva_oauth.py
   ```

---

## 📚 Full Documentation

For detailed step-by-step instructions, see:
- **[OAUTH_SETUP_GUIDE.md](OAUTH_SETUP_GUIDE.md)** - Complete guide with troubleshooting

---

## ✅ What You'll Get

After setup, you'll have:

- **Google Drive**: `token.json` and `credentials.json`
- **Canva**: `canva_tokens.json` and `.env` with credentials

These files are used automatically by the application.

---

## 🔧 Troubleshooting

**"credentials.json not found"** (Google)
- Download OAuth credentials from Google Cloud Console
- Save as `credentials.json` in project directory

**"CANVA_CLIENT_ID not set"** (Canva)
- Create `.env` file with your Canva credentials
- See [OAUTH_SETUP_GUIDE.md](OAUTH_SETUP_GUIDE.md) for details

**"Port already in use"** (Canva)
- Change `CANVA_REDIRECT_URI` in `.env` to use a different port
- Or close the application using the port

**Need help?**
- See [OAUTH_SETUP_GUIDE.md](OAUTH_SETUP_GUIDE.md) for detailed troubleshooting

---

## 📝 Files Created

| File | Purpose | When Created |
|------|---------|--------------|
| `credentials.json` | Google OAuth client | Download from Google Cloud |
| `token.json` | Google auth token | Created by setup script |
| `.env` | Environment variables | You create this |
| `canva_tokens.json` | Canva auth tokens | Created by setup script |

---

**Ready to start?** Run `python setup_oauth.py`!

