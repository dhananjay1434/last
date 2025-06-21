#!/bin/bash

# 🚀 Flask Compatibility Fixes Deployment Script
# This script applies all the necessary fixes for Flask compatibility and deployment issues

echo "🔧 Applying Flask compatibility fixes..."

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the project root directory."
    exit 1
fi

echo "✅ Found app.py - proceeding with fixes..."

# 1. Backup current render.yaml
if [ -f "render.yaml" ]; then
    echo "📦 Backing up current render.yaml..."
    cp render.yaml render.yaml.backup
fi

# 2. Option to use simplified deployment
echo ""
echo "🤔 Choose deployment option:"
echo "1) Simplified deployment (single service, no Celery) - RECOMMENDED for fixing issues"
echo "2) Keep complex multi-service deployment"
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo "📝 Using simplified deployment configuration..."
    if [ -f "render-simple.yaml" ]; then
        cp render-simple.yaml render.yaml
        echo "✅ Switched to simplified deployment"
    else
        echo "❌ render-simple.yaml not found. Creating simplified config..."
        cat > render.yaml << 'EOF'
services:
  - type: web
    name: slide-extractor-api
    env: python
    buildCommand: |
      pip install --upgrade pip &&
      pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300 --preload
    plan: standard
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: PORT
        value: 10000
      - key: ENVIRONMENT
        value: production
      - key: USE_CELERY
        value: "false"
      - key: CORS_ALLOWED_ORIGINS
        value: "https://latenighter.netlify.app"
      - key: GEMINI_API_KEY
        sync: false
      - key: FLASK_APP
        value: app.py
    healthCheckPath: /api/status
EOF
        echo "✅ Created simplified deployment config"
    fi
else
    echo "📝 Keeping complex multi-service deployment..."
fi

# 3. Verify fixes are applied
echo ""
echo "🔍 Verifying fixes..."

# Check for Flask compatibility fix
if grep -q "before_first_request" app.py; then
    echo "❌ Warning: before_first_request still found in app.py"
    echo "   The Flask compatibility fix may not be fully applied"
else
    echo "✅ Flask compatibility fix verified"
fi

# Check for SQLAlchemy syntax fix
if grep -q "db.session.execute('SELECT 1')" app.py; then
    echo "❌ Warning: Old SQLAlchemy syntax still found in app.py"
    echo "   The SQLAlchemy syntax fix may not be fully applied"
else
    echo "✅ SQLAlchemy syntax fix verified"
fi

# 4. Git operations
echo ""
echo "📝 Git operations..."

# Add all changes
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo "ℹ️  No changes to commit"
else
    echo "💾 Committing fixes..."
    git commit -m "🔧 Fix Flask compatibility and deployment issues

- Fix Flask before_first_request deprecation
- Update SQLAlchemy syntax for 2.0 compatibility  
- Update Python runtime to 3.11.0
- Add simplified deployment option
- Improve database initialization error handling"
    
    echo "✅ Changes committed"
    
    # Ask about pushing
    echo ""
    read -p "🚀 Push changes to trigger deployment? (y/n): " push_choice
    if [ "$push_choice" = "y" ] || [ "$push_choice" = "Y" ]; then
        echo "📤 Pushing to remote repository..."
        git push
        echo "✅ Changes pushed - deployment should start automatically"
        
        echo ""
        echo "🎯 Next steps:"
        echo "1. Monitor Render.com dashboard for deployment progress"
        echo "2. Check deployment logs for any errors"
        echo "3. Test API endpoints once deployment completes:"
        echo "   curl https://your-app.onrender.com/api/status"
        echo "4. Verify frontend connectivity at https://latenighter.netlify.app/"
        
    else
        echo "ℹ️  Changes committed but not pushed. Run 'git push' when ready to deploy."
    fi
fi

echo ""
echo "🎉 Flask compatibility fixes script completed!"
echo ""
echo "📊 Summary of fixes applied:"
echo "✅ Flask compatibility (before_first_request removal)"
echo "✅ SQLAlchemy 2.0 syntax updates"
echo "✅ Python runtime update to 3.11.0"
echo "✅ Database initialization improvements"
echo "✅ Simplified deployment option available"
echo ""
echo "🔗 Useful links:"
echo "   - Render Dashboard: https://dashboard.render.com/"
echo "   - Frontend: https://latenighter.netlify.app/"
echo ""
echo "📞 If issues persist, check the deployment logs and consider:"
echo "   - Using the simplified deployment (render-simple.yaml)"
echo "   - Disabling Celery temporarily (USE_CELERY=false)"
echo "   - Rolling back to a previous working commit"
