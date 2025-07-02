from flask import request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app.auth import bp
from app.models import User, Tenant, db
from datetime import datetime, timedelta
import re

# Simple JWT blacklist (in production, use Redis or database)
blacklisted_tokens = set()

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
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
            return jsonify({'error': 'Invalid tenant'}), 400
        
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
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 24))
        )
        
        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role.value,
                'tenant': {
                    'id': tenant.id,
                    'name': tenant.name,
                    'slug': tenant.slug
                }
            },
            'access_token': access_token
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
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
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 24))
        )
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role.value,
                'tenant': {
                    'id': user.tenant.id,
                    'name': user.tenant.name,
                    'slug': user.tenant.slug
                }
            },
            'access_token': access_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user by blacklisting the token"""
    try:
        jti = get_jwt()['jti']  # JWT ID
        blacklisted_tokens.add(jti)
        
        return jsonify({'message': 'Successfully logged out'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role.value,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'tenant': {
                    'id': user.tenant.id,
                    'name': user.tenant.name,
                    'slug': user.tenant.slug
                }
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get current user error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    """Refresh the access token"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User not found or inactive'}), 404
        
        # Generate new access token
        access_token = create_access_token(
            identity=user.id,
            expires_delta=timedelta(hours=current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', 24))
        )
        
        return jsonify({
            'access_token': access_token
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Validate new password strength
        if len(new_password) < 8:
            return jsonify({'error': 'New password must be at least 8 characters'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Change password error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# JWT token checker to handle blacklisted tokens
@bp.before_app_request
def check_if_token_revoked():
    """Check if JWT token is blacklisted"""
    try:
        jti = get_jwt().get('jti')
        if jti in blacklisted_tokens:
            return jsonify({'error': 'Token has been revoked'}), 401
    except:
        pass  # No JWT token in request 