from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import uuid
from flask import current_app
from app.llm import LLMManager, LLMResponse
from app.mcp import mcp_registry, MCPResponse
from app.models import AgentExecution, RequestStatus
from app import db
from app.mcp import JiraProvider, AzureDevOpsProvider, GitHubProvider

@dataclass
class AgentContext:
    """Context for agent execution"""
    user_id: int
    project_id: Optional[int]
    session_id: Optional[int]
    tenant_id: int
    conversation_history: List[Dict[str, Any]] = None
    tools_available: List[str] = None
    custom_data: Dict[str, Any] = None

@dataclass
class AgentResponse:
    """Response from agent execution"""
    success: bool
    content: str
    data: Any = None
    error: str = None
    metadata: Dict[str, Any] = None
    tokens_used: int = 0
    cost: float = 0.0
    execution_time: float = 0.0

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm_manager = LLMManager()
    
    @abstractmethod
    def execute(self, query: str, context: AgentContext) -> AgentResponse:
        """Execute the agent with the given query and context"""
        pass
    
    @abstractmethod
    def get_system_prompt(self, context: AgentContext) -> str:
        """Get the system prompt for this agent"""
        pass
    
    def _call_llm(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Call the LLM with the given messages"""
        return self.llm_manager.generate_response(messages, **kwargs)
    
    def _get_project_context(self, project_id: int) -> Dict[str, Any]:
        """Get project context from database and MCP providers"""
        from app.models import Project, ProjectTool, Tool
        
        project = Project.query.get(project_id)
        if not project:
            return {}
        
        project_tools = ProjectTool.query.filter_by(
            project_id=project_id, 
            is_active=True
        ).all()
        
        context = {
            'project': {
                'id': project.id,
                'name': project.name,
                'key': project.key,
                'description': project.description,
                'start_date': project.start_date.isoformat() if project.start_date else None,
                'end_date': project.end_date.isoformat() if project.end_date else None
            },
            'tools': []
        }
        
        # Gather data from connected tools
        for project_tool in project_tools:
            tool = project_tool.tool
            provider = None
            
            # Create provider based on tool type
            try:
                if tool.tool_type.value == 'jira':
                    provider = JiraProvider(
                        server_url=tool.base_url,
                        username='mock_user',
                        api_token=tool.api_token,
                        config=tool.configuration
                    )
                elif tool.tool_type.value == 'azure_devops':
                    provider = AzureDevOpsProvider(
                        server_url=tool.base_url,
                        auth_token=tool.api_token,
                        config=tool.configuration
                    )
                elif tool.tool_type.value == 'github':
                    provider = GitHubProvider(
                        base_url=tool.base_url,
                        auth_token=tool.api_token,
                        config=tool.configuration
                    )
            except Exception as e:
                current_app.logger.error(f"Error creating provider for {tool.name}: {str(e)}")
                continue
            
            if provider:
                tool_data = {
                    'type': tool.tool_type.value,
                    'name': tool.name,
                    'data': {}
                }
                
                try:
                    # Get basic project data from the tool
                    if hasattr(provider, 'get_work_items'):
                        work_items_response = provider.get_work_items(project.key)
                        if work_items_response.success:
                            tool_data['data']['work_items'] = work_items_response.data
                    
                    if hasattr(provider, 'get_sprints'):
                        sprints_response = provider.get_sprints(project.key)
                        if sprints_response.success:
                            tool_data['data']['sprints'] = sprints_response.data
                
                except Exception as e:
                    current_app.logger.error(f"Error getting data from {tool.name}: {str(e)}")
                
                context['tools'].append(tool_data)
        
        return context
    
    def _log_execution(self, context: AgentContext, query: str, response: AgentResponse) -> AgentExecution:
        """Log agent execution to database"""
        
        def serialize_data(data):
            """Convert complex objects to JSON-serializable format"""
            if data is None:
                return None
            
            if isinstance(data, dict):
                serialized = {}
                for key, value in data.items():
                    if key == 'project_context' and isinstance(value, dict):
                        # Handle project context with tools data
                        serialized[key] = serialize_data(value)
                    elif key == 'tools' and isinstance(value, list):
                        # Handle tools list with work items and sprints
                        serialized[key] = []
                        for tool in value:
                            if isinstance(tool, dict):
                                tool_data = tool.copy()
                                if 'data' in tool_data:
                                    tool_data['data'] = serialize_data(tool_data['data'])
                                serialized[key].append(tool_data)
                            else:
                                serialized[key].append(serialize_data(tool))
                    elif hasattr(value, '__dict__'):
                        # Convert objects with __dict__ to dictionary
                        serialized[key] = serialize_data(value.__dict__)
                    elif isinstance(value, list):
                        serialized[key] = [serialize_data(item) for item in value]
                    elif isinstance(value, dict):
                        serialized[key] = serialize_data(value)
                    elif isinstance(value, datetime):
                        serialized[key] = value.isoformat()
                    else:
                        serialized[key] = value
                return serialized
            elif isinstance(data, list):
                return [serialize_data(item) for item in data]
            elif hasattr(data, '__dict__'):
                # Convert objects with __dict__ to dictionary
                obj_dict = {}
                for attr, value in data.__dict__.items():
                    if isinstance(value, datetime):
                        obj_dict[attr] = value.isoformat()
                    elif hasattr(value, '__dict__'):
                        obj_dict[attr] = serialize_data(value)
                    elif isinstance(value, list):
                        obj_dict[attr] = serialize_data(value)
                    else:
                        obj_dict[attr] = value
                return obj_dict
            else:
                return data
        
        try:
            # Serialize the response data
            serialized_output = serialize_data(response.data) if response.success else None
            
            execution = AgentExecution(
                user_id=context.user_id,
                project_id=context.project_id,
                session_id=context.session_id,
                agent_type=self.name,
                task_description=query,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_seconds=int(response.execution_time),
                status=RequestStatus.COMPLETED if response.success else RequestStatus.FAILED,
                output=serialized_output,
                error_message=response.error if not response.success else None,
                total_tokens=response.tokens_used,
                total_cost=response.cost
            )
            
            db.session.add(execution)
            db.session.commit()
            return execution
            
        except Exception as e:
            # If there's an error, rollback and log it
            db.session.rollback()
            current_app.logger.error(f"Error logging agent execution: {str(e)}")
            
            # Try to save a simplified version without the complex data
            try:
                execution = AgentExecution(
                    user_id=context.user_id,
                    project_id=context.project_id,
                    session_id=context.session_id,
                    agent_type=self.name,
                    task_description=query,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    duration_seconds=int(response.execution_time),
                    status=RequestStatus.COMPLETED if response.success else RequestStatus.FAILED,
                    output={"error": "Could not serialize complex data"},
                    error_message=response.error if not response.success else None,
                    total_tokens=response.tokens_used,
                    total_cost=response.cost
                )
                
                db.session.add(execution)
                db.session.commit()
                return execution
            except Exception as e2:
                db.session.rollback()
                current_app.logger.error(f"Failed to log agent execution even with simplified data: {str(e2)}")
                return None
    
    def _format_work_items_for_llm(self, work_items: List[Any]) -> str:
        """Format work items data for LLM consumption"""
        if not work_items:
            return "No work items found."
        
        formatted = "Work Items:\n"
        for item in work_items[:20]:  # Limit to avoid token overflow
            if hasattr(item, '__dict__'):
                formatted += f"- ID: {item.id}, Title: {item.title}, Status: {item.status}"
                if item.assignee:
                    formatted += f", Assignee: {item.assignee}"
                if item.priority:
                    formatted += f", Priority: {item.priority}"
                formatted += "\n"
            else:
                formatted += f"- {str(item)}\n"
        
        return formatted
    
    def _format_sprints_for_llm(self, sprints: List[Any]) -> str:
        """Format sprints data for LLM consumption"""
        if not sprints:
            return "No sprints found."
        
        formatted = "Sprints:\n"
        for sprint in sprints:
            if hasattr(sprint, '__dict__'):
                formatted += f"- ID: {sprint.id}, Name: {sprint.name}, State: {sprint.state}"
                if sprint.start_date:
                    formatted += f", Start: {sprint.start_date}"
                if sprint.end_date:
                    formatted += f", End: {sprint.end_date}"
                formatted += "\n"
            else:
                formatted += f"- {str(sprint)}\n"
        
        return formatted

class AgentRegistry:
    """Registry for managing AI agents"""
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent"""
        self._agents[agent.name] = agent
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self._agents.get(name)
    
    def list_agents(self) -> List[str]:
        """List all registered agents"""
        return list(self._agents.keys())
    
    def get_agent_for_query(self, query: str, context: AgentContext) -> Optional[BaseAgent]:
        """Determine which agent should handle the query"""
        query_lower = query.lower()
        
        # Simple keyword-based routing (can be enhanced with ML)
        if any(keyword in query_lower for keyword in ['analyze', 'analysis', 'health', 'metrics', 'progress']):
            return self.get_agent('project_analysis')
        elif any(keyword in query_lower for keyword in ['sprint', 'iteration', 'plan', 'planning']):
            return self.get_agent('sprint_planning')
        elif any(keyword in query_lower for keyword in ['task', 'work item', 'issue', 'ticket', 'create', 'update']):
            return self.get_agent('task_management')
        elif any(keyword in query_lower for keyword in ['performance', 'velocity', 'productivity', 'team']):
            return self.get_agent('performance_analysis')
        elif any(keyword in query_lower for keyword in ['risk', 'risks', 'issues', 'blockers', 'impediments']):
            return self.get_agent('risk_assessment')
        elif any(keyword in query_lower for keyword in ['report', 'status', 'summary', 'dashboard']):
            return self.get_agent('report_generation')
        else:
            # Default to project analysis for general queries
            return self.get_agent('project_analysis')

# Global agent registry
agent_registry = AgentRegistry() 