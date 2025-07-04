from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from flask import current_app

from app.mcp.unified_schema import EntityType, UnifiedQuery, TOOL_CAPABILITIES
from app.llm import LLMManager


@dataclass
class AgentDecision:
    """Represents a decision made by the intelligent agent"""
    action_type: str  # analyze, create, update, delete, search, report
    entities_needed: List[EntityType]
    tools_to_use: List[str]
    filters: Dict[str, Any]
    reasoning: str
    confidence: float
    additional_context: Dict[str, Any]


@dataclass
class QueryAnalysis:
    """Analysis of a user query"""
    intent: str
    entities_mentioned: List[str]
    actions_implied: List[str]
    temporal_references: List[str]
    specific_filters: Dict[str, Any]
    context_clues: List[str]


class AgentIntelligence:
    """Intelligent decision-making system for agents"""
    
    def __init__(self):
        self.llm_manager = LLMManager()
    
    def analyze_query_and_decide(self, query: str, project_context: Dict[str, Any], conversation_history: List[Dict[str, Any]] = None) -> AgentDecision:
        """Analyze user query and make intelligent decisions about actions and tools"""
        
        # First, analyze the query structure and intent
        query_analysis = self._analyze_query_structure(query, conversation_history)
        
        # Determine available tools for the project
        available_tools = self._get_available_tools(project_context)
        
        # Use LLM to make intelligent decisions
        decision_data = self._llm_decision_making(query, query_analysis, available_tools, project_context)
        
        # Create the agent decision
        decision = AgentDecision(
            action_type=decision_data.get('action_type', 'analyze'),
            entities_needed=self._parse_entities_needed(decision_data.get('entities_needed', [])),
            tools_to_use=decision_data.get('tools_to_use', available_tools),
            filters=decision_data.get('filters', {}),
            reasoning=decision_data.get('reasoning', 'LLM-based decision'),
            confidence=decision_data.get('confidence', 0.7),
            additional_context=decision_data.get('additional_context', {})
        )
        
        return decision
    
    def create_unified_query(self, decision: AgentDecision) -> UnifiedQuery:
        """Create a unified query based on the agent decision"""
        return UnifiedQuery(
            entities=decision.entities_needed,
            filters=decision.filters,
            include_related=self._determine_related_entities(decision.entities_needed),
            limit=decision.additional_context.get('limit'),
            sort_by=decision.additional_context.get('sort_by'),
            sort_order=decision.additional_context.get('sort_order', 'asc')
        )
    
    def _analyze_query_structure(self, query: str, conversation_history: List[Dict[str, Any]] = None) -> QueryAnalysis:
        """Analyze the structure and intent of the user query"""
        query_lower = query.lower()
        
        # Extract entities mentioned
        entities_mentioned = []
        entity_keywords = {
            'work items': ['work item', 'task', 'issue', 'story', 'bug', 'ticket', 'epic'],
            'sprints': ['sprint', 'iteration', 'cycle'],
            'users': ['user', 'assignee', 'team member', 'developer'],
            'repositories': ['repo', 'repository', 'code', 'github'],
            'pull requests': ['pr', 'pull request', 'merge request'],
            'commits': ['commit', 'change', 'version']
        }
        
        for entity, keywords in entity_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                entities_mentioned.append(entity)
        
        # Extract action implications
        actions_implied = []
        action_keywords = {
            'analyze': ['analyze', 'show', 'display', 'view', 'report', 'status', 'health', 'performance'],
            'create': ['create', 'add', 'new', 'generate', 'make'],
            'update': ['update', 'edit', 'change', 'modify', 'fix'],
            'delete': ['delete', 'remove', 'cancel'],
            'search': ['find', 'search', 'look for', 'get', 'fetch'],
            'assign': ['assign', 'reassign', 'allocate'],
            'move': ['move', 'transition', 'change status'],
            'plan': ['plan', 'schedule', 'organize']
        }
        
        for action, keywords in action_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                actions_implied.append(action)
        
        # Extract temporal references
        temporal_references = []
        temporal_keywords = ['today', 'yesterday', 'this week', 'last week', 'this month', 'last month', 
                           'current', 'recent', 'latest', 'past', 'upcoming', 'next']
        
        for keyword in temporal_keywords:
            if keyword in query_lower:
                temporal_references.append(keyword)
        
        # Extract specific filters (but be careful about "backlog")
        specific_filters = {}
        
        # Status filters - but NOT for "backlog" since it's not a JIRA status
        status_keywords = ['todo', 'in progress', 'done', 'blocked', 'open', 'closed']
        for status in status_keywords:
            if status in query_lower:
                specific_filters['status'] = status
        
        # Don't add status filter for "backlog" - backlog refers to all project items, not a specific status
        # The term "backlog" in project management means "items to be worked on", not a status
        
        # Priority filters
        priority_keywords = ['high', 'low', 'critical', 'medium']
        for priority in priority_keywords:
            if priority in query_lower:
                specific_filters['priority'] = priority
        
        # Context clues from conversation history
        context_clues = []
        if conversation_history:
            # Extract context from recent messages
            for msg in conversation_history[-3:]:  # Last 3 messages
                content = msg.get('content', '').lower()
                if 'project' in content:
                    context_clues.append('project_context')
                if any(entity in content for entity_list in entity_keywords.values() for entity in entity_list):
                    context_clues.append('entity_continuity')
        
        return QueryAnalysis(
            intent=self._determine_primary_intent(actions_implied),
            entities_mentioned=entities_mentioned,
            actions_implied=actions_implied,
            temporal_references=temporal_references,
            specific_filters=specific_filters,
            context_clues=context_clues
        )
    
    def _determine_primary_intent(self, actions_implied: List[str]) -> str:
        """Determine the primary intent from multiple actions"""
        # Priority order for actions
        priority_order = ['create', 'update', 'delete', 'assign', 'move', 'plan', 'search', 'analyze']
        
        for action in priority_order:
            if action in actions_implied:
                return action
        
        return 'analyze'  # Default intent
    
    def _get_available_tools(self, project_context: Dict[str, Any]) -> List[str]:
        """Get list of available tools for the project"""
        available_tools = []
        for tool in project_context.get('tools', []):
            tool_type = tool.get('type')
            if tool_type in TOOL_CAPABILITIES:
                available_tools.append(tool_type)
        return available_tools
    
    def _llm_decision_making(self, query: str, analysis: QueryAnalysis, available_tools: List[str], project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to make intelligent decisions about actions and tools"""
        
        system_prompt = self._get_decision_making_prompt(available_tools, project_context)
        
        user_prompt = f"""
Analyze this user query and make intelligent decisions about what actions to take and which tools to use.

User Query: "{query}"

Query Analysis:
- Primary Intent: {analysis.intent}
- Entities Mentioned: {', '.join(analysis.entities_mentioned)}
- Actions Implied: {', '.join(analysis.actions_implied)}
- Temporal References: {', '.join(analysis.temporal_references)}
- Specific Filters: {analysis.specific_filters}
- Context Clues: {', '.join(analysis.context_clues)}

Available Tools: {', '.join(available_tools)}

IMPORTANT FILTER RULES:
- "backlog" is NOT a JIRA status - it refers to all project work items
- Valid JIRA statuses are: "To Do", "In Progress", "Done", "Blocked", etc.
- When user asks for "backlog items", they want ALL work items, not items with status "backlog"
- Only use status filters for actual JIRA statuses like "To Do", "In Progress", "Done"

Based on this analysis, provide a JSON response with your decisions:

{{
  "action_type": "analyze|create|update|delete|search|report",
  "entities_needed": ["work_item", "sprint", "user", "repository", "pull_request", "commit"],
  "tools_to_use": ["jira", "github", "azure_devops"],
  "filters": {{"priority": "...", "assignee": "...", "date_range": "..."}},
  "reasoning": "Explanation of why these decisions were made",
  "confidence": 0.8,
  "additional_context": {{"limit": 50, "sort_by": "created_date", "sort_order": "desc"}}
}}

Consider:
1. What information does the user actually need?
2. Which tools contain that information?
3. What filters would be most relevant? (Remember: NO status="backlog")
4. What's the most efficient way to get the answer?
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.llm_manager.generate_response(
                messages=messages,
                model="gpt-3.5-turbo",
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse JSON response
            import json
            import re
            
            content = response.content.strip()
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                decision_data = json.loads(json_match.group(0))
                
                # Post-process to remove any incorrect status filters
                if 'filters' in decision_data and isinstance(decision_data['filters'], dict):
                    if decision_data['filters'].get('status') == 'backlog':
                        del decision_data['filters']['status']
                        decision_data['reasoning'] += " (Removed invalid 'backlog' status filter)"
                
                return decision_data
            else:
                return self._fallback_decision_making(analysis, available_tools)
                
        except Exception as e:
            current_app.logger.error(f"Error in LLM decision making: {str(e)}")
            return self._fallback_decision_making(analysis, available_tools)
    
    def _get_decision_making_prompt(self, available_tools: List[str], project_context: Dict[str, Any]) -> str:
        """Get system prompt for decision making"""
        return f"""You are an intelligent project management assistant that analyzes user queries and determines the best course of action.

Your goal is to understand what the user wants and decide:
1. What type of action needs to be performed
2. What entities/data need to be retrieved
3. Which tools should be used to get that data
4. What filters should be applied
5. How to present the information

Available Tools and Their Capabilities:
{self._format_tool_capabilities(available_tools)}

Project Context:
- Project: {project_context.get('project', {}).get('name', 'Unknown')}
- Key: {project_context.get('project', {}).get('key', 'Unknown')}
- Tools Configured: {len(project_context.get('tools', []))}

Decision-Making Principles:
1. **Efficiency**: Use the minimum number of tools needed to answer the query
2. **Relevance**: Only fetch data that's directly relevant to the user's question
3. **Completeness**: Ensure all necessary information is retrieved to provide a complete answer
4. **Performance**: Consider tool rate limits and response times
5. **User Intent**: Focus on what the user actually wants to know, not just what they said

Action Types:
- **analyze**: Generate insights, reports, status updates, health checks
- **create**: Create new work items, sprints, projects
- **update**: Modify existing items, change status, assign users
- **delete**: Remove items, cancel sprints
- **search**: Find specific items, users, or information
- **report**: Generate detailed reports and dashboards

Entity Types:
- **work_item**: Tasks, issues, stories, bugs, epics
- **sprint**: Sprints, iterations, cycles
- **user**: Team members, assignees, developers
- **repository**: Code repositories, projects
- **pull_request**: Pull requests, merge requests
- **commit**: Code commits, changes

Always provide clear reasoning for your decisions and consider the user's likely follow-up questions."""
    
    def _format_tool_capabilities(self, available_tools: List[str]) -> str:
        """Format tool capabilities for the prompt"""
        formatted = ""
        for tool_name in available_tools:
            if tool_name in TOOL_CAPABILITIES:
                capabilities = TOOL_CAPABILITIES[tool_name]
                formatted += f"\n- **{tool_name.upper()}**: "
                formatted += f"Entities: {', '.join([e.value for e in capabilities.supported_entities])}, "
                formatted += f"Operations: {', '.join(capabilities.supported_operations)}"
        return formatted
    
    def _fallback_decision_making(self, analysis: QueryAnalysis, available_tools: List[str]) -> Dict[str, Any]:
        """Fallback decision making when LLM fails"""
        # Map entities mentioned to entity types
        entity_mapping = {
            'work items': [EntityType.WORK_ITEM],
            'sprints': [EntityType.SPRINT],
            'users': [EntityType.USER],
            'repositories': [EntityType.REPOSITORY],
            'pull requests': [EntityType.PULL_REQUEST],
            'commits': [EntityType.COMMIT]
        }
        
        entities_needed = []
        for entity in analysis.entities_mentioned:
            if entity in entity_mapping:
                entities_needed.extend(entity_mapping[entity])
        
        # If no entities mentioned, default to work items
        if not entities_needed:
            entities_needed = [EntityType.WORK_ITEM]
        
        # Use the specific filters from analysis, but remove any incorrect ones
        filters = analysis.specific_filters.copy()
        
        # Remove 'status': 'backlog' since backlog is not a JIRA status
        if filters.get('status') == 'backlog':
            del filters['status']
        
        # Generate appropriate reasoning
        reasoning = f"Fallback decision: {analysis.intent} action for {', '.join([e.value for e in entities_needed])}"
        if 'backlog' in analysis.entities_mentioned or any('backlog' in entity for entity in analysis.entities_mentioned):
            reasoning = "User wants to view project backlog items (all work items in the project)"
        
        return {
            'action_type': analysis.intent,
            'entities_needed': [e.value for e in entities_needed],
            'tools_to_use': available_tools,
            'filters': filters,
            'reasoning': reasoning,
            'confidence': 0.6,
            'additional_context': {'limit': 50, 'sort_by': 'updated_date', 'sort_order': 'desc'}
        }
    
    def _parse_entities_needed(self, entity_strings: List[str]) -> List[EntityType]:
        """Parse entity strings to EntityType enums"""
        entities = []
        for entity_str in entity_strings:
            try:
                entities.append(EntityType(entity_str))
            except ValueError:
                current_app.logger.warning(f"Unknown entity type: {entity_str}")
        return entities
    
    def _determine_related_entities(self, main_entities: List[EntityType]) -> List[EntityType]:
        """Determine what related entities should be included"""
        related = []
        
        if EntityType.WORK_ITEM in main_entities:
            related.extend([EntityType.USER, EntityType.SPRINT])
        
        if EntityType.SPRINT in main_entities:
            related.append(EntityType.WORK_ITEM)
        
        if EntityType.PULL_REQUEST in main_entities:
            related.extend([EntityType.USER, EntityType.COMMIT, EntityType.REPOSITORY])
        
        if EntityType.REPOSITORY in main_entities:
            related.extend([EntityType.PULL_REQUEST, EntityType.COMMIT])
        
        # Remove duplicates and main entities
        related = list(set(related) - set(main_entities))
        
        return related


# Global intelligence instance
agent_intelligence = AgentIntelligence() 