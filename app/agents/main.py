import time
from typing import Dict, Any, List
from datetime import datetime
from flask import current_app
from .base import BaseAgent, AgentContext, AgentResponse

class MainAgent(BaseAgent):
    """Main coordination agent that analyzes user intent and routes to specialized agents"""
    
    def __init__(self):
        super().__init__(
            name="main",
            description="Intelligent router that analyzes user messages and delegates to specialized agents for analysis or management tasks"
        )
    
    def execute(self, query: str, context: AgentContext) -> AgentResponse:
        """Analyze user intent and route to appropriate specialized agent"""
        start_time = time.time()
        
        try:
            # Analyze user intent using LLM
            intent_analysis = self._analyze_user_intent(query, context)
            
            if not intent_analysis['success']:
                return AgentResponse(
                    success=False,
                    content="I couldn't understand your request. Please try rephrasing your message.",
                    error="Intent analysis failed",
                    execution_time=time.time() - start_time
                )
            
            target_agent = intent_analysis['target_agent']
            reasoning = intent_analysis['reasoning']
            
            # Route to the appropriate specialized agent
            if target_agent == 'analysis':
                from .analysis import AnalysisAgent
                agent = AnalysisAgent()
                
            elif target_agent == 'management':
                from .management import ManagementAgent  
                agent = ManagementAgent()
                
            else:
                return AgentResponse(
                    success=False,
                    content="I'm not sure how to handle that request. Please try being more specific about what you'd like me to do.",
                    error=f"Unknown target agent: {target_agent}",
                    execution_time=time.time() - start_time
                )
            
            # Execute the specialized agent
            current_app.logger.info(f"MainAgent routing to {target_agent} agent. Reasoning: {reasoning}")
            
            # Add routing context to the response
            specialized_response = agent.execute(query, context)
            
            # Enhance response with routing information
            if specialized_response.data is None:
                specialized_response.data = {}
            
            specialized_response.data['routing'] = {
                'target_agent': target_agent,
                'reasoning': reasoning,
                'routed_by': 'main_agent'
            }
            
            return specialized_response
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            current_app.logger.error(f"MainAgent error: {str(e)}")
            
            return AgentResponse(
                success=False,
                content="I encountered an error while processing your request. Please try again.",
                error=str(e),
                execution_time=execution_time
            )
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """Get system prompt for intent analysis"""
        return """You are an intelligent request router for a Project Management AI system. Your job is to analyze user messages and determine the appropriate specialized agent to handle the request.

## Available Specialized Agents:

### 1. Analysis Agent
**Purpose**: Viewing, reporting, metrics, insights, and analysis
**Handles**:
- Viewing current work items, sprints, backlogs
- Status reports and project health analysis
- Metrics dashboards and KPI tracking  
- Progress summaries and timeline analysis
- Team performance and velocity metrics
- Predictive analytics and forecasting
- Risk assessment and issue identification
- Sprint retrospectives and burndown analysis
- Searching and displaying project data

**Action Types**: search, analyze, view, report, display, show, list
**Keywords**: show, view, display, list, current, status, analyze, report, health, metrics, dashboard, progress, performance, velocity, forecast, trends, insights, summary, how is, what is, tell me about

### 2. Management Agent  
**Purpose**: Creating, updating, and managing project artifacts
**Handles**:
- Creating, deleting, updating work items
- Updating work item fields and properties
- Moving items across statuses and workflows
- Assigning users to work items
- Sprint creation, deletion, and planning
- Backlog management and organization
- Managing project resources and assignments

**Action Types**: create, update, delete, assign, move, plan, manage, organize
**Keywords**: create, add, new, update, edit, change, modify, delete, remove, assign, move, transition, plan sprint, create sprint, organize backlog, manage backlog, prioritize, schedule

## Critical Routing Rules:
1. **VIEWING/SHOWING DATA** → Analysis Agent (even if it mentions backlog, work items, sprints)
2. **CREATING/MODIFYING DATA** → Management Agent
3. When in doubt, prefer Analysis Agent for data viewing requests

## Instructions:
1. Analyze the user's message to understand their primary intent
2. Determine which specialized agent is most appropriate
3. Provide clear reasoning for your decision
4. Respond with ONLY a JSON object in this exact format:

```json
{
  "target_agent": "analysis|management", 
  "reasoning": "Brief explanation of why this agent was selected",
  "confidence": "high|medium|low"
}
```

## Examples:

User: "Show me the current items in JIRA backlog"
```json
{
  "target_agent": "analysis",
  "reasoning": "User wants to VIEW current backlog items, which is an analysis/viewing task",
  "confidence": "high"
}
```

User: "Show me the project status"
```json
{
  "target_agent": "analysis",
  "reasoning": "User wants to view current project status, which is an analysis/reporting task",
  "confidence": "high"
}
```

User: "List all open work items"
```json
{
  "target_agent": "analysis",
  "reasoning": "User wants to view/list work items, which is a data viewing task",
  "confidence": "high"
}
```

User: "Create a new sprint for next month"  
```json
{
  "target_agent": "management",
  "reasoning": "User wants to create a new sprint, which is a management task",
  "confidence": "high"
}
```

User: "Update the priority of task ABC-123"
```json
{
  "target_agent": "management",
  "reasoning": "User wants to update a work item field, which is a management operation",
  "confidence": "high"
}
```

User: "How is the team performing?"
```json
{
  "target_agent": "analysis", 
  "reasoning": "User wants team performance insights, which requires analysis and metrics",
  "confidence": "high"
}
```

IMPORTANT: Respond with ONLY the JSON object, no additional text."""
    
    def _analyze_user_intent(self, query: str, context: AgentContext) -> Dict[str, Any]:
        """Analyze user intent using LLM to determine target agent"""
        
        system_prompt = self.get_system_prompt(context)
        
        user_prompt = f"""Analyze this user message and determine the appropriate specialized agent:

User Message: "{query}"

Project Context:
- User ID: {context.user_id}
- Project ID: {context.project_id}  
- Has conversation history: {bool(context.conversation_history)}

Respond with the JSON routing decision:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self._call_llm(
                messages=messages,
                model="gpt-3.5-turbo", 
                temperature=0.1,
                max_tokens=150
            )
            
            # Parse the JSON response
            import json
            import re
            
            # Extract JSON from response
            content = response.content.strip()
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    intent_data = json.loads(json_str)
                    
                    # Validate required fields
                    if 'target_agent' in intent_data and intent_data['target_agent'] in ['analysis', 'management']:
                        return {
                            'success': True,
                            'target_agent': intent_data['target_agent'],
                            'reasoning': intent_data.get('reasoning', 'No reasoning provided'),
                            'confidence': intent_data.get('confidence', 'medium')
                        }
                
                except json.JSONDecodeError:
                    pass
            
            # Fallback: if JSON parsing fails, use keyword analysis
            current_app.logger.warning(f"Failed to parse LLM routing response: {content}")
            return self._fallback_intent_analysis(query)
            
        except Exception as e:
            current_app.logger.error(f"Error in intent analysis: {str(e)}")
            return self._fallback_intent_analysis(query)
    
    def _fallback_intent_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback intent analysis using keyword matching"""
        query_lower = query.lower()
        
        # Strong analysis keywords (viewing/analyzing data)
        strong_analysis_keywords = [
            'show', 'view', 'display', 'list', 'see', 'current', 'status',
            'report', 'analyze', 'analysis', 'health', 'metrics', 'dashboard',
            'progress', 'performance', 'velocity', 'forecast', 'trends',
            'insights', 'summary', 'how is', 'what is', 'tell me about',
            'current items', 'show items', 'view backlog', 'backlog status'
        ]
        
        # Strong management keywords (creating/modifying data)
        strong_management_keywords = [
            'create', 'add', 'new', 'update', 'edit', 'change', 'modify',
            'delete', 'remove', 'assign', 'move', 'transition', 'close',
            'resolve', 'reopen', 'plan sprint', 'create sprint', 'organize backlog',
            'manage backlog', 'prioritize', 'schedule'
        ]
        
        # Neutral keywords that depend on context
        neutral_keywords = [
            'sprint', 'backlog', 'work item', 'task', 'issue', 'ticket', 'story', 'epic'
        ]
        
        # Check for strong indicators first
        strong_analysis_score = sum(1 for keyword in strong_analysis_keywords if keyword in query_lower)
        strong_management_score = sum(1 for keyword in strong_management_keywords if keyword in query_lower)
        
        # If we have strong indicators, use them
        if strong_analysis_score > 0 and strong_management_score == 0:
            return {
                'success': True,
                'target_agent': 'analysis',
                'reasoning': f'Strong analysis keywords detected: viewing/analyzing data request',
                'confidence': 'high'
            }
        elif strong_management_score > 0 and strong_analysis_score == 0:
            return {
                'success': True,
                'target_agent': 'management',
                'reasoning': f'Strong management keywords detected: creating/modifying data request',
                'confidence': 'high'
            }
        
        # If we have mixed signals or only neutral keywords, analyze the action verbs
        action_verbs_analysis = ['show', 'view', 'display', 'list', 'see', 'get', 'find', 'search']
        action_verbs_management = ['create', 'add', 'update', 'edit', 'delete', 'assign', 'move', 'plan']
        
        analysis_action_score = sum(1 for verb in action_verbs_analysis if verb in query_lower)
        management_action_score = sum(1 for verb in action_verbs_management if verb in query_lower)
        
        if analysis_action_score > management_action_score:
            return {
                'success': True,
                'target_agent': 'analysis',
                'reasoning': 'Action verbs indicate viewing/analyzing data',
                'confidence': 'medium'
            }
        elif management_action_score > analysis_action_score:
            return {
                'success': True,
                'target_agent': 'management',
                'reasoning': 'Action verbs indicate creating/modifying data',
                'confidence': 'medium'
            }
        else:
            # Default to analysis for ambiguous cases since most queries are for viewing data
            return {
                'success': True,
                'target_agent': 'analysis',
                'reasoning': 'Ambiguous request, defaulting to analysis agent for data viewing',
                'confidence': 'low'
            } 