# Fix Canva Authentication on Render

## Problem
Error: `"Token lineage has been revoked"` - The Canva refresh token in Render is invalid/expired.

## Solution: Re-authorize and persist tokens (no scripts)

### Step 1: Re-authorize via the running server

1. Ensure these env vars are set in Render:
   - `CANVA_CLIENT_ID`
   - `CANVA_CLIENT_SECRET`
   - `CANVA_REDIRECT_URI` (must exactly match the redirect URI in your Canva app, e.g. `https://your-app.onrender.com/oauth/canva/callback`)
   - `FLASK_SECRET_KEY` (any long random string)

2. Visit this URL in your browser (while logged into the right Canva account):

   `https://your-app.onrender.com/oauth/canva/start`

3. Approve the app. After redirect, you should see a success message.

4. Tokens are saved automatically (and will auto-refresh). For best persistence across restarts, configure the Google Drive token store (see below).

### Optional: persist tokens in Google Drive (recommended)

If your server has Google Drive OAuth configured, set:

```bash
CANVA_TOKEN_STORE_DRIVE_FILE_NAME=canva_tokens.json
# Optional: choose a folder (defaults to GOOGLE_DRIVE_FOLDER_ID if set)
CANVA_TOKEN_STORE_DRIVE_FOLDER_ID=your_folder_id
```

This stores Canva tokens in a private JSON file on Drive so refresh survives restarts without manual env var updates.

### If you still prefer env-var tokens

Go to your Render dashboard > Environment Variables and update these (tokens can be obtained from local flow if needed):

#### Required Canva Variables:

```bash
CANVA_CLIENT_ID=your_new_client_id
CANVA_CLIENT_SECRET=your_new_client_secret
CANVA_REFRESH_TOKEN=your_new_refresh_token_from_canva_tokens.json
CANVA_ACCESS_TOKEN=your_new_access_token_from_canva_tokens.json
CANVA_TOKEN_REFRESHED_AT=current_unix_timestamp
```

#### How to Get the Values:

1. **CANVA_CLIENT_ID** and **CANVA_CLIENT_SECRET**: 
   - From your Canva app at canva.dev
   - Or from your `.env` file

2. **CANVA_REFRESH_TOKEN**: 
   - Copy the `refresh_token` value from `canva_tokens.json`
   - It's a long encrypted string starting with `eyJ...`

3. **CANVA_ACCESS_TOKEN**: 
   - Copy the `access_token` value from `canva_tokens.json`
   - It's a JWT token starting with `eyJ...`

4. **CANVA_TOKEN_REFRESHED_AT**: 
   - Copy the `token_refreshed_at` value from `canva_tokens.json`
   - It's a Unix timestamp (e.g., `1766962736.598428`)
   - Or use current timestamp: `python -c "import time; print(time.time())"`

### Step 3: Redeploy on Render

After updating environment variables:
1. Go to Render dashboard
2. Click "Manual Deploy" > "Clear build cache & deploy"
3. Or wait for auto-deploy (if enabled)

### Step 4: Verify

Check the logs - you should see:
```
✓ Loaded stored Canva OAuth tokens from environment variables
✓ Successfully refreshed access token!
```

---

## Quick Copy-Paste from canva_tokens.json

After running `setup_canva_oauth.py`, your `canva_tokens.json` will look like:

```json
{
  "access_token": "eyJraWQiOiI...",
  "refresh_token": "eyJhbGciOiJSU0EtT0FFUC0yNTYiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2Iiwi...",
  "token_type": "Bearer",
  "expires_in": 14400,
  "token_refreshed_at": 1766962736.598428
}
```

**Copy these values to Render:**
- `access_token` → `CANVA_ACCESS_TOKEN`
- `refresh_token` → `CANVA_REFRESH_TOKEN`
- `token_refreshed_at` → `CANVA_TOKEN_REFRESHED_AT`

---

## Important Notes

1. **Tokens auto-refresh**: The system will automatically refresh tokens when they expire (every 4 hours)
2. **Refresh token is long-lived**: The refresh token should last a long time, but if it gets revoked, you'll need to re-run `setup_canva_oauth.py`
3. **Don't commit tokens**: Never commit `canva_tokens.json` to git (it's already in `.gitignore`)

---

## If You Don't Have Canva App Credentials

1. Go to [Canva Developers](https://www.canva.dev/)
2. Sign in with the **new company's Canva account**
3. Create a new app or use existing app
4. Get the **Client ID** and **Client Secret**
5. Use these in Step 1 above

---

## Troubleshooting

**Error: "Token lineage has been revoked"**
- The refresh token is invalid
- Solution: Generate new tokens (Step 1-2 above)

**Error: "Rate limited (429)"**
- Too many token refresh attempts
- Solution: Wait a few minutes, then redeploy

**Error: "No refresh token available"**
- `CANVA_REFRESH_TOKEN` not set in Render
- Solution: Set it in Render environment variables

**Error: "invalid_grant"**
- Refresh token is expired/revoked
- Solution: Generate new tokens


