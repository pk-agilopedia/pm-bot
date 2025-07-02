import time
import json
from typing import Dict, Any, List
from datetime import datetime
from .base import BaseAgent, AgentContext, AgentResponse
from app.mcp import mcp_registry, WorkItem

class TaskManagementAgent(BaseAgent):
    """Agent for creating, updating, and tracking work items"""
    
    def __init__(self):
        super().__init__(
            name="task_management",
            description="Creates, updates, and tracks work items across different project management tools"
        )
    
    def execute(self, query: str, context: AgentContext) -> AgentResponse:
        """Execute task management operations"""
        start_time = time.time()
        
        try:
            # Determine the action based on the query
            action = self._determine_action(query)
            
            if not context.project_id:
                return AgentResponse(
                    success=False,
                    content="No project specified for task management.",
                    error="Project ID is required for task operations"
                )
            
            project_context = self._get_project_context(context.project_id)
            
            # Execute the appropriate action
            if action == 'create':
                result = self._create_work_item(query, project_context, context)
            elif action == 'update':
                result = self._update_work_item(query, project_context, context)
            elif action == 'search':
                result = self._search_work_items(query, project_context, context)
            elif action == 'analyze':
                result = self._analyze_tasks(query, project_context, context)
            else:
                result = self._general_task_help(query, project_context, context)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            response = AgentResponse(
                success=True,
                content=result['content'],
                data=result.get('data'),
                tokens_used=result.get('tokens_used', 0),
                cost=result.get('cost', 0.0),
                execution_time=execution_time
            )
            
            # Log execution
            self._log_execution(context, query, response)
            
            return response
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            return AgentResponse(
                success=False,
                content="I encountered an error while managing the task.",
                error=str(e),
                execution_time=execution_time
            )
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """Get system prompt for task management"""
        return """You are a Task Management AI Agent specialized in managing work items across software development projects. Your role is to:

1. **Create Work Items**: Help users create new tasks, user stories, bugs, and other work items
2. **Update Work Items**: Modify existing work items including status, assignee, priority, and description
3. **Track Progress**: Monitor work item status and provide updates on task completion
4. **Search & Filter**: Find specific work items based on various criteria
5. **Provide Insights**: Analyze task patterns and provide recommendations

## Key Capabilities:
- **CRUD Operations**: Create, Read, Update work items in JIRA, Azure DevOps, etc.
- **Status Management**: Track and update work item statuses through workflows
- **Assignment Management**: Assign tasks to team members and manage workloads
- **Priority Management**: Set and adjust work item priorities
- **Dependencies**: Identify and manage task dependencies
- **Time Tracking**: Monitor effort estimation and actual time spent

## Response Format:
For task operations:
- Confirm actions taken
- Provide work item details (ID, title, status, assignee)
- Include links to the actual work items
- Summarize changes made

For searches and analysis:
- Present results in a clear, organized format
- Highlight important information
- Provide actionable insights

Always be specific about which tool/system you're working with and provide clear confirmation of actions taken."""
    
    def _determine_action(self, query: str) -> str:
        """Determine what action to take based on the query"""
        query_lower = query.lower()
        
        if any(keyword in query_lower for keyword in ['create', 'new', 'add', 'make']):
            return 'create'
        elif any(keyword in query_lower for keyword in ['update', 'change', 'modify', 'edit', 'assign', 'move']):
            return 'update'
        elif any(keyword in query_lower for keyword in ['find', 'search', 'show', 'list', 'get']):
            return 'search'
        elif any(keyword in query_lower for keyword in ['analyze', 'analysis', 'report', 'summary']):
            return 'analyze'
        else:
            return 'general'
    
    def _create_work_item(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Create a new work item"""
        # Use LLM to extract work item details from query
        system_prompt = """You are a work item creation assistant. Extract the following information from the user's request:
- title: Brief title for the work item
- description: Detailed description
- work_item_type: Type of work item (Story, Task, Bug, Epic, etc.)
- priority: Priority level (High, Medium, Low, Critical)
- assignee: Person to assign to (if mentioned)
- labels: Any labels or tags (if mentioned)

Return the information as a JSON object. If information is missing, use reasonable defaults or leave empty."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract work item details from: {query}"}
        ]
        
        llm_response = self._call_llm(messages, temperature=0.3)
        
        try:
            # Parse the LLM response to get work item details
            work_item_data = json.loads(llm_response.content)
        except:
            # Fallback to basic parsing
            work_item_data = {
                "title": query[:100],  # Use first 100 chars as title
                "description": query,
                "work_item_type": "Task"
            }
        
        # Create work item using the first available tool
        tools = project_context.get('tools', [])
        created_items = []
        
        for tool in tools:
            provider = mcp_registry.get_provider(tool['type'])
            if provider and hasattr(provider, 'create_work_item'):
                work_item = WorkItem(
                    id="",  # Will be assigned by the provider
                    title=work_item_data.get('title', 'New Work Item'),
                    description=work_item_data.get('description', ''),
                    status='New',
                    assignee=work_item_data.get('assignee'),
                    priority=work_item_data.get('priority'),
                    labels=work_item_data.get('labels', []),
                    metadata={'work_item_type': work_item_data.get('work_item_type', 'Task')}
                )
                
                project_key = project_context['project']['key']
                result = provider.create_work_item(project_key, work_item)
                
                if result.success:
                    created_items.append({
                        'tool': tool['name'],
                        'item': result.data
                    })
        
        if created_items:
            content = f"Successfully created work item(s):\n"
            for item in created_items:
                content += f"- {item['tool']}: {item['item']}\n"
        else:
            content = "No work items were created. Please check tool configurations."
        
        return {
            'content': content,
            'data': created_items,
            'tokens_used': llm_response.tokens_used.get('total_tokens', 0),
            'cost': llm_response.cost
        }
    
    def _update_work_item(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Update an existing work item"""
        # Use LLM to extract update details
        system_prompt = """You are a work item update assistant. Extract the following information from the user's request:
- work_item_id: ID or key of the work item to update
- updates: Dictionary of fields to update (status, assignee, priority, title, description, etc.)

Return the information as a JSON object."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract update details from: {query}"}
        ]
        
        llm_response = self._call_llm(messages, temperature=0.3)
        
        try:
            update_data = json.loads(llm_response.content)
        except:
            return {
                'content': "I couldn't understand the update request. Please specify the work item ID and what changes you want to make.",
                'tokens_used': llm_response.tokens_used.get('total_tokens', 0),
                'cost': llm_response.cost
            }
        
        work_item_id = update_data.get('work_item_id')
        updates = update_data.get('updates', {})
        
        if not work_item_id:
            return {
                'content': "Please specify the work item ID or key to update.",
                'tokens_used': llm_response.tokens_used.get('total_tokens', 0),
                'cost': llm_response.cost
            }
        
        # Update work item using available tools
        tools = project_context.get('tools', [])
        updated_items = []
        
        for tool in tools:
            provider = mcp_registry.get_provider(tool['type'])
            if provider and hasattr(provider, 'update_work_item'):
                project_key = project_context['project']['key']
                result = provider.update_work_item(project_key, work_item_id, updates)
                
                if result.success:
                    updated_items.append({
                        'tool': tool['name'],
                        'item': result.data
                    })
        
        if updated_items:
            content = f"Successfully updated work item {work_item_id}:\n"
            for item in updated_items:
                content += f"- {item['tool']}: {item['item']}\n"
        else:
            content = f"Could not update work item {work_item_id}. Please check the ID and try again."
        
        return {
            'content': content,
            'data': updated_items,
            'tokens_used': llm_response.tokens_used.get('total_tokens', 0),
            'cost': llm_response.cost
        }
    
    def _search_work_items(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Search for work items"""
        # Extract search criteria from query
        all_work_items = []
        
        tools = project_context.get('tools', [])
        for tool in tools:
            tool_data = tool.get('data', {})
            if 'work_items' in tool_data:
                all_work_items.extend(tool_data['work_items'])
        
        # Format work items for display
        if all_work_items:
            content = f"Found {len(all_work_items)} work items:\n\n"
            content += self._format_work_items_for_llm(all_work_items)
        else:
            content = "No work items found matching your criteria."
        
        return {
            'content': content,
            'data': all_work_items[:50],  # Limit for performance
            'tokens_used': 0,
            'cost': 0.0
        }
    
    def _analyze_tasks(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Analyze tasks and provide insights"""
        # Get all work items
        all_work_items = []
        tools = project_context.get('tools', [])
        
        for tool in tools:
            tool_data = tool.get('data', {})
            if 'work_items' in tool_data:
                all_work_items.extend(tool_data['work_items'])
        
        # Use LLM to analyze the tasks
        system_prompt = self.get_system_prompt(context)
        
        work_items_text = self._format_work_items_for_llm(all_work_items)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze these work items and answer: {query}\n\nWork Items:\n{work_items_text}"}
        ]
        
        llm_response = self._call_llm(messages, temperature=0.3, max_tokens=1500)
        
        return {
            'content': llm_response.content,
            'data': {'work_items_count': len(all_work_items)},
            'tokens_used': llm_response.tokens_used.get('total_tokens', 0),
            'cost': llm_response.cost
        }
    
    def _general_task_help(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Provide general task management help"""
        system_prompt = self.get_system_prompt(context)
        
        project_data = self._format_project_data(project_context)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Help with this task management question: {query}\n\nProject Context:\n{project_data}"}
        ]
        
        llm_response = self._call_llm(messages, temperature=0.5, max_tokens=1000)
        
        return {
            'content': llm_response.content,
            'tokens_used': llm_response.tokens_used.get('total_tokens', 0),
            'cost': llm_response.cost
        }
    
    def _format_project_data(self, project_context: Dict[str, Any]) -> str:
        """Format project data for LLM"""
        if not project_context:
            return "No project data available."
        
        formatted_data = []
        project = project_context.get('project', {})
        formatted_data.append(f"Project: {project.get('name', 'Unknown')}")
        
        tools = project_context.get('tools', [])
        for tool in tools:
            formatted_data.append(f"Tool: {tool['name']} ({tool['type']})")
            
            tool_data = tool.get('data', {})
            if 'work_items' in tool_data:
                work_items = tool_data['work_items']
                formatted_data.append(f"Work Items: {len(work_items)} total")
        
        return "\n".join(formatted_data) 