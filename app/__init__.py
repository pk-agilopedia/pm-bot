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

    # Register shell context processor
    @app.shell_context_processor
    def make_shell_context():
        """Shell context for flask shell"""
        from app.models import (User, Tenant, Project, Tool, ProjectTool, 
                               ChatSession, ChatMessage, TokenUsage, APIUsage, 
                               AgentExecution, SystemConfig, ModelPricing)
        return {
            'db': db, 
            'User': User, 
            'Tenant': Tenant,
            'Project': Project,
            'Tool': Tool,
            'ProjectTool': ProjectTool,
            'ChatSession': ChatSession,
            'ChatMessage': ChatMessage,
            'TokenUsage': TokenUsage,
            'APIUsage': APIUsage,
            'AgentExecution': AgentExecution,
            'SystemConfig': SystemConfig,
            'ModelPricing': ModelPricing
        }

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

def register_cli_commands(app):
    """Register CLI commands with the Flask app"""
    
    @app.cli.command()
    def init_db():
        """Initialize the database with tables"""
        db.create_all()
        print('✅ Database initialized!')

    @app.cli.command()
    def create_sample_data():
        """Create sample data for development"""
        from app.models import User, Tenant, Project
        
        # Create sample tenant
        tenant = Tenant(
            name='Demo Company',
            slug='demo',
            description='Demo tenant for testing'
        )
        db.session.add(tenant)
        db.session.commit()
        
        # Create sample user
        user = User(
            tenant_id=tenant.id,
            username='admin',
            email='admin@demo.com',
            first_name='Admin',
            last_name='User'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Create sample project
        project = Project(
            tenant_id=tenant.id,
            name='Sample Project',
            key='SAMPLE',
            description='A sample project for testing',
            manager_id=user.id
        )
        db.session.add(project)
        db.session.commit()
        
        print('✅ Sample data created!')
        print(f'Tenant: {tenant.name} (slug: {tenant.slug})')
        print(f'User: {user.username} / password123')
        print(f'Project: {project.name} ({project.key})')

# Create and configure app instance for CLI commands
def create_cli_app():
    """Create app instance specifically for CLI operations"""
    env = os.environ.get('ENVIRONMENT', 'development')
    config_class = config.get(env, config['default'])
    app = create_app(config_class)
    register_cli_commands(app)
    return app

# Import models at the end
from app import models