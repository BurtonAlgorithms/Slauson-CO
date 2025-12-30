# Railway Deployment Setup

## Quick Start

### Option 1: Deploy via Railway Dashboard (Recommended)

1. **Go to:** https://railway.app
2. **Sign up / Login**
3. **Click "New Project"**
4. **Choose "Deploy from GitHub repo"**
   - Connect your GitHub account
   - Select repository: `BurtonAlgorithms/Slauson-CO` (or your repo)
5. **Railway will auto-detect:**
   - Python environment
   - `requirements.txt`
   - `Procfile` or `railway.json`
6. **Add Environment Variables:**
   - Go to your service → Variables tab
   - Add all required variables (see below)

### Option 2: Deploy via Railway CLI

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login:**
   ```bash
   railway login
   ```

3. **Initialize and Deploy:**
   ```bash
   cd /path/to/slauson-automation
   railway init
   railway up
   ```

4. **Set Environment Variables:**
   ```bash
   railway variables set REMOVEBG_API_KEY=your_key
   railway variables set NUMBA_DISABLE_JIT=1
   # ... add all other variables
   ```

---

## Required Environment Variables

Add these in Railway Dashboard → Your Service → Variables:

### Required:
- `PORT` - Railway sets this automatically (don't add manually)
- `NUMBA_DISABLE_JIT=1` - Prevents numba compilation timeouts
- `OMP_NUM_THREADS=1` - Limits CPU threads
- `CUDA_VISIBLE_DEVICES=""` - Disables GPU detection

### Optional (but recommended):
- `FLASK_DEBUG=False` - Production mode
- `PYTHON_VERSION=3.11.0` - Python version

### API Keys (as needed):
- `REMOVEBG_API_KEY` - For background removal API
- `OPENAI_API_KEY` - For OpenAI image processing
- `GEMINI_API_KEY` - For Gemini map generation
- `NOTION_API_KEY` - For Notion integration
- `CANVA_CLIENT_ID` - For Canva integration
- `CANVA_CLIENT_SECRET` - For Canva integration
- `GOOGLE_DRIVE_CREDENTIALS_JSON` - For Google Drive integration
- `SLIDE_TEMPLATE_PATH` - Path to slide template (if not in repo)

See `ENVIRONMENT_VARIABLES.md` for complete list.

---

## Configuration Files

### `railway.json`
Already configured with:
- Start command: `gunicorn webhook_listener:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2`
- Auto-restart on failure

### `Procfile`
Alternative start command (Railway will use `railway.json` if present):
```
web: gunicorn webhook_listener:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

### `requirements.txt`
All dependencies are listed and will be installed automatically.

---

## After Deployment

1. **Get Your URL:**
   - Railway provides: `https://your-app.railway.app`
   - Webhook URL: `https://your-app.railway.app/webhook/onboarding`

2. **Test Health Check:**
   ```bash
   curl https://your-app.railway.app/health
   ```

3. **Test Webhook:**
   ```bash
   curl -X POST https://your-app.railway.app/webhook/onboarding \
     -H "Content-Type: application/json" \
     -d '{"company_data": {"name": "Test Company"}}'
   ```

4. **Update Zapier/Make.com:**
   - Replace webhook URL with Railway URL
   - Test the integration

---

## Troubleshooting

### Build Fails
- Check Railway build logs
- Verify `requirements.txt` is correct
- Check Python version compatibility

### App Crashes on Start
- Check Railway logs
- Verify all environment variables are set
- Check `railway.json` start command is correct

### Timeout Issues
- Already configured with `--timeout 120`
- `NUMBA_DISABLE_JIT=1` prevents numba compilation timeouts
- Workers set to 2 for better concurrency

### Port Issues
- Railway sets `PORT` automatically
- Don't manually set `PORT` variable
- Code uses `os.getenv("PORT", 5001)` as fallback

---

## Railway vs Render

| Feature | Railway | Render |
|---------|---------|--------|
| Free Tier | ✅ Yes | ✅ Yes |
| Auto-Deploy | ✅ Yes | ✅ Yes |
| Web Interface | ✅ Yes | ✅ Yes |
| CLI | ✅ Yes | ⚠️ Limited |
| Reliability | ✅ Good | ✅ Good |
| Python Support | ✅ Excellent | ✅ Excellent |

Both platforms work well. Choose based on preference!

---

## Cost

**Free Tier:**
- $5/month credit
- Usually enough for small apps
- Pay-as-you-go after

**Pricing:**
- ~$0.000463 per GB-hour
- ~$0.01 per GB bandwidth
- Very affordable for small apps

---

## Next Steps

1. Deploy to Railway
2. Set all environment variables
3. Test the webhook endpoint
4. Update Zapier/Make.com with new URL
5. Monitor logs for any issues

