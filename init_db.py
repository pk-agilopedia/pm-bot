#!/usr/bin/env python3
"""
Database initialization script for PM Bot API
"""

from app import create_app, db
from app.models import Tenant, User, Project

def init_database():
    """Initialize database and create sample data"""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Check if sample data already exists
        existing_tenant = Tenant.query.filter_by(slug='demo').first()
        if existing_tenant:
            print("✅ Sample data already exists!")
            return
        
        # Create sample tenant
        tenant = Tenant(
            name='Demo Company',
            slug='demo',
            description='Demo tenant for testing',
            is_active=True
        )
        db.session.add(tenant)
        db.session.commit()
        print("✅ Demo tenant created!")
        
        # Create sample user
        user = User(
            tenant_id=tenant.id,
            username='admin',
            email='admin@demo.com',
            first_name='Admin',
            last_name='User',
            is_active=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        print("✅ Admin user created!")
        
        # Create sample project
        project = Project(
            tenant_id=tenant.id,
            name='Sample Project',
            key='SAMPLE',
            description='A sample project for testing',
            manager_id=user.id,
            is_active=True
        )
        db.session.add(project)
        db.session.commit()
        print("✅ Sample project created!")
        
        print("\n🎉 Database initialization complete!")
        print(f"📋 Login credentials:")
        print(f"   Username: admin")
        print(f"   Password: password123")
        print(f"   Tenant: demo")

if __name__ == '__main__':
    init_database() 