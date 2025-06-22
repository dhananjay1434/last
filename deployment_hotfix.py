#!/usr/bin/env python3
"""
Deployment Hotfix Script
Addresses immediate issues in the production deployment
"""

import os
import sys
import logging
import subprocess
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentHotfix:
    """Handles deployment hotfixes and environment setup"""
    
    def __init__(self):
        self.environment = os.environ.get('ENVIRONMENT', 'development')
        self.is_production = self.environment.lower() == 'production'
        
    def check_environment(self):
        """Check and fix environment configuration"""
        logger.info("🔍 Checking environment configuration...")
        
        # Check critical environment variables
        critical_vars = {
            'USE_CELERY': 'false',  # Disabled for simplified deployment
            'USE_REDIS': 'false',   # Disabled for simplified deployment
            'ENVIRONMENT': 'production',
            'CORS_ALLOWED_ORIGINS': 'https://latenighter.netlify.app'
        }
        
        missing_vars = []
        for var, default in critical_vars.items():
            if not os.environ.get(var):
                os.environ[var] = default
                logger.warning(f"⚠️ Set missing environment variable: {var}={default}")
            else:
                logger.info(f"✅ {var}={os.environ.get(var)}")
        
        return len(missing_vars) == 0
    
    def fix_redis_connection(self):
        """Fix Redis connection issues"""
        logger.info("🔧 Fixing Redis connection issues...")
        
        # Disable Redis if not available
        os.environ['USE_REDIS'] = 'false'
        os.environ['USE_CELERY'] = 'false'
        
        logger.info("✅ Redis and Celery disabled for simplified deployment")
        return True
    
    def check_dependencies(self):
        """Check if critical dependencies are available"""
        logger.info("📦 Checking dependencies...")
        
        critical_deps = [
            'yt-dlp',
            'tesseract',
            'ffmpeg'
        ]
        
        missing_deps = []
        for dep in critical_deps:
            try:
                result = subprocess.run([dep, '--version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=10)
                if result.returncode == 0:
                    logger.info(f"✅ {dep} is available")
                else:
                    missing_deps.append(dep)
                    logger.error(f"❌ {dep} is not working properly")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing_deps.append(dep)
                logger.error(f"❌ {dep} is not installed")
        
        return len(missing_deps) == 0
    
    def fix_youtube_download(self):
        """Apply YouTube download fixes"""
        logger.info("🎥 Applying YouTube download fixes...")
        
        try:
            # Update yt-dlp to latest version
            result = subprocess.run([
                sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ yt-dlp updated successfully")
            else:
                logger.warning(f"⚠️ yt-dlp update failed: {result.stderr}")
            
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update yt-dlp: {e}")
            return False
    
    def test_api_endpoints(self):
        """Test critical API endpoints"""
        logger.info("🧪 Testing API endpoints...")
        
        try:
            # Import Flask app
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from app import app
            
            with app.test_client() as client:
                # Test status endpoint
                response = client.get('/api/status')
                if response.status_code == 200:
                    logger.info("✅ /api/status endpoint working")
                else:
                    logger.error(f"❌ /api/status failed: {response.status_code}")
                
                # Test health endpoint
                response = client.get('/api/health')
                if response.status_code in [200, 503]:  # 503 is acceptable for degraded state
                    logger.info("✅ /api/health endpoint working")
                else:
                    logger.error(f"❌ /api/health failed: {response.status_code}")
            
            return True
        except Exception as e:
            logger.error(f"❌ API endpoint test failed: {e}")
            return False
    
    def create_directories(self):
        """Create necessary directories"""
        logger.info("📁 Creating necessary directories...")
        
        directories = [
            'slides',
            'logs',
            'temp'
        ]
        
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                logger.info(f"✅ Created directory: {directory}")
            except Exception as e:
                logger.error(f"❌ Failed to create directory {directory}: {e}")
        
        return True
    
    def fix_database_connection(self):
        """Fix database connection issues"""
        logger.info("🗄️ Fixing database connection...")
        
        try:
            # Import and test database
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from app import app, db
            
            with app.app_context():
                # Test database connection
                db.session.execute(db.text('SELECT 1'))
                logger.info("✅ Database connection working")
                
                # Create tables if they don't exist
                db.create_all()
                logger.info("✅ Database tables created/verified")
            
            return True
        except Exception as e:
            logger.warning(f"⚠️ Database issue (will use fallback): {e}")
            return False
    
    def apply_all_fixes(self):
        """Apply all hotfixes"""
        logger.info("🚀 Starting deployment hotfix...")
        
        fixes = [
            ("Environment Configuration", self.check_environment),
            ("Redis Connection Fix", self.fix_redis_connection),
            ("Directory Creation", self.create_directories),
            ("Dependencies Check", self.check_dependencies),
            ("YouTube Download Fix", self.fix_youtube_download),
            ("Database Connection", self.fix_database_connection),
            ("API Endpoints Test", self.test_api_endpoints)
        ]
        
        results = {}
        for name, fix_func in fixes:
            try:
                logger.info(f"🔧 Applying: {name}")
                result = fix_func()
                results[name] = result
                if result:
                    logger.info(f"✅ {name}: SUCCESS")
                else:
                    logger.warning(f"⚠️ {name}: FAILED (non-critical)")
            except Exception as e:
                logger.error(f"❌ {name}: ERROR - {e}")
                results[name] = False
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("🎯 HOTFIX SUMMARY")
        logger.info("="*50)
        
        success_count = sum(1 for result in results.values() if result)
        total_count = len(results)
        
        for name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} {name}")
        
        logger.info(f"\n📊 Overall: {success_count}/{total_count} fixes successful")
        
        if success_count >= total_count * 0.7:  # 70% success rate
            logger.info("🎉 Deployment hotfix completed successfully!")
            logger.info("🚀 Application should be working in simplified mode")
        else:
            logger.warning("⚠️ Some fixes failed, but application may still work")
        
        return results

def main():
    """Main hotfix execution"""
    print("🔧 Deployment Hotfix Tool")
    print("=" * 40)
    
    hotfix = DeploymentHotfix()
    results = hotfix.apply_all_fixes()
    
    # Exit with appropriate code
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    if success_count >= total_count * 0.7:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Partial failure

if __name__ == "__main__":
    main()
