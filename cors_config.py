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
            # Add your production frontend URLs here
            'https://your-netlify-app.netlify.app',
            'https://your-render-app.onrender.com',
            # You can add more domains if needed
        ]
        
        # If CORS_ORIGINS is set in environment variables, use that instead
        if os.environ.get('CORS_ORIGINS'):
            allowed_origins = os.environ.get('CORS_ORIGINS').split(',')
        
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
