#!/usr/bin/env python3

import os
import sys

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app import create_app
from config import config

env = os.environ.get('ENVIRONMENT', 'development')
config_class = config.get(env, config['default'])

app = create_app(config_class)

print(f"✓ Successfully created Flask app using factory pattern")
print(f"✓ Environment: {env}")
print(f"✓ Config class: {config_class.__name__}")
print(f"✓ Database configured: {bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}")

# WRAP FLASK AS ASGI
from asgiref.wsgi import WsgiToAsgi

asgi_app = WsgiToAsgi(app)
