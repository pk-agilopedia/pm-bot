#!/usr/bin/env python3
"""
Robust WSGI file for Azure deployment
"""

import os
import sys

# Ensure we can find our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set PORT environment variable if not set (Azure sets this automatically)
if 'PORT' not in os.environ:
    os.environ['PORT'] = '8000'

try:
    # Try to import the app from app.py
    from app import app
    print(f"✓ Successfully imported app from app.py")
    
    # Ensure the app is properly configured
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
    
    print(f"✓ App configured successfully")
    print(f"✓ Environment: {os.environ.get('ENVIRONMENT', 'not-set')}")
    print(f"✓ Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI', 'not-set')}")
    
except Exception as e:
    print(f"✗ Error importing app: {e}")
    
    # Create a minimal Flask app as fallback
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-key')
    
    @app.route('/')
    def home():
        return jsonify({
            'message': 'PM Bot API - Fallback Mode',
            'status': 'Running in fallback mode',
            'error': str(e),
            'current_directory': os.getcwd(),
            'files_present': [f for f in os.listdir('.') if f.endswith('.py')],
            'environment_vars': {
                'ENVIRONMENT': os.environ.get('ENVIRONMENT'),
                'PYTHONPATH': os.environ.get('PYTHONPATH'),
                'PORT': os.environ.get('PORT')
            }
        })
    
    print(f"✓ Fallback app created")

if __name__ == "__main__":
    # For direct execution (when using: python wsgi.py)
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)