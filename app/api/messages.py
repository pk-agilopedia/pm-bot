import os
import uuid
import time
import pprint
from datetime import datetime
from flask import request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api import bp
from app.models import User, ChatSession, ChatMessage, db
from app.agents.base import AgentContext, agent_registry
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import Bot Framework SDK
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity

# -----------------------------
# Adapter for Bot Framework
# -----------------------------

adapter_settings = BotFrameworkAdapterSettings(
    app_id=os.environ.get("BOT_APP_ID", ""),
    app_password=os.environ.get("BOT_APP_PASSWORD", "")
)
adapter = BotFrameworkAdapter(adapter_settings)

# Thread pool for running sync operations in async context
thread_pool = ThreadPoolExecutor(max_workers=4)

# -----------------------------
# Async wrapper for agent pipeline
# -----------------------------

async def run_agent_pipeline_async(message, user_id, project_id=None, session_id=None, interface="teams"):
    """
    Async wrapper for the agent pipeline to avoid blocking the async event loop
    Preserves Flask application context for database operations
    """
    # Get the current Flask app context
    app = current_app._get_current_object()
    
    def run_with_context():
        with app.app_context():
            return run_agent_pipeline(message, user_id, project_id, session_id, interface)
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(thread_pool, run_with_context)

# -----------------------------
# Shared logic for message handling
# -----------------------------

def run_agent_pipeline(message, user_id, project_id=None, session_id=None, interface="web"):
    """
    Shared logic to handle a message and produce an agent response.
    Used both by web UI and Teams endpoint.
    """
    # Fetch user
    user = User.query.get(user_id)
    if not user:
        return {
            "error": "User not found",
            "status_code": 404
        }

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

    # Find agent
    agent = agent_registry.get_agent_for_query(message, context)

    if not agent:
        return {
            "error": "No suitable agent found for this query",
            "status_code": 400
        }

    # Run agent
    start_time = time.time()
    agent_response = agent.execute(message, context)
    end_time = time.time()

    # Store assistant message
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
        llm_provider=None,
        model_name=None,
        tokens_used=agent_response.tokens_used,
        cost=agent_response.cost
    )
    db.session.add(assistant_message)
    db.session.commit()

    # Build response
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

    return {
        "data": response_data,
        "status_code": 200
    }


# -----------------------------
# Web (JWT Auth) endpoint
# -----------------------------

@bp.route('/messages', methods=['POST'])
@jwt_required()
def handle_message():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400

        message = data['message']
        project_id = data.get('project_id')
        session_id = data.get('session_id')
        interface = data.get('interface', 'web')

        result = run_agent_pipeline(
            message=message,
            user_id=user_id,
            project_id=project_id,
            session_id=session_id,
            interface=interface
        )

        return jsonify(result.get("data")), result.get("status_code")

    except Exception as e:
        current_app.logger.error(f"Error handling message: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An error occurred while processing your message'
        }), 500


# -----------------------------
# Microsoft Teams endpoint (async) - FULL TEAMS INTEGRATION
# -----------------------------

