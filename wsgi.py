#!/usr/bin/env python3
"""
WSGI file for Flask factory pattern
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
    # Import create_app factory and config
    from app import create_app
    from config import config
    
    # Get environment and config class
    env = os.environ.get('ENVIRONMENT', 'development')
    config_class = config.get(env, config['default'])
    
    # Create the Flask app instance
    app = create_app(config_class)
    
    print(f"✓ Successfully created Flask app using factory pattern")
    print(f"✓ Environment: {env}")
    print(f"✓ Config class: {config_class.__name__}")
    print(f"✓ Database configured: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")
    
except Exception as e:
    print(f"✗ Error creating Flask app: {e}")
    
    # Create emergency fallback
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    
    @app.route('/')
    def emergency():
        return jsonify({
            'message': 'Emergency mode - Flask factory import failed',
            'error': str(e),
            'help': 'Check that app/__init__.py exports create_app function',
            'files_present': [f for f in os.listdir('.') if f.endswith('.py')],
            'app_folder_exists': os.path.exists('app'),
            'config_exists': os.path.exists('config.py'),
            'working_directory': os.getcwd()
        })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)