# 🚀 Resume Radar — Render Deployment Guide

## Step 1: GitHub pe Push karo

```bash
cd Resume_Radar_
git init
git add .
git commit -m "Resume Radar - ready for deployment"
```

GitHub pe new repository banao (`Resume_Radar`) aur push karo:
```bash
git remote add origin https://github.com/YOUR_USERNAME/Resume_Radar.git
git branch -M main
git push -u origin main
```

## Step 2: Render pe Account banao

1. **https://render.com** pe jaao
2. **Sign up** — GitHub se login karo (easy)

## Step 3: Web Service Create karo

1. Dashboard pe **"New +"** → **"Web Service"** click karo
2. **"Connect a repository"** → apna `Resume_Radar` repo select karo
3. Settings fill karo:
   - **Name:** `resume-radar`
   - **Region:** Singapore (closest to India)
   - **Branch:** `main`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Plan:** Free ✅

## Step 4: Environment Variables set karo

Render dashboard → **"Environment"** tab mein yeh add karo:

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | Tumhara Gemini API key (jo .env mein hai) |
| `SECRET_KEY` | Kuch bhi random likh do (e.g. `my-super-secret-key-2024`) |
| `FLASK_DEBUG` | `False` |

## Step 5: Deploy! 🎉

**"Create Web Service"** button dabao — Render automatically:
- Code download karega
- Dependencies install karega
- App start karega
- **Public URL dega** (e.g. `https://resume-radar.onrender.com`)

## ⚠️ Important Notes

- **Free plan** pe app 15 min inactivity ke baad sleep ho jaata hai — first visit mein 30-50 sec lagega
- **Database:** Free tier pe SQLite use hoga (file-based) — data deploy ke baad reset ho sakta hai. Production ke liye Render ka PostgreSQL add karo (free tier available)
- **.env file** GitHub pe push MAT karo — already .gitignore mein hai ✅

## 🔗 PostgreSQL Add karna hai? (Optional but recommended)

1. Render Dashboard → **"New +"** → **"PostgreSQL"**
2. Free plan select karo
3. Database banne ke baad **"Internal Database URL"** copy karo
4. Web Service ke Environment mein `DATABASE_URL` key mein paste karo
5. App automatically PostgreSQL use karega!
