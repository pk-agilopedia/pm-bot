import os
from app import create_app
from config import config

env = os.environ.get('ENVIRONMENT', 'development')
config_class = config.get(env, config['default'])

app = create_app(config_class)
