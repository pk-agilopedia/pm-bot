import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base import BaseAgent, AgentContext, AgentResponse

class ProjectAnalysisAgent(BaseAgent):
    """Agent for analyzing project health, progress, and metrics"""
    
    def __init__(self):
        super().__init__(
            name="project_analysis",
            description="Analyzes project health, progress, metrics, and provides insights on project status"
        )
    
    def execute(self, query: str, context: AgentContext) -> AgentResponse:
        """Execute project analysis"""
        start_time = time.time()
        
        try:
            # Get project context
            if not context.project_id:
                return AgentResponse(
                    success=False,
                    content="No project specified for analysis.",
                    error="Project ID is required for analysis"
                )
            
            project_context = self._get_project_context(context.project_id)
            
            # Build messages for LLM
            system_prompt = self.get_system_prompt(context)
            
            # Format project data for analysis
            project_data = self._format_project_data(project_context)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Please analyze the following project data and answer this question: {query}\n\nProject Data:\n{project_data}"}
            ]
            
            # Call LLM
            llm_response = self._call_llm(messages, temperature=0.3, max_tokens=2000)
            
            # Calculate metrics
            metrics = self._calculate_project_metrics(project_context)
            
            # Format response
            end_time = time.time()
            execution_time = end_time - start_time
            
            response = AgentResponse(
                success=True,
                content=llm_response.content,
                data={
                    'metrics': metrics,
                    'project_context': project_context,
                    'analysis_timestamp': datetime.utcnow().isoformat()
                },
                tokens_used=llm_response.tokens_used.get('total_tokens', 0),
                cost=llm_response.cost,
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
                content="I encountered an error while analyzing the project.",
                error=str(e),
                execution_time=execution_time
            )
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """Get system prompt for project analysis"""
        return """You are a Project Analysis AI Agent specialized in analyzing software development projects. Your role is to:

1. **Analyze Project Health**: Evaluate overall project status, identify potential issues, and assess project trajectory
2. **Progress Tracking**: Analyze sprint/milestone progress, completion rates, and timeline adherence
3. **Metrics Analysis**: Interpret key project metrics like velocity, burn rates, cycle time, and lead time
4. **Identify Patterns**: Spot trends in work completion, team performance, and project risks
5. **Provide Insights**: Offer actionable recommendations for project improvement

## Analysis Framework:
- **Health Status**: Overall project health (Green/Yellow/Red)
- **Progress**: Current sprint/milestone status and completion trends
- **Velocity**: Team velocity trends and capacity analysis
- **Quality**: Bug/defect rates and resolution times
- **Blockers**: Current impediments and risks
- **Recommendations**: Specific actions to improve project outcomes

## Response Format:
Provide clear, structured analysis with:
- Executive summary
- Key metrics and findings
- Risk assessment
- Actionable recommendations
- Supporting data and trends

Use data-driven insights and maintain a professional, analytical tone. Focus on practical recommendations that project managers can implement."""
    
    def _format_project_data(self, project_context: Dict[str, Any]) -> str:
        """Format project data for LLM analysis"""
        if not project_context:
            return "No project data available."
        
        formatted_data = []
        
        # Project basic info
        project = project_context.get('project', {})
        formatted_data.append(f"Project: {project.get('name', 'Unknown')} ({project.get('key', 'N/A')})")
        formatted_data.append(f"Description: {project.get('description', 'No description')}")
        
        if project.get('start_date'):
            formatted_data.append(f"Start Date: {project['start_date']}")
        if project.get('end_date'):
            formatted_data.append(f"End Date: {project['end_date']}")
        
        formatted_data.append("")
        
        # Tools and data
        tools = project_context.get('tools', [])
        for tool in tools:
            formatted_data.append(f"=== {tool['name']} ({tool['type']}) ===")
            
            tool_data = tool.get('data', {})
            
            # Work items
            if 'work_items' in tool_data:
                work_items = tool_data['work_items']
                formatted_data.append(self._format_work_items_for_llm(work_items))
            
            # Sprints
            if 'sprints' in tool_data:
                sprints = tool_data['sprints']
                formatted_data.append(self._format_sprints_for_llm(sprints))
            
            formatted_data.append("")
        
        return "\n".join(formatted_data)
    
    def _calculate_project_metrics(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate key project metrics"""
        metrics = {
            'total_work_items': 0,
            'completed_work_items': 0,
            'in_progress_work_items': 0,
            'open_work_items': 0,
            'completion_rate': 0.0,
            'active_sprints': 0,
            'total_sprints': 0,
            'team_members': set(),
            'priority_breakdown': {},
            'status_breakdown': {},
            'overdue_items': 0
        }
        
        tools = project_context.get('tools', [])
        
        for tool in tools:
            tool_data = tool.get('data', {})
            
            # Analyze work items
            if 'work_items' in tool_data:
                work_items = tool_data['work_items']
                
                for item in work_items:
                    metrics['total_work_items'] += 1
                    
                    # Status analysis
                    status = getattr(item, 'status', '').lower() if hasattr(item, 'status') else ''
                    if status in ['done', 'completed', 'closed', 'resolved']:
                        metrics['completed_work_items'] += 1
                    elif status in ['in progress', 'active', 'working']:
                        metrics['in_progress_work_items'] += 1
                    else:
                        metrics['open_work_items'] += 1
                    
                    # Status breakdown
                    if status:
                        metrics['status_breakdown'][status] = metrics['status_breakdown'].get(status, 0) + 1
                    
                    # Priority breakdown
                    priority = getattr(item, 'priority', '') if hasattr(item, 'priority') else ''
                    if priority:
                        metrics['priority_breakdown'][priority] = metrics['priority_breakdown'].get(priority, 0) + 1
                    
                    # Team members
                    assignee = getattr(item, 'assignee', '') if hasattr(item, 'assignee') else ''
                    if assignee:
                        metrics['team_members'].add(assignee)
                    
                    # Overdue analysis (simplified)
                    if hasattr(item, 'created_date') and item.created_date:
                        days_old = (datetime.utcnow() - item.created_date).days
                        if days_old > 30 and status not in ['done', 'completed', 'closed', 'resolved']:
                            metrics['overdue_items'] += 1
            
            # Analyze sprints
            if 'sprints' in tool_data:
                sprints = tool_data['sprints']
                
                for sprint in sprints:
                    metrics['total_sprints'] += 1
                    
                    state = getattr(sprint, 'state', '').lower() if hasattr(sprint, 'state') else ''
                    if state in ['active', 'current', 'open']:
                        metrics['active_sprints'] += 1
        
        # Calculate completion rate
        if metrics['total_work_items'] > 0:
            metrics['completion_rate'] = (metrics['completed_work_items'] / metrics['total_work_items']) * 100
        
        # Convert set to count
        metrics['team_size'] = len(metrics['team_members'])
        del metrics['team_members']  # Remove set for JSON serialization
        
        return metrics 