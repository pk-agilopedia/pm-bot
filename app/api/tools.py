from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api import bp
from app.models import User, Tool, ToolType, db

@bp.route('/tools', methods=['GET'])
@jwt_required()
def get_tools():
    """Get all tools for the user's tenant"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        tools = Tool.query.filter_by(
            tenant_id=user.tenant_id,
            is_active=True
        ).order_by(Tool.updated_at.desc()).all()
        
        tool_list = []
        for tool in tools:
            tool_data = {
                'id': tool.id,
                'name': tool.name,
                'tool_type': tool.tool_type.value,
                'base_url': tool.base_url,
                'configuration': tool.configuration,
                'created_at': tool.created_at.isoformat(),
                'updated_at': tool.updated_at.isoformat()
            }
            tool_list.append(tool_data)
        
        return jsonify({
            'tools': tool_list,
            'total_count': len(tool_list)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting tools: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/tools', methods=['POST'])
@jwt_required()
def create_tool():
    """Create a new tool configuration"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        # Validate input
        required_fields = ['name', 'tool_type', 'base_url', 'api_token']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate tool type
        try:
            tool_type = ToolType(data['tool_type'])
        except ValueError:
            return jsonify({'error': 'Invalid tool type'}), 400
        
        # Create tool
        tool = Tool(
            tenant_id=user.tenant_id,
            name=data['name'],
            tool_type=tool_type,
            base_url=data['base_url'],
            api_token=data['api_token'],  # In production, encrypt this
            configuration=data.get('configuration', {})
        )
        
        db.session.add(tool)
        db.session.commit()
        
        return jsonify({
            'message': 'Tool created successfully',
            'tool': {
                'id': tool.id,
                'name': tool.name,
                'tool_type': tool.tool_type.value,
                'base_url': tool.base_url,
                'configuration': tool.configuration
            }
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating tool: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/tools/<int:tool_id>', methods=['PUT'])
@jwt_required()
def update_tool(tool_id):
    """Update a tool configuration"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        tool = Tool.query.filter_by(
            id=tool_id,
            tenant_id=user.tenant_id
        ).first()
        
        if not tool:
            return jsonify({'error': 'Tool not found'}), 404
        
        data = request.get_json()
        
        # Update tool fields
        if 'name' in data:
            tool.name = data['name']
        
        if 'base_url' in data:
            tool.base_url = data['base_url']
        
        if 'api_token' in data:
            tool.api_token = data['api_token']  # In production, encrypt this
        
        if 'configuration' in data:
            tool.configuration = data['configuration']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Tool updated successfully',
            'tool': {
                'id': tool.id,
                'name': tool.name,
                'tool_type': tool.tool_type.value,
                'base_url': tool.base_url,
                'configuration': tool.configuration
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating tool: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/tools/<int:tool_id>', methods=['DELETE'])
@jwt_required()
def delete_tool(tool_id):
    """Delete a tool configuration"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        tool = Tool.query.filter_by(
            id=tool_id,
            tenant_id=user.tenant_id
        ).first()
        
        if not tool:
            return jsonify({'error': 'Tool not found'}), 404
        
        # Mark as inactive instead of deleting
        tool.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Tool deleted successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting tool: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/tools/types', methods=['GET'])
@jwt_required()
def get_tool_types():
    """Get available tool types"""
    try:
        tool_types = []
        for tool_type in ToolType:
            tool_types.append({
                'value': tool_type.value,
                'name': tool_type.value.replace('_', ' ').title()
            })
        
        return jsonify({
            'tool_types': tool_types
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting tool types: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 