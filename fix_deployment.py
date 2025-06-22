#!/usr/bin/env python3
"""
Deployment fix script for Slide Extractor
Handles Redis connection issues and improves YouTube download reliability
"""

import os
import sys
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_redis_availability():
    """Check if Redis is available and running"""
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        client = redis.from_url(redis_url, socket_timeout=5)
        client.ping()
        logger.info("✅ Redis is available and running")
        return True
    except Exception as e:
        logger.warning(f"❌ Redis not available: {e}")
        return False

def set_environment_variables():
    """Set appropriate environment variables for deployment"""
    redis_available = check_redis_availability()
    
    # Set environment variables based on Redis availability
    env_vars = {
        'USE_CELERY': 'true' if redis_available else 'false',
        'USE_REDIS': 'true' if redis_available else 'false',
        'ENVIRONMENT': 'production',
        'FLASK_APP': 'app.py'
    }
    
    # Update environment
    for key, value in env_vars.items():
        os.environ[key] = value
        logger.info(f"Set {key}={value}")
    
    return env_vars

def install_dependencies():
    """Install required dependencies"""
    try:
        logger.info("Installing/updating dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        logger.info("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to install dependencies: {e}")
        return False

def test_youtube_download():
    """Test YouTube download functionality"""
    try:
        logger.info("Testing YouTube download capabilities...")
        
        # Test basic yt-dlp
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info(f"✅ yt-dlp available: {result.stdout.strip()}")
        else:
            logger.warning("❌ yt-dlp not available")
        
        # Test robust downloader
        try:
            from robust_youtube_downloader import RobustYouTubeDownloader
            logger.info("✅ Robust YouTube downloader available")
        except ImportError:
            logger.warning("❌ Robust YouTube downloader not available")
        
        return True
    except Exception as e:
        logger.error(f"❌ YouTube download test failed: {e}")
        return False

def create_render_config():
    """Create optimized render.yaml for deployment"""
    redis_available = check_redis_availability()
    
    render_config = f"""services:
  # Main API Service (Optimized)
  - type: web
    name: slide-extractor-api
    env: python
    buildCommand: |
      pip install --upgrade pip &&
      pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 600 --preload
    plan: standard
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: PORT
        value: 10000
      - key: ENVIRONMENT
        value: production
      - key: USE_CELERY
        value: "{'true' if redis_available else 'false'}"
      - key: USE_REDIS
        value: "{'true' if redis_available else 'false'}"
      - key: CORS_ALLOWED_ORIGINS
        value: "https://latenighter.netlify.app"
      - key: GEMINI_API_KEY
        sync: false  # Set manually in dashboard
      - key: MAX_CONTENT_LENGTH
        value: "104857600"  # 100MB
      - key: UPLOAD_TIMEOUT
        value: "600"  # 10 minutes
      - key: FLASK_APP
        value: app.py
    healthCheckPath: /api/status
"""
    
    if redis_available:
        render_config += """
  # Redis Service (if needed)
  - type: redis
    name: slide-extractor-redis
    plan: starter
    maxmemoryPolicy: allkeys-lru
"""
    
    with open('render-optimized.yaml', 'w') as f:
        f.write(render_config)
    
    logger.info("✅ Created optimized render-optimized.yaml")

def update_yt_dlp_version():
    """Update yt-dlp to the latest version"""
    try:
        logger.info("Updating yt-dlp to latest version...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'], check=True)
        logger.info("✅ yt-dlp updated successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to update yt-dlp: {e}")
        return False

def create_deployment_env_file():
    """Create .env file for deployment"""
    env_content = """# Deployment Environment Variables
USE_CELERY=false
USE_REDIS=false
ENVIRONMENT=production
FLASK_APP=app.py

# CORS Configuration
CORS_ALLOWED_ORIGINS=https://latenighter.netlify.app

# Optional: Set these in Render dashboard
# GEMINI_API_KEY=your_key_here
# DATABASE_URL=postgresql://...
"""

    try:
        with open('.env.deployment', 'w') as f:
            f.write(env_content)
        logger.info("✅ Created deployment environment file")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create env file: {e}")
        return False

def main():
    """Main deployment fix function"""
    logger.info("🚀 Starting deployment fix process...")

    # Step 1: Set environment variables
    env_vars = set_environment_variables()

    # Step 2: Update yt-dlp
    update_yt_dlp_version()

    # Step 3: Install dependencies
    if not install_dependencies():
        logger.error("❌ Deployment fix failed: Could not install dependencies")
        return False

    # Step 4: Test YouTube download
    test_youtube_download()

    # Step 5: Create optimized config
    create_render_config()

    # Step 6: Create deployment env file
    create_deployment_env_file()

    # Step 7: Summary
    logger.info("🎉 Deployment fix completed!")
    logger.info("📋 Summary:")
    for key, value in env_vars.items():
        logger.info(f"  {key}: {value}")

    logger.info("\n📝 Next steps:")
    logger.info("1. Use 'render-optimized.yaml' for deployment")
    logger.info("2. Set GEMINI_API_KEY in Render dashboard if using AI features")
    logger.info("3. Monitor logs for any remaining issues")
    logger.info("4. Check .env.deployment for environment variables")

    if not env_vars['USE_REDIS'] == 'true':
        logger.info("⚠️  Note: Redis disabled - using database-only mode")
        logger.info("   This may impact performance but will work reliably")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
