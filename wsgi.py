#!/usr/bin/env python3
"""
WSGI file for original Flask app structure
"""

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Set PORT environment variable if not set
if 'PORT' not in os.environ:
    os.environ['PORT'] = '8000'

try:
    # Import the Flask app instance from app.py
    from app import app
    print(f"✓ Successfully imported app from app.py")
    
    # Verify app configuration
    print(f"✓ Environment: {os.environ.get('ENVIRONMENT', 'not-set')}")
    print(f"✓ Database configured: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")
    
except Exception as e:
    print(f"✗ Error importing app: {e}")
    
    # Create emergency fallback
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    
    @app.route('/')
    def emergency():
        return jsonify({
            'message': 'Emergency mode - Original app import failed',
            'error': str(e),
            'help': 'Check that app/__init__.py exists and create_app() function is defined',
            'files_present': [f for f in os.listdir('.') if f.endswith('.py')],
            'app_folder_exists': os.path.exists('app'),
            'config_exists': os.path.exists('config.py')
        })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)