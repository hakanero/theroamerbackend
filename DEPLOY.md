# The Roamer Backend - Render.com Deployment

Deploy this Flask backend to Render.com for hassle-free hosting with automatic CORS support.

## Quick Deploy to Render.com

1. **Go to [render.com](https://render.com)** and sign up/login with GitHub

2. **Click "New +" → "Web Service"**

3. **Connect this repository**: `hakanero/theroamerbackend`

4. **Configure the service**:
   - **Name**: `theroamer-backend` (or any name)
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: leave empty
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`
   - **Instance Type**: Free (or paid for better performance)

5. **Add Environment Variables** (click "Advanced" then add these):
   ```
   GENAI_API_KEY=your_google_genai_api_key
   MAPS_API_KEY=your_google_maps_api_key
   ELEVEN_API_KEY=your_elevenlabs_api_key
   ```

6. **Click "Create Web Service"**

That's it! Render will:
- ✅ Automatically deploy your Flask app
- ✅ Handle CORS properly
- ✅ Give you a URL like `https://theroamer-backend.onrender.com`
- ✅ Auto-deploy on every git push

## Update Your Frontend

Once deployed, update your frontend to use:
```
https://your-app-name.onrender.com/audio
```

## Why Render > Vercel for this project?

- ✅ Native Flask support (no serverless conversion needed)
- ✅ CORS works out of the box
- ✅ Supports long-running requests (audio generation)
- ✅ Free tier available
- ✅ Simpler deployment process

## Local Testing

```bash
python app.py
# Test at http://localhost:8080
```

## Alternative: Railway.app

If you prefer Railway:
1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub repo"
3. Select this repo
4. Add environment variables
5. Done!

Railway auto-detects Python and runs it correctly.