@bp.route('/teams/messages', methods=['POST'])
async def handle_teams_message():
    """
    Endpoint for handling messages from Microsoft Teams.
    Supports full Teams integration with Bot Framework authentication and responses.
    """
    try:
        # Print the raw payload for debugging
        print("========== Incoming request from Teams ==========")
        pprint.pprint(request.json)
        print("=================================================")

        # Get the authorization header
        auth_header = request.headers.get('Authorization', '')
        print(f"Authorization header present: {bool(auth_header)}")
        if auth_header:
            print(f"Auth header preview: {auth_header[:50]}...")
        
        # Deserialize incoming Activity
        activity = Activity().deserialize(request.json)
        
        # Extract message text
        message_text = activity.text if activity.text else ""
        
        # Skip empty messages
        if not message_text.strip():
            return Response(status=200)

        # Map Teams user to your internal user (implement your logic here)
        teams_user_id = activity.from_property.id if activity.from_property else None
        conversation_id = activity.conversation.id if activity.conversation else None
        
        print(f"Teams user ID: {teams_user_id}")
        print(f"Conversation ID: {conversation_id}")
        
        # TEMP: Use default/fixed user ID for testing without auth
        # TODO: Implement proper user mapping logic based on teams_user_id
        default_user_id = 1  # Replace with a valid user ID in your DB

        # Define the turn logic function
        async def turn_logic(turn_context: TurnContext):
            try:
                print(f"Processing message: {message_text}")
                
                # Run agent pipeline asynchronously with proper context
                result = await run_agent_pipeline_async(
                    message=message_text,
                    user_id=default_user_id,
                    interface="teams"
                )
                
                print(f"Agent pipeline result: {result}")
                
                # Prepare response
                if result.get("error"):
                    response_text = f"Sorry, I encountered an error: {result.get('error')}"
                else:
                    response_text = result["data"]["content"]
                
                print(f"Sending response: {response_text[:100]}...")
                
                # Send response back to Teams
                await turn_context.send_activity(response_text)
                
            except Exception as e:
                error_msg = f"Error in turn logic: {str(e)}"
                current_app.logger.error(error_msg)
                print(f"Turn logic error: {error_msg}")
                
                # Try to send error message to user
                try:
                    await turn_context.send_activity("Sorry, I encountered an error processing your message.")
                except Exception as send_error:
                    print(f"Failed to send error message: {str(send_error)}")

        # Process the activity with Bot Framework
        print("Processing activity with Bot Framework adapter...")
        await adapter.process_activity(activity, auth_header, turn_logic)
        
        print("Successfully processed Teams message")
        return Response(status=200)

    except Exception as e:
        error_msg = f"Error handling Teams message: {str(e)}"
        current_app.logger.error(error_msg)
        print(f"Main handler error: {error_msg}")
        return Response(status=500)


# -----------------------------
# Alternative Teams endpoint without Bot Framework (for testing)
# -----------------------------

@bp.route('/teams/messages/simple', methods=['POST'])
def handle_teams_message_simple():
    """
    Simplified Teams endpoint that bypasses Bot Framework authentication.
    Use this for testing purposes only.
    """
    try:
        # Print the raw payload for debugging
        print("========== Incoming request from Teams (Simple) ==========")
        pprint.pprint(request.json)
        print("==========================================================")

        # Parse the request
        data = request.get_json()
        
        # Extract message text from Teams activity
        message_text = data.get('text', '')
        
        # Skip empty messages
        if not message_text.strip():
            return jsonify({'type': 'message', 'text': 'Hello! How can I help you?'}), 200

        # TEMP: Use default/fixed user ID for testing
        default_user_id = 1

        # Run agent pipeline
        result = run_agent_pipeline(
            message=message_text,
            user_id=default_user_id,
            interface="teams"
        )

        # Prepare response
        if result.get("error"):
            response_text = f"Sorry, I encountered an error: {result.get('error')}"
        else:
            response_text = result["data"]["content"]

        # Return response in Teams format
        return jsonify({
            'type': 'message',
            'text': response_text
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error handling Teams message (simple): {str(e)}")
        return jsonify({
            'type': 'message',
            'text': 'Sorry, I encountered an error processing your message.'
        }), 500


# -----------------------------
# Other Endpoints (same as yours)
# -----------------------------

@bp.route('/messages/history/<session_id>', methods=['GET'])
@jwt_required()
def get_message_history(session_id):
    try:
        user_id = get_jwt_identity()

        chat_session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if not chat_session:
            return jsonify({'error': 'Session not found'}), 404

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
    try:
        user_id = get_jwt_identity()

        sessions = ChatSession.query.filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(ChatSession.updated_at.desc()).all()

        session_list = []
        for session in sessions:
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
    try:
        user_id = get_jwt_identity()

        session = ChatSession.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).first()

        if not session:
            return jsonify({'error': 'Session not found'}), 404

        session.is_active = False
        db.session.commit()

        return jsonify({'message': 'Session deleted successfully'}), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting session: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


# -----------------------------
# Helper for conversation history
# -----------------------------

def _get_conversation_history(session_id: int, limit: int = 10):
    messages = ChatMessage.query.filter_by(
        session_id=session_id
    ).order_by(ChatMessage.created_at.desc()).limit(limit).all()

    history = []
    for msg in reversed(messages):
        history.append({
            'role': 'user' if msg.message_type == 'user' else 'assistant',
            'content': msg.content,
            'timestamp': msg.created_at.isoformat()
        })

    return history