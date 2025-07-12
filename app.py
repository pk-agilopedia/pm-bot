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

@app.shell_context_processor
def make_shell_context():
    """Shell context for flask shell"""
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

@app.cli.command()
def init_db():
    """Initialize the database with tables"""
    db.create_all()
    print('Database initialized!')

@app.cli.command()
def create_sample_data():
    """Create sample data for development"""
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
    
    print('Sample data created!')
    print(f'Tenant: {tenant.name} (slug: {tenant.slug})')
    print(f'User: {user.username} / password123')
    print(f'Project: {project.name} ({project.key})')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 