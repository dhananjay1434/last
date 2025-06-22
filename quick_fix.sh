#!/bin/bash

# Quick Fix Script for Slide Extractor Deployment Issues
# This script addresses the immediate issues seen in the logs

echo "🔧 Quick Fix for Slide Extractor Deployment"
echo "============================================"

# Set environment variables for simplified deployment
export USE_CELERY=false
export USE_REDIS=false
export ENVIRONMENT=production

echo "✅ Environment variables set for simplified deployment"

# Update yt-dlp to latest version
echo "📦 Updating yt-dlp..."
pip install --upgrade yt-dlp

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p slides logs temp

# Run the deployment hotfix
echo "🚀 Running deployment hotfix..."
python deployment_hotfix.py

# Test the application
echo "🧪 Testing application..."
python -c "
import sys
sys.path.insert(0, '.')
try:
    from app import app
    print('✅ Application imports successfully')
    with app.test_client() as client:
        response = client.get('/api/status')
        if response.status_code == 200:
            print('✅ API status endpoint working')
        else:
            print(f'❌ API status failed: {response.status_code}')
except Exception as e:
    print(f'❌ Application test failed: {e}')
"

echo "🎉 Quick fix completed!"
echo ""
echo "📋 Summary of changes:"
echo "  - Disabled Celery and Redis for simplified deployment"
echo "  - Updated yt-dlp to latest version"
echo "  - Created necessary directories"
echo "  - Applied deployment hotfixes"
echo ""
echo "🚀 The application should now work in simplified mode"
echo "   (using threading instead of Celery for background jobs)"
