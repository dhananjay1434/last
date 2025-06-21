"""
CORS configuration for the Slide Extractor API
This file should be imported in your Flask application
"""

from flask_cors import CORS
import os

def configure_cors(app):
    """
    Configure CORS for the Flask application
    
    Args:
        app: Flask application instance
    """
    # Get environment
    environment = os.environ.get('ENVIRONMENT', 'development')
    
    # Configure CORS based on environment
    if environment == 'production':
        # In production, only allow requests from your frontend domains
        allowed_origins = [
            # Production frontend URLs
            'https://latenighter.netlify.app',
            'https://slide-extractor-frontend.onrender.com',
            'https://slide-extractor.netlify.app',
            # Development URLs
            'http://localhost:3000',
            'http://localhost:5173',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5173',
            # Gradio URLs
            'https://*.gradio.live'
        ]
        
        # If CORS_ALLOWED_ORIGINS is set in environment variables, use that instead
        if os.environ.get('CORS_ALLOWED_ORIGINS'):
            cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS')
            # Handle both comma-separated and single origin
            if ',' in cors_origins:
                allowed_origins = [origin.strip() for origin in cors_origins.split(',')]
            else:
                allowed_origins = [cors_origins.strip()]
        
        CORS(app, resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        })
    else:
        # In development, allow all origins
        CORS(app)
    
    return app
