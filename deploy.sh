#!/bin/bash

# Slide Extractor Deployment Script
echo "🚀 Slide Extractor Deployment Helper"
echo "======================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: Slide Extractor with React frontend"
fi

# Check for GitHub remote
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "⚠️  No GitHub remote found."
    echo "Please create a GitHub repository and add it as origin:"
    echo "git remote add origin https://github.com/yourusername/slide-extractor.git"
    echo "git push -u origin main"
    exit 1
fi

echo "✅ Git repository ready"

# Create .env.example for backend
cat > .env.example << EOF
# Backend Environment Variables
GEMINI_API_KEY=your_gemini_api_key_here
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://your-frontend-url.netlify.app,https://your-frontend-url.onrender.com
EOF

# Create frontend .env.example
cat > frontend/.env.example << EOF
# Frontend Environment Variables
REACT_APP_API_URL=https://your-backend-url.onrender.com
EOF

echo "📝 Created environment variable examples"

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Build frontend locally to test
echo "🔨 Testing frontend build..."
cd frontend
npm run build
if [ $? -eq 0 ]; then
    echo "✅ Frontend build successful"
else
    echo "❌ Frontend build failed"
    exit 1
fi
cd ..

# Test backend locally
echo "🧪 Testing backend..."
python -c "
import sys
try:
    from app import app
    print('✅ Backend imports successful')
except ImportError as e:
    print(f'❌ Backend import failed: {e}')
    sys.exit(1)
"

echo ""
echo "🎉 Pre-deployment checks complete!"
echo ""
echo "Next steps:"
echo "1. Push to GitHub: git push origin main"
echo "2. Deploy backend to Render.com"
echo "3. Deploy frontend to Netlify"
echo "4. Update environment variables"
echo ""
echo "See DEPLOYMENT.md for detailed instructions"
