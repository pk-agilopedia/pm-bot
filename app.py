#!/usr/bin/env python3
"""
Enhanced Flask app with database support
"""

import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import re

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///pm_bot_db.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'fallback-jwt-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# Simple Models
class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationship
    tenant = db.relationship('Tenant', backref='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Routes
@app.route('/')
def home():
    """Home route - basic health check"""
    return jsonify({
        'message': 'PM Bot API is running!',
        'status': 'OK',
        'version': '2.0 - With Database Support',
        'environment': os.environ.get('ENVIRONMENT', 'not-set'),
        'database_url': app.config.get('SQLALCHEMY_DATABASE_URI'),
        'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        'working_directory': os.getcwd(),
        'features': [
            'User Registration',
            'JWT Authentication', 
            'SQLite Database',
            'Multi-tenant Support'
        ]
    })

@app.route('/init-db')
def init_database():
    """Initialize database tables and create demo tenant"""
    try:
        # Create all tables
        db.create_all()
        
        # Check if demo tenant exists
        demo_tenant = Tenant.query.filter_by(slug='demo').first()
        if not demo_tenant:
            demo_tenant = Tenant(
                name='Demo Company',
                slug='demo',
                description='Demo tenant for testing',
                is_active=True
            )
            db.session.add(demo_tenant)
            db.session.commit()
        
        return jsonify({
            'message': 'Database initialized successfully!',
            'tables_created': True,
            'demo_tenant': {
                'id': demo_tenant.id,
                'name': demo_tenant.name,
                'slug': demo_tenant.slug
            },
            'database_file': app.config.get('SQLALCHEMY_DATABASE_URI')
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Database initialization failed',
            'details': str(e)
        }), 500

@app.route('/auth/register', methods=['POST'])
def register():
    """Real user registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate input
        required_fields = ['username', 'email', 'password', 'tenant_slug']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        username = data['username']
        email = data['email']
        password = data['password']
        tenant_slug = data['tenant_slug']
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        
        # Validate email format
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate password strength
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Check if tenant exists
        tenant = Tenant.query.filter_by(slug=tenant_slug, is_active=True).first()
        if not tenant:
            return jsonify({'error': 'Invalid tenant. Use /init-db to create demo tenant.'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Create new user
        user = User(
            tenant_id=tenant.id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Generate access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'slug': tenant.slug
                }
            },
            'access_token': access_token
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': 'Registration failed',
            'details': str(e)
        }), 500

@app.route('/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password are required'}), 400
        
        username = data['username']
        password = data['password']
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'tenant': {
                    'id': user.tenant.id,
                    'name': user.tenant.name,
                    'slug': user.tenant.slug
                }
            },
            'access_token': access_token
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Login failed',
            'details': str(e)
        }), 500

@app.route('/test')
def test():
    """Test route"""
    return jsonify({
        'message': 'Test route working!',
        'database_connected': True,
        'total_users': User.query.count(),
        'total_tenants': Tenant.query.count()
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
    app.run(host='0.0.0.0', port=port, debug=False)