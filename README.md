# 🎬 ReelForge — Deploy to Railway

## Project Structure
```
reelforge-deploy/
├── app.py              ← Flask backend (serves frontend + all APIs)
├── requirements.txt    ← Python dependencies
├── Procfile            ← Tells Railway how to start the app
├── nixpacks.toml       ← Tells Railway to install ffmpeg + Python
├── .gitignore
└── frontend/
    └── index.html      ← Full app UI
```

---

## Deploy Steps (takes ~5 minutes)

### Step 1 — Create GitHub repo
1. Go to github.com → New repository
2. Name it `reelforge` (this becomes part of your URL)
3. Make it **Public**
4. Don't add README
5. Click **Create repository**

### Step 2 — Push this folder to GitHub
In VS Code terminal, inside this folder:
```bash
git init
git add .
git commit -m "Initial deploy"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/reelforge.git
git push -u origin main
```
Replace `YOUR_USERNAME` with your actual GitHub username.

### Step 3 — Deploy on Railway
1. Go to **railway.app**
2. Sign up with GitHub (free)
3. Click **New Project**
4. Click **Deploy from GitHub repo**
5. Select your `reelforge` repo
6. Railway auto-detects Python and starts deploying

### Step 4 — Set your custom subdomain
1. Once deployed, click your service in Railway
2. Go to **Settings** → **Networking** → **Generate Domain**
3. Click **Generate Domain**
4. You'll get something like `reelforge-production.up.railway.app`
5. To customise it: click the domain → edit the prefix → save
   - Example: change to `reelforge` → `reelforge.up.railway.app`

### Step 5 — Done! 🎉
Your app is live at your Railway URL.
Open it in any browser, on any device.

---

## Free Tier Limits (Railway)
- $5 free credit per month
- ~500 hours of compute (enough for personal use)
- 1GB RAM, shared CPU
- Files deleted when server restarts (downloads are temp anyway)

---

## Local Development (still works)
```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```
