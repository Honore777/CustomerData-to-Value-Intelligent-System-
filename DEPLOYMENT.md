# 🚀 DEPLOYMENT GUIDE

Deploy to production in 30 minutes.

## Option 1: Railway (EASIEST - Recommended)

Railway = Deploy with 0 configuration

### Backend Deployment

```bash
# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Create project
cd supermarket-ai-agent
railway init

# 4. Add PostgreSQL plugin
# Go to railway.app dashboard
# Click "Add Service" → Select "PostgreSQL"
# Copy DATABASE_URL from Variables

# 5. Update .env with PostgreSQL URL from Railway
# DATABASE_URL=postgresql://...

# 6. Deploy
railway up

# Get URL
railway link
# Your API is live at: https://xxx.railway.app
```

### Frontend Deployment with Vercel

```bash
# 1. Create Vercel account (vercel.com)

# 2. Install Vercel CLI
npm i -g vercel

# 3. Deploy
cd frontend
vercel

# Follow prompts:
# - Confirm project name
# - Set REACT_APP_API_URL to your Railway API URL
# - Deploy

# Your frontend is live at: https://xxx.vercel.app
```

### Connect Frontend to Backend

In Vercel dashboard:
```
Settings → Environment Variables
Name: REACT_APP_API_URL
Value: https://xxx.railway.app
Redeploy
```

**Cost:**
- Railway: $5-20/month (includes PostgreSQL)
- Vercel: Free tier (generous)
- **Total: ~$5-20/month**

---

## Option 2: Heroku + Netlify

### Backend (Heroku)

```bash
# 1. Create Heroku account (heroku.com)

# 2. Install Heroku CLI
# Download from heroku.com/download

# 3. Create Procfile
echo "web: uvicorn backend.app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# 4. Create runtime.txt
echo "python-3.11.6" > runtime.txt

# 5. Login
heroku login

# 6. Create app
heroku create supermarket-ai-api

# 7. Add PostgreSQL free tier
heroku addons:create heroku-postgresql:hobby-dev -a supermarket-ai-api

# 8. Get DATABASE_URL
heroku config -a supermarket-ai-api

# 9. Deploy
git push heroku main

# Check logs
heroku logs --tail -a supermarket-ai-api
```

### Frontend (Netlify)

```bash
# 1. Create Netlify account (netlify.com)

# 2. Build frontend
cd frontend
npm run build

# 3. Drag & drop "build" folder to Netlify

# 4. Set environment variable
# Site settings → Build & deploy → Environment
# REACT_APP_API_URL = https://supermarket-ai-api.herokuapp.com
# Trigger redeploy
```

**Cost:**
- Heroku: $7/month (hobby tier PostgreSQL)
- Netlify: Free
- **Total: ~$7/month**

---

## Option 3: AWS EC2

### Backend (EC2 + RDS)

```bash
# 1. Create EC2 instance
# - Ubuntu 22.04
# - t3.micro (free tier)
# - Security group: allow 80, 443, 22

# 2. SSH into instance
ssh -i key.pem ubuntu@ec2-xxx.amazonaws.com

# 3. Setup
sudo apt update
sudo apt install python3-pip python3-venv nginx

# 4. Clone repo
git clone <your-repo>
cd supermarket-ai-agent

# 5. Setup Python app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Create RDS PostgreSQL
# AWS console → RDS → Create database
# Get endpoint: postgres-xxxx.rds.amazonaws.com

# 7. Update .env
# DATABASE_URL=postgresql://admin:password@postgres-xxx.rds.amazonaws.com:5432/supermarket_mvp

# 8. Setup Gunicorn
pip install gunicorn
gunicorn -w 4 backend.app.main:app

# 9. Setup Nginx reverse proxy
# Edit /etc/nginx/sites-available/default
# upstream fastapi { server 127.0.0.1:8000; }
# location / { proxy_pass http://fastapi; }

# 10. Start services
sudo systemctl restart nginx
```

**Cost:**
- EC2: $4.58/month (t3.micro reserved)
- RDS: $15/month (db.t3.micro PostgreSQL)
- Data transfer: Free (within region)
- **Total: ~$20/month**

---

## Option 4: Docker + Any Cloud

### Containerize Application

```bash
# Create Dockerfile in project root
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend ./backend
COPY frontend/build ./frontend/build

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Deploy to Render, Fly.io, or Digital Ocean

```bash
# Example: Railway with Docker
railway add Dockerfile
railway up

# Example: Render.com
# 1. Push to GitHub
# 2. Connect Render to GitHub
# 3. Create Web Service
# 4. Select Dockerfile
# 5. Deploy
```

---

## ✅ Pre-Deployment Checklist

```python
# Before going live, ensure:

□ DATABASE_URL is set (PostgreSQL in production)
□ DEBUG = False in settings
□ CORS origins configured (not "*")
□ HTTPS/SSL enabled
□ Logging configured
□ Error tracking (Sentry?) added
□ API rate limiting added
□ Authentication added (JWT tokens)
□ File upload validation added
□ Database backups configured
□ CDN for static files (Cloudflare)
□ Monitoring/uptime alerts set
□ Performance tested (load test)
□ Security audit completed
```

---

## 🔍 Post-Deployment

### Monitor Your App

```bash
# 1. Add monitoring
pip install sentry-sdk
# In main.py:
import sentry_sdk
sentry_sdk.init("your-sentry-url")

# 2. Setup alerts
# Railway/Heroku dashboard → Enable alerts
# Get notified if app crashes

# 3. Check logs daily
# Railway: railway logs
# Heroku: heroku logs --tail
# AWS: tail /var/log/syslog

# 4. Test endpoints regularly
# Uptime robot: uptimerobot.com
# Free monitoring tool
```

### Optimize Performance

```bash
# 1. Add Redis caching
pip install redis
# Cache predictions for 1 hour

# 2. Database indexing
# Already in models.py __table_args__

# 3. CDN for frontend assets
# Cloudflare: Free + fast

# 4. Compress API responses
# FastAPI does this automatically

# 5. Monitor database queries
# Use slow_db_query logging
```

---

## 💰 Cost Comparison

| Option | Cost/Month | Setup Time | Scaling |
|--------|-----------|-----------|---------|
| **Railway** (Recommended) | $5-20 | 5 min | Easy |
| Vercel + Railway | $5-20 | 10 min | Easy |
| Heroku + Netlify | $7-15 | 15 min | Medium |
| AWS EC2 + RDS | $20-50 | 30 min | Hard |
| Digital Ocean App | $12-20 | 10 min | Medium |

**RECOMMENDATION: Railway** - Best for startups, easiest to use.

---

## 🎯 Deployment Timeline

```
Day 1:
  □ Deploy backend to Railway
  □ Test API endpoints
  
Day 2:
  □ Deploy frontend to Vercel
  □ Test full flow
  
Day 3:
  □ Setup custom domain
  □ Enable HTTPS
  
Day 4:
  □ Create admin user
  □ Onboard first customer
  
Day 5:
  □ Monitor logs
  □ Fix any issues
  □ Go live!
```

---

## 🆘 Common Deployment Issues

### "ModuleNotFoundError" on Railway
```
Solution: 
requirements.txt is in wrong location
Fix: Place at project root, not in backend/
```

### "Cold start" slowdown
```
Solution:
First request takes 5-10 seconds
Fix: Use paid tier, or accept it as cost of operation
```

### "CORS error" in frontend
```
Solution:
API_URL not configured
Fix: Set REACT_APP_API_URL environment variable
```

### "Database connection refused"
```
Solution:
DATABASE_URL incorrect
Fix: Check Postgres credentials in Railway/Heroku
```

---

Ready to deploy? **Pick Railway and follow the steps above!** 🚀
