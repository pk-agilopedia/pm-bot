#!/usr/bin/env python3
"""
Minimal working Flask app for debugging
Replace your app.py with this temporarily
"""

import os
from flask import Flask, jsonify, request

# Create Flask app
app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///pm_bot_db.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.route('/')
def home():
    """Home route - basic health check"""
    return jsonify({
        'message': 'PM Bot API is running!',
        'status': 'OK',
        'environment': os.environ.get('ENVIRONMENT', 'not-set'),
        'database_url': app.config.get('SQLALCHEMY_DATABASE_URI'),
        'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        'working_directory': os.getcwd(),
        'environment_vars': {
            'ENVIRONMENT': os.environ.get('ENVIRONMENT'),
            'SECRET_KEY': 'Set' if os.environ.get('SECRET_KEY') else 'Not set',
            'DATABASE_URL': 'Set' if os.environ.get('DATABASE_URL') else 'Not set',
            'PYTHONPATH': os.environ.get('PYTHONPATH'),
            'PORT': os.environ.get('PORT')
        }
    })

@app.route('/test')
def test():
    """Test route"""
    return jsonify({
        'message': 'Test route working!',
        'method': request.method,
        'path': request.path
    })

@app.route('/files')
def check_files():
    """Check what files are present"""
    try:
        files = []
        for root, dirs, file_list in os.walk('.'):
            for file in file_list:
                if file.endswith(('.py', '.txt', '.yml', '.yaml')):
                    files.append(os.path.join(root, file))
        
        return jsonify({
            'current_directory': os.getcwd(),
            'python_files': [f for f in files if f.endswith('.py')],
            'config_files': [f for f in files if f.endswith(('.txt', '.yml', '.yaml'))],
            'total_files': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/auth/test', methods=['GET', 'POST'])
def auth_test():
    """Test auth endpoint"""
    return jsonify({
        'message': 'Auth test endpoint working!',
        'method': request.method,
        'content_type': request.content_type,
        'has_json': request.is_json,
        'data': request.get_json() if request.is_json else None
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Not found',
        'message': 'The requested URL was not found',
        'available_routes': [str(rule) for rule in app.url_map.iter_rules()]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An internal error occurred',
        'details': str(error)
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)