from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config
import logging
from logging.handlers import RotatingFileHandler
import os

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_class=None):
    app = Flask(__name__)
    # Determine which config to use
    if config_class is None:
        env = os.environ.get('ENVIRONMENT', 'development')
        config_class = config[env]
    
    app.config.from_object(config_class)

    # Log the JIRA_SERVER_URL to verify it's loaded correctly
    app.logger.info(f"JIRA_SERVER_URL: {app.config.get('JIRA_SERVER_URL')}")

    # Initialize Flask extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)

    # Register Blueprints
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # Setup logging to stdout
    if not app.debug and not app.testing:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'))
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('PM Bot startup')

    # Register AI Agents
    with app.app_context():
        _register_agents()

    return app

def _register_agents():
    """Register all AI agents with the agent registry"""
    from app.agents.base import agent_registry
    from app.agents.main import MainAgent
    
    # Register only the main agent - it handles routing to specialized agents
    agent_registry.register_agent(MainAgent())

from app import models 