from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api import bp
from app.models import User, Project, ChatSession, ChatMessage, db
from app.agents.base import AgentContext, agent_registry
import uuid
from datetime import datetime
import time

@bp.route('/messages', methods=['POST'])
@jwt_required()
def handle_message():
    """
    Main endpoint for receiving messages from different chat interfaces
    (Teams, Slack, Web interface, etc.)
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message']
        project_id = data.get('project_id')
        session_id = data.get('session_id')
        interface = data.get('interface', 'web')  # web, teams, slack
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get or create chat session
        if session_id:
            chat_session = ChatSession.query.filter_by(
                session_id=session_id, 
                user_id=user_id
            ).first()
        else:
            chat_session = None
        
        if not chat_session:
            chat_session = ChatSession(
                user_id=user_id,
                project_id=project_id,
                session_id=str(uuid.uuid4()),
                title=message[:100] if len(message) > 100 else message,
                is_active=True
            )
            db.session.add(chat_session)
            db.session.commit()
        
        # Store user message
        user_message = ChatMessage(
            session_id=chat_session.id,
            message_type='user',
            content=message,
            message_metadata={'interface': interface}
        )
        db.session.add(user_message)
        
        # Create agent context
        context = AgentContext(
            user_id=user_id,
            project_id=project_id,
            session_id=chat_session.id,
            tenant_id=user.tenant_id,
            conversation_history=_get_conversation_history(chat_session.id),
            custom_data={'interface': interface}
        )
        
        # Determine which agent should handle the message
        agent = agent_registry.get_agent_for_query(message, context)
        
        if not agent:
            return jsonify({
                'error': 'No suitable agent found for this query'
            }), 400
        
        # Execute agent
        start_time = time.time()
        agent_response = agent.execute(message, context)
        end_time = time.time()
        
        # Store assistant response
        assistant_message = ChatMessage(
            session_id=chat_session.id,
            message_type='assistant',
            content=agent_response.content,
            message_metadata={
                'agent_type': agent.name,
                'success': agent_response.success,
                'execution_time': agent_response.execution_time,
                'interface': interface
            },
            llm_provider=None,  # Could be enhanced to track LLM provider
            model_name=None,
            tokens_used=agent_response.tokens_used,
            cost=agent_response.cost
        )
        db.session.add(assistant_message)
        db.session.commit()
        
        # Prepare response
        response_data = {
            'session_id': chat_session.session_id,
            'message_id': assistant_message.id,
            'content': agent_response.content,
            'success': agent_response.success,
            'agent_type': agent.name,
            'execution_time': agent_response.execution_time,
            'tokens_used': agent_response.tokens_used,
            'cost': agent_response.cost,
            'timestamp': assistant_message.created_at.isoformat()
        }
        
        if agent_response.data:
            response_data['data'] = agent_response.data
        
        if not agent_response.success:
            response_data['error'] = agent_response.error
        
        return jsonify(response_data), 200
        
    except Exception as e:
        current_app.logger.error(f"Error handling message: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An error occurred while processing your message'
        }), 500

@bp.route('/messages/history/<session_id>', methods=['GET'])
@jwt_required()
def get_message_history(session_id):
    """Get conversation history for a session"""
    try:
        user_id = get_jwt_identity()
        
        # Verify session belongs to user
        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get messages
        messages = ChatMessage.query.filter_by(
            session_id=chat_session.id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        history = []
        for msg in messages:
            history.append({
                'id': msg.id,
                'type': msg.message_type,
                'content': msg.content,
                'timestamp': msg.created_at.isoformat(),
                'metadata': msg.message_metadata,
                'tokens_used': msg.tokens_used,
                'cost': msg.cost
            })
        
        return jsonify({
            'session_id': session_id,
            'messages': history,
            'total_count': len(history)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting message history: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/sessions', methods=['GET'])
@jwt_required()
def get_user_sessions():
    """Get all chat sessions for the current user"""
    try:
        user_id = get_jwt_identity()
        
        sessions = ChatSession.query.filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(ChatSession.updated_at.desc()).all()
        
        session_list = []
        for session in sessions:
            # Get last message
            last_message = ChatMessage.query.filter_by(
                session_id=session.id
            ).order_by(ChatMessage.created_at.desc()).first()
            
            session_data = {
                'session_id': session.session_id,
                'title': session.title,
                'project_id': session.project_id,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'last_message': last_message.content[:100] if last_message else None,
                'last_message_time': last_message.created_at.isoformat() if last_message else None
            }
            
            if session.project:
                session_data['project_name'] = session.project.name
            
            session_list.append(session_data)
        
        return jsonify({
            'sessions': session_list,
            'total_count': len(session_list)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error getting user sessions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/sessions/<session_id>', methods=['DELETE'])
@jwt_required()
def delete_session(session_id):
    """Delete a chat session"""
    try:
        user_id = get_jwt_identity()
        
        session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()
        
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Mark as inactive instead of deleting
        session.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Session deleted successfully'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting session: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def _get_conversation_history(session_id: int, limit: int = 10):
    """Get recent conversation history for context"""
    messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
    
    history = []
    for msg in reversed(messages):  # Reverse to get chronological order
        history.append({
            'role': 'user' if msg.message_type == 'user' else 'assistant',
            'content': msg.content,
            'timestamp': msg.created_at.isoformat()
        })
    
    return history 