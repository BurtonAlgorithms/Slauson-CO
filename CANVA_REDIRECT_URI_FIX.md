# Fix Canva OAuth Redirect URI Error

## The Error

```
error=invalid_request
error_description=The provided redirect uri doesn't match any of the stored uris for this client.
```

This means the redirect URI in the script doesn't match what you configured in your Canva app.

## Solution

### Step 1: Check Your Canva App Settings

1. Go to [Canva Developers Portal](https://www.canva.com/developers/)
2. Open your app (the one with Client ID: `OC-AZrV8PyvUWAe`)
3. Find **"Redirect URIs"** or **"OAuth Settings"** section
4. Check what redirect URIs are currently configured

### Step 2: Match the Redirect URI

You have two options:

#### Option A: Update Canva App (Recommended)

1. In your Canva app settings, add this redirect URI:
   ```
   https://oauth.example.com/canva/callback
   ```
2. Save the changes
3. Run `python setup_canva_oauth.py` again

#### Option B: Update the Script

If your Canva app already has a different redirect URI configured (like `https://oauth.example.com/canva/callback`):

1. Open `setup_canva_oauth.py`
2. Find this line:
   ```python
  REDIRECT_URI = "https://oauth.example.com/canva/callback"
   ```
3. Change it to match your Canva app:
   ```python
  REDIRECT_URI = "https://oauth.example.com/canva/callback"  # Or whatever you have in Canva
   ```
4. Also update the port in the server setup (line ~140):
   ```python
  httpd = socketserver.TCPServer(("", 3001), handler)  # Ensure the port matches your URI
   ```
5. Save and run again

## Common Redirect URIs

- `https://oauth.example.com/canva/callback` (default in script)
- `https://your-domain.com/canva/callback`
- `https://yourdomain.example/oauth/redirect`

**Important:** The URI must match EXACTLY (including http vs https, port number, and path).

## Quick Fix

If you want to use the default `https://oauth.example.com/canva/callback`:

1. Go to your Canva app dashboard
2. Add redirect URI: `https://oauth.example.com/canva/callback`
3. Save
4. Run `python setup_canva_oauth.py` again


