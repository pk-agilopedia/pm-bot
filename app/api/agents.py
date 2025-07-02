from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api import bp
from app.models import User, AgentExecution, db
from app.agents.base import agent_registry
from sqlalchemy import desc

@bp.route('/agents', methods=['GET'])
@jwt_required()
def get_available_agents():
    """Get list of available AI agents"""
    try:
        agents = []
        for agent_name in agent_registry.list_agents():
            agent = agent_registry.get_agent(agent_name)
            if agent:
                agents.append({
                    'name': agent.name,
                    'description': agent.description
                })
        
        return jsonify({
            'agents': agents,
            'total_count': len(agents)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting agents: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/agents/executions', methods=['GET'])
@jwt_required()
def get_agent_executions():
    """Get agent execution history for the user"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        agent_type = request.args.get('agent_type')
        project_id = request.args.get('project_id', type=int)
        
        # Build query
        query = AgentExecution.query.filter_by(user_id=user_id)
        
        if agent_type:
            query = query.filter_by(agent_type=agent_type)
        
        if project_id:
            query = query.filter_by(project_id=project_id)
        
        # Execute query with pagination
        executions = query.order_by(desc(AgentExecution.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        execution_list = []
        for execution in executions.items:
            execution_data = {
                'id': execution.id,
                'agent_type': execution.agent_type,
                'task_description': execution.task_description,
                'status': execution.status.value,
                'start_time': execution.start_time.isoformat() if execution.start_time else None,
                'end_time': execution.end_time.isoformat() if execution.end_time else None,
                'duration_seconds': execution.duration_seconds,
                'total_tokens': execution.total_tokens,
                'total_cost': float(execution.total_cost) if execution.total_cost else 0.0,
                'project_id': execution.project_id,
                'created_at': execution.created_at.isoformat()
            }
            
            if execution.error_message:
                execution_data['error_message'] = execution.error_message
            
            execution_list.append(execution_data)
        
        return jsonify({
            'executions': execution_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': executions.total,
                'pages': executions.pages,
                'has_next': executions.has_next,
                'has_prev': executions.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting agent executions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/agents/executions/<int:execution_id>', methods=['GET'])
@jwt_required()
def get_agent_execution(execution_id):
    """Get detailed information about a specific agent execution"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        execution = AgentExecution.query.filter_by(
            id=execution_id,
            user_id=user_id
        ).first()
        
        if not execution:
            return jsonify({'error': 'Execution not found'}), 404
        
        execution_data = {
            'id': execution.id,
            'agent_type': execution.agent_type,
            'task_description': execution.task_description,
            'status': execution.status.value,
            'start_time': execution.start_time.isoformat() if execution.start_time else None,
            'end_time': execution.end_time.isoformat() if execution.end_time else None,
            'duration_seconds': execution.duration_seconds,
            'total_tokens': execution.total_tokens,
            'total_cost': float(execution.total_cost) if execution.total_cost else 0.0,
            'project_id': execution.project_id,
            'session_id': execution.session_id,
            'output': execution.output,
            'error_message': execution.error_message,
            'created_at': execution.created_at.isoformat()
        }
        
        return jsonify({'execution': execution_data}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting agent execution: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/agents/stats', methods=['GET'])
@jwt_required()
def get_agent_stats():
    """Get usage statistics for AI agents"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get stats for the user
        from sqlalchemy import func
        
        # Total executions by agent type
        agent_stats = db.session.query(
            AgentExecution.agent_type,
            func.count(AgentExecution.id).label('count'),
            func.sum(AgentExecution.total_tokens).label('total_tokens'),
            func.sum(AgentExecution.total_cost).label('total_cost'),
            func.avg(AgentExecution.duration_seconds).label('avg_duration')
        ).filter_by(user_id=user_id).group_by(AgentExecution.agent_type).all()
        
        stats_by_agent = []
        for stat in agent_stats:
            stats_by_agent.append({
                'agent_type': stat.agent_type,
                'execution_count': stat.count,
                'total_tokens': stat.total_tokens or 0,
                'total_cost': float(stat.total_cost) if stat.total_cost else 0.0,
                'average_duration': float(stat.avg_duration) if stat.avg_duration else 0.0
            })
        
        # Overall stats
        overall_stats = db.session.query(
            func.count(AgentExecution.id).label('total_executions'),
            func.sum(AgentExecution.total_tokens).label('total_tokens'),
            func.sum(AgentExecution.total_cost).label('total_cost')
        ).filter_by(user_id=user_id).first()
        
        return jsonify({
            'overall': {
                'total_executions': overall_stats.total_executions or 0,
                'total_tokens': overall_stats.total_tokens or 0,
                'total_cost': float(overall_stats.total_cost) if overall_stats.total_cost else 0.0
            },
            'by_agent': stats_by_agent
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting agent stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 