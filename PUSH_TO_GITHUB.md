# Push to GitHub - Quick Guide

## Your Repository is Ready!

All files are committed and ready to push. You just need to:

1. **Create GitHub repository**
2. **Add remote**
3. **Push**

## Step 1: Create GitHub Repository

Go to: https://github.com/new

**Settings:**
- **Repository name:** `slauson-automation`
- **Description:** "Portfolio onboarding automation for Slauson & Co."
- **Visibility:** Private (recommended)
- **DO NOT** check "Initialize with README" (we already have files)
- Click **"Create repository"**

## Step 2: Add Remote and Push

After creating the repo, GitHub will show you commands. Use these:

```bash
cd ~/slauson-automation
git remote add origin https://github.com/YOUR_USERNAME/slauson-automation.git
git branch -M main
git push -u origin main
```

**Replace `YOUR_USERNAME` with your GitHub username!**

## Authentication

When you push, GitHub will ask for credentials:

### Option 1: Personal Access Token (Recommended)

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. **Note:** `slauson-automation`
4. **Expiration:** 90 days (or your preference)
5. **Scopes:** Check `repo`
6. Click **"Generate token"**
7. **Copy the token**

When pushing:
- **Username:** your GitHub username
- **Password:** paste the token (not your GitHub password)

### Option 2: GitHub CLI (If Installed)

If you have `gh` CLI installed:
```bash
gh repo create slauson-automation --private --source=. --remote=origin --push
```

---

## After Pushing

Once pushed, you can:
- ✅ Deploy to Render using GitHub
- ✅ Share with team
- ✅ Version control
- ✅ Backup your code

---

**Create the GitHub repo and share the URL, or use the commands above!**

