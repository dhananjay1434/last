#!/usr/bin/env python3
"""
Smart startup script for Slide Extractor
Automatically detects available services and configures the app accordingly
"""

import os
import sys
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_redis():
    """Check Redis availability"""
    try:
        import redis
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        client = redis.from_url(redis_url, socket_timeout=3)
        client.ping()
        return True
    except:
        return False

def check_database():
    """Check database availability"""
    try:
        # Try to import SQLAlchemy and test connection
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        
        app = Flask(__name__)
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///slide_extractor.db')
        if database_url and database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db = SQLAlchemy(app)
        
        with app.app_context():
            db.engine.execute('SELECT 1')
        
        return True
    except:
        return False

def setup_environment():
    """Setup environment variables based on available services"""
    logger.info("🔍 Checking available services...")
    
    # Check services
    redis_available = check_redis()
    db_available = check_database()
    
    logger.info(f"Redis: {'✅ Available' if redis_available else '❌ Not available'}")
    logger.info(f"Database: {'✅ Available' if db_available else '❌ Not available'}")
    
    # Set environment variables
    env_config = {
        'USE_CELERY': 'true' if redis_available else 'false',
        'USE_REDIS': 'true' if redis_available else 'false',
        'ENVIRONMENT': os.environ.get('ENVIRONMENT', 'production'),
        'FLASK_APP': 'app.py'
    }
    
    # Apply configuration
    for key, value in env_config.items():
        os.environ[key] = value
        logger.info(f"Set {key}={value}")
    
    # Log configuration summary
    if redis_available:
        logger.info("🚀 Full-featured mode: Redis + Celery enabled")
    else:
        logger.info("🔧 Simplified mode: Using threading + database only")
        logger.info("   This mode is more reliable for deployment platforms")
    
    return env_config

def start_application():
    """Start the Flask application"""
    try:
        logger.info("🚀 Starting Slide Extractor application...")
        
        # Setup environment
        config = setup_environment()
        
        # Import and run the app
        from app import app, create_tables
        
        # Ensure database tables exist
        try:
            create_tables()
            logger.info("✅ Database tables ready")
        except Exception as e:
            logger.warning(f"Database setup warning: {e}")
        
        # Get port and host
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', '0.0.0.0')
        debug = os.environ.get('ENVIRONMENT', 'production').lower() != 'production'
        
        logger.info(f"🌐 Starting server on {host}:{port}")
        logger.info(f"🔧 Debug mode: {debug}")
        
        # Start the application
        app.run(host=host, port=port, debug=debug)
        
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_application()
