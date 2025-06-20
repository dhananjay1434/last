# 🚀 Slide Extractor Deployment Guide

## Architecture Overview

```
Frontend (React)          Backend API (Flask)
     ↓                          ↓
Netlify/Render    ←→    Render.com
     ↓                          ↓
Static Files              Python + AI Services
```

## 📋 Prerequisites

- GitHub account
- Render.com account
- Netlify account (optional, can use Render for both)
- Gemini API key (optional, for AI features)

## 🔧 Backend Deployment (Render.com)

### Step 1: Prepare Repository
1. Push your code to GitHub
2. Ensure all files are committed including:
   - `app.py`
   - `requirements.txt`
   - `render.yaml`
   - All Python modules

### Step 2: Deploy to Render
1. Go to [Render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `slide-extractor-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300`

### Step 3: Environment Variables
Set these in Render dashboard:
```
ENVIRONMENT=production
PYTHON_VERSION=3.11.0
GEMINI_API_KEY=your_gemini_api_key_here
CORS_ALLOWED_ORIGINS=https://slide-extractor-frontend.onrender.com,https://your-netlify-app.netlify.app
```

### Step 4: System Dependencies
Render will automatically install:
- Tesseract OCR
- FFmpeg
- Python dependencies

## 🎨 Frontend Deployment

### Option A: Netlify (Recommended)

1. Go to [Netlify](https://netlify.com)
2. Click "New site from Git"
3. Connect GitHub and select your repository
4. Configure:
   - **Base directory**: `frontend`
   - **Build command**: `npm run build`
   - **Publish directory**: `frontend/build`
5. Set environment variable:
   - `REACT_APP_API_URL`: `https://your-render-app.onrender.com`

### Option B: Render Static Site

1. In Render dashboard, click "New +" → "Static Site"
2. Connect your repository
3. Configure:
   - **Name**: `slide-extractor-frontend`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/build`

## 🔗 Integration Steps

### 1. Update CORS Settings
After deploying frontend, update backend CORS in `cors_config.py`:
```python
allowed_origins = [
    'https://your-frontend-url.netlify.app',
    'https://your-frontend-url.onrender.com',
    # Add your actual frontend URLs
]
```

### 2. Update Frontend API URL
In `frontend/src/App.js`, ensure:
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://your-backend-url.onrender.com';
```

### 3. Test Integration
1. Open your frontend URL
2. Check API status indicator
3. Test slide extraction with a YouTube URL
4. Verify file downloads work

## 🔧 Configuration Files

### Backend (`render.yaml`)
```yaml
services:
  - type: web
    name: slide-extractor-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300
```

### Frontend (`netlify.toml`)
```toml
[build]
  publish = "build"
  command = "npm run build"

[build.environment]
  REACT_APP_API_URL = "https://slide-extractor-api.onrender.com"
```

## 🚀 Deployment URLs

After successful deployment:
- **Backend API**: `https://slide-extractor-api.onrender.com`
- **Frontend**: `https://slide-extractor-frontend.netlify.app`

## 🔍 Testing Checklist

- [ ] Backend API responds at `/api/status`
- [ ] Frontend loads without errors
- [ ] API status shows "Online" in frontend
- [ ] Video URL input accepts YouTube links
- [ ] Extraction starts and shows progress
- [ ] PDF download works
- [ ] Study guide generation works
- [ ] CORS allows frontend-backend communication

## 🛠 Troubleshooting

### Common Issues:

1. **CORS Errors**
   - Update `CORS_ALLOWED_ORIGINS` environment variable
   - Include both HTTP and HTTPS versions

2. **API Timeout**
   - Increase timeout in gunicorn command
   - Use fewer workers for memory-intensive tasks

3. **Build Failures**
   - Check Python version compatibility
   - Ensure all dependencies in requirements.txt

4. **Frontend API Connection**
   - Verify `REACT_APP_API_URL` environment variable
   - Check network tab for failed requests

## 📊 Monitoring

- **Render Logs**: Monitor backend performance and errors
- **Netlify Analytics**: Track frontend usage
- **API Health**: Use `/api/status` endpoint for monitoring

## 🔄 Updates

To update the deployment:
1. Push changes to GitHub
2. Render will auto-deploy backend changes
3. Netlify will auto-deploy frontend changes
4. Monitor logs for any issues

## 💡 Optimization Tips

1. **Backend Performance**:
   - Use Redis for job caching in production
   - Implement rate limiting
   - Add database for persistent storage

2. **Frontend Performance**:
   - Enable gzip compression
   - Use CDN for static assets
   - Implement service worker for offline support

3. **Security**:
   - Add API authentication
   - Implement request validation
   - Use HTTPS everywhere
