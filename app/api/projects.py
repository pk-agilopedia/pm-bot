from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api import bp
from app.models import User, Project, ProjectTool, Tool, Tenant, db
from datetime import datetime

@bp.route('/projects', methods=['GET'])
@jwt_required()
def get_projects():
    """Get all projects for the user's tenant"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get projects for the user's tenant
        projects = Project.query.filter_by(
            tenant_id=user.tenant_id,
            is_active=True
        ).order_by(Project.updated_at.desc()).all()
        
        project_list = []
        for project in projects:
            # Get connected tools
            project_tools = ProjectTool.query.filter_by(
                project_id=project.id,
                is_active=True
            ).all()
            
            tools = []
            for pt in project_tools:
                tools.append({
                    'id': pt.tool.id,
                    'name': pt.tool.name,
                    'type': pt.tool.tool_type.value,
                    'configuration': pt.configuration
                })
            
            project_data = {
                'id': project.id,
                'name': project.name,
                'key': project.key,
                'description': project.description,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'manager_id': project.manager_id,
                'manager_name': project.manager.username if project.manager else None,
                'tools': tools,
                'created_at': project.created_at.isoformat(),
                'updated_at': project.updated_at.isoformat()
            }
            project_list.append(project_data)
        
        return jsonify({
            'projects': project_list,
            'total_count': len(project_list)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting projects: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/projects', methods=['POST'])
@jwt_required()
def create_project():
    """Create a new project"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate input
        if not data.get('name'):
            return jsonify({'error': 'Project name is required'}), 400
        
        if not data.get('key'):
            return jsonify({'error': 'Project key is required'}), 400
        
        # Check if project key is unique within tenant
        existing_project = Project.query.filter_by(
            tenant_id=user.tenant_id,
            key=data['key']
        ).first()
        
        if existing_project:
            return jsonify({'error': 'Project key already exists'}), 400
        
        # Create project
        project = Project(
            tenant_id=user.tenant_id,
            name=data['name'],
            key=data['key'],
            description=data.get('description', ''),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
            manager_id=data.get('manager_id', user_id)
        )
        
        db.session.add(project)
        db.session.commit()
        
        return jsonify({
            'message': 'Project created successfully',
            'project': {
                'id': project.id,
                'name': project.name,
                'key': project.key,
                'description': project.description,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'manager_id': project.manager_id
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating project: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/projects/<int:project_id>', methods=['GET'])
@jwt_required()
def get_project(project_id):
    """Get a specific project"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        project = Project.query.filter_by(
            id=project_id,
            tenant_id=user.tenant_id
        ).first()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Get connected tools
        project_tools = ProjectTool.query.filter_by(
            project_id=project.id,
            is_active=True
        ).all()
        
        tools = []
        for pt in project_tools:
            tools.append({
                'id': pt.tool.id,
                'name': pt.tool.name,
                'type': pt.tool.tool_type.value,
                'base_url': pt.tool.base_url,
                'configuration': pt.configuration
            })
        
        project_data = {
            'id': project.id,
            'name': project.name,
            'key': project.key,
            'description': project.description,
            'start_date': project.start_date.isoformat() if project.start_date else None,
            'end_date': project.end_date.isoformat() if project.end_date else None,
            'manager_id': project.manager_id,
            'manager_name': project.manager.username if project.manager else None,
            'tools': tools,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat()
        }
        
        return jsonify({'project': project_data}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting project: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/projects/<int:project_id>', methods=['PUT'])
@jwt_required()
def update_project(project_id):
    """Update a project"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        project = Project.query.filter_by(
            id=project_id,
            tenant_id=user.tenant_id
        ).first()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        
        # Update project fields
        if 'name' in data:
            project.name = data['name']
        
        if 'description' in data:
            project.description = data['description']
        
        if 'start_date' in data:
            project.start_date = datetime.fromisoformat(data['start_date']) if data['start_date'] else None
        
        if 'end_date' in data:
            project.end_date = datetime.fromisoformat(data['end_date']) if data['end_date'] else None
        
        if 'manager_id' in data:
            project.manager_id = data['manager_id']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Project updated successfully',
            'project': {
                'id': project.id,
                'name': project.name,
                'key': project.key,
                'description': project.description,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None,
                'manager_id': project.manager_id
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating project: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/projects/<int:project_id>/tools', methods=['POST'])
@jwt_required()
def connect_tool_to_project(project_id):
    """Connect a tool to a project"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        project = Project.query.filter_by(
            id=project_id,
            tenant_id=user.tenant_id
        ).first()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        
        if not data.get('tool_id'):
            return jsonify({'error': 'Tool ID is required'}), 400
        
        tool = Tool.query.filter_by(
            id=data['tool_id'],
            tenant_id=user.tenant_id
        ).first()
        
        if not tool:
            return jsonify({'error': 'Tool not found'}), 404
        
        # Check if already connected
        existing_connection = ProjectTool.query.filter_by(
            project_id=project.id,
            tool_id=tool.id
        ).first()
        
        if existing_connection:
            existing_connection.is_active = True
            existing_connection.configuration = data.get('configuration', {})
        else:
            project_tool = ProjectTool(
                project_id=project.id,
                tool_id=tool.id,
                configuration=data.get('configuration', {}),
                is_active=True
            )
            db.session.add(project_tool)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Tool connected to project successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error connecting tool to project: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/projects/<int:project_id>/tools/<int:tool_id>', methods=['DELETE'])
@jwt_required()
def disconnect_tool_from_project(project_id, tool_id):
    """Disconnect a tool from a project"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        project = Project.query.filter_by(
            id=project_id,
            tenant_id=user.tenant_id
        ).first()
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        project_tool = ProjectTool.query.filter_by(
            project_id=project_id,
            tool_id=tool_id
        ).first()
        
        if not project_tool:
            return jsonify({'error': 'Tool connection not found'}), 404
        
        # Mark as inactive instead of deleting
        project_tool.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Tool disconnected from project successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error disconnecting tool from project: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 