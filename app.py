#!/usr/bin/env python3
"""
PM Bot API - Project Management AI Agent Backend
Main application entry point
"""

import os
from app import create_app, db
from app.models import *
from flask_migrate import Migrate
from config import config

# Get environment
env = os.environ.get('ENVIRONMENT', 'development')
config_class = config.get(env, config['default'])

# Create Flask app
app = create_app(config_class)
migrate = Migrate(app, db)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)