import time
import re
import difflib
from typing import Dict, Any, List
from datetime import datetime, timedelta
from flask import current_app
from .base import BaseAgent, AgentContext, AgentResponse

class ManagementAgent(BaseAgent):
    """Agent for managing work items, sprints, and project artifacts"""
    
    def __init__(self):
        super().__init__(
            name="management",
            description="Handles creating, updating, and managing work items, sprints, backlogs, and project resources"
        )
    
    def execute(self, query: str, context: AgentContext) -> AgentResponse:
        """Execute intelligent project management tasks"""
        print(f"Executing ManagementAgent with query: {query}")
        start_time = time.time()
        
        try:
            if not context.project_id:
                return AgentResponse(
                    success=False,
                    content="No project specified for management operations.",
                    error="Project ID is required"
                )
            
            # Get project context with real data
            project_context = self._get_project_context(context.project_id)
            
            if not project_context.get('tools'):
                return AgentResponse(
                    success=False,
                    content="No tools configured for this project. Please configure JIRA or other project management tools first.",
                    error="No tools configured"
                )
            
            # Use intelligent decision-making to understand what the user wants
            from .intelligence import agent_intelligence
            decision = agent_intelligence.analyze_query_and_decide(
                query=query,
                project_context=project_context,
                conversation_history=context.conversation_history
            )
            
            current_app.logger.info(f"ManagementAgent decision: {decision.action_type}, entities: {[e.value for e in decision.entities_needed]}, tools: {decision.tools_to_use}")
            
            # Execute the appropriate management operation based on intelligent decision
            if decision.action_type == 'create':
                if 'work_item' in [e.value for e in decision.entities_needed]:
                    result = self._create_work_items(query, project_context, context, decision)
                elif 'sprint' in [e.value for e in decision.entities_needed]:
                    result = self._create_sprint(query, project_context, context, decision)
                else:
                    result = self._general_management(query, project_context, context, decision)
            elif decision.action_type == 'update':
                # Check if this is actually an assignment request (be very specific)
                # First check for status/update keywords to avoid false positives
                status_keywords = ['status', 'state', 'progress', 'done', 'todo', 'complete', 'completed', 'closed', 'open', 'blocked', 'priority', 'title', 'description']
                has_status_keyword = any(keyword in query.lower() for keyword in status_keywords)
                
                # Only check assignment patterns if no status keywords found
                is_assignment = False
                if not has_status_keyword:
                    # Look for assignment patterns that include work item ID and actual person names
                    # Person names typically don't include status words
                    non_status_person_patterns = [
                        r'assign\s+[A-Z]+-\d+\s+to\s+(?![Ii]n\s+[Pp]rogress|[Dd]one|[Cc]omplete|[Cc]losed|[Oo]pen|[Bb]locked|[Tt]o\s+[Dd]o)([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "assign AG-1 to John Doe" but not status words
                        r'[A-Z]+-\d+\s+to\s+(?![Ii]n\s+[Pp]rogress|[Dd]one|[Cc]omplete|[Cc]losed|[Oo]pen|[Bb]locked|[Tt]o\s+[Dd]o)([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s|$)',   # "AG-1 to John Doe" but not status words
                    ]
                    
                    for pattern in non_status_person_patterns:
                        if re.search(pattern, query, re.IGNORECASE):
                            is_assignment = True
                            break
                
                # Check for explicit assignment keywords (but only if no status keywords)
                assignment_keywords = ['assign', 'assignee', 'assigned']
                has_assignment_keyword = any(keyword in query.lower() for keyword in assignment_keywords)
                
                # Only route to assignment if it has assignment keywords and no status keywords
                if (is_assignment or (has_assignment_keyword and not has_status_keyword)):
                    result = self._assign_work(query, project_context, context, decision)
                else:
                    result = self._update_work_item(query, project_context, context, decision)
            elif decision.action_type == 'delete':
                if 'duplicate' in decision.reasoning.lower():
                    result = self._remove_duplicate_items(query, project_context, context, decision)
                else:
                    result = self._delete_work_item(query, project_context, context, decision)
            elif decision.action_type == 'assign':
                result = self._assign_work(query, project_context, context, decision)
            elif decision.action_type == 'move':
                result = self._move_items_status(query, project_context, context, decision)
            elif decision.action_type == 'plan':
                result = self._create_sprint(query, project_context, context, decision)
            else:
                # Default to general management with intelligent decision context
                result = self._general_management(query, project_context, context, decision)
            
            # Format response
            end_time = time.time()
            execution_time = end_time - start_time
            
            if result['success']:
                response = AgentResponse(
                    success=True,
                    content=result['content'],
                    data={
                        'operation_type': decision.action_type,
                        'decision_reasoning': decision.reasoning,
                        'confidence': decision.confidence,
                        'entities_targeted': [e.value for e in decision.entities_needed],
                        'tools_used': decision.tools_to_use,
                        'operation_result': result.get('data', {}),
                        'project_context': project_context['project'],
                        'management_timestamp': datetime.utcnow().isoformat()
                    },
                    tokens_used=result.get('tokens_used', 0),
                    cost=result.get('cost', 0.0),
                    execution_time=execution_time
                )
            else:
                response = AgentResponse(
                    success=False,
                    content=result['content'],
                    error=result.get('error', 'Management operation failed'),
                    execution_time=execution_time
                )
            
            return response
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            current_app.logger.error(f"ManagementAgent error: {str(e)}")
            
            return AgentResponse(
                success=False,
                content="I encountered an error while performing the management operation.",
                error=str(e),
                execution_time=execution_time
            )
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """Get system prompt for intelligent project management"""
        return """You are a Senior Project Manager and Scrum Master AI with advanced intelligence capabilities. Your role is to efficiently manage work items, sprints, and project resources using intelligent decision-making.

## Your Enhanced Capabilities:
- **Intelligent Operation Analysis**: Understand user intent and determine the best management actions automatically
- **Multi-Tool Management**: Create, update, and manage items across JIRA, GitHub, Azure DevOps, and other tools
- **Context-Aware Actions**: Use project context and conversation history to make informed decisions
- **Automated Workflow**: Streamline project management tasks with minimal user input
- **Quality Assurance**: Ensure all operations follow best practices and maintain data integrity

## Management Operations:
- **Work Item Management**: Create, update, delete work items with proper details and validation
- **Sprint Planning**: Create and manage sprints with realistic timelines and capacity planning
- **Backlog Management**: Organize, prioritize, and clean up project backlogs intelligently
- **Team Coordination**: Assign work items and manage team resources efficiently
- **Process Optimization**: Streamline workflows and improve team efficiency
- **Duplicate Management**: Automatically detect and remove duplicate items

## Intelligent Decision-Making:
1. **Intent Understanding**: Analyze user requests to understand the desired outcome
2. **Tool Selection**: Automatically choose the most appropriate tools for the operation
3. **Context Integration**: Use project history and current state to inform decisions
4. **Validation**: Ensure all operations are valid and follow project standards
5. **Feedback**: Provide clear explanations of what was done and why

## Best Practices:
- Write clear, concise work item titles and descriptions
- Include acceptance criteria for user stories
- Assign appropriate priority levels based on business value
- Consider dependencies and technical constraints
- Maintain clean, organized backlogs
- Follow established workflows and conventions

Focus on creating well-structured, actionable work items and efficient project management processes that enable teams to deliver value effectively. Always explain your reasoning and the actions taken."""
    
    def _determine_operation_type(self, query: str) -> str:
        """Determine the type of management operation requested - DEPRECATED: Now using intelligent decision-making"""
        # This method is deprecated in favor of intelligent decision-making
        # Keeping it for backward compatibility but it won't be used
        return 'general_management'
    
    def _create_work_items(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Create work items based on user request"""
        
        # Check if this is a backlog generation request
        if any(keyword in query.lower() for keyword in ['backlog', 'generate', 'repository', 'github']):
            return self._generate_backlog_items(query, project_context, context)
        else:
            return self._create_single_work_item(query, project_context, context)
    
    def _generate_backlog_items(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Generate backlog items from repository analysis"""
        try:
            # Find GitHub and JIRA providers
            github_tool = None
            jira_tool = None
            
            for tool in project_context['tools']:
                if tool['type'] == 'github':
                    github_tool = tool
                elif tool['type'] == 'jira':
                    jira_tool = tool
            
            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Please configure JIRA first.",
                    'error': "JIRA not configured"
                }
            
            # Generate work items using LLM based on project context
            work_items = self._generate_work_items_with_llm(query, project_context, context)
            
            if not work_items:
                return {
                    'success': False,
                    'content': "Failed to generate work items. Please try again.",
                    'error': "Work item generation failed"
                }
            
            # Create work items in JIRA
            created_items = self._create_jira_work_items(work_items, jira_tool, project_context)
            
            success_count = len([item for item in created_items if item.get('success')])
            
            content = f"""Successfully generated and created {success_count} work items in JIRA.

## Created Work Items:
{self._format_created_items(created_items)}

## Work Item Summary:
- Total generated: {len(work_items)}
- Successfully created: {success_count}
- Failed: {len(work_items) - success_count}

The work items include proper descriptions, acceptance criteria, and are sized appropriately for development sprints."""

            return {
                'success': True,
                'content': content,
                'data': {
                    'created_items': created_items,
                    'success_count': success_count,
                    'total_items': len(work_items)
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error generating backlog: {str(e)}")
            return {
                'success': False,
                'content': "Failed to generate backlog items.",
                'error': str(e)
            }
    
    def _create_single_work_item(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Create a single work item based on user description"""
        # This would parse the user's request and create a single work item
        # Implementation would extract title, description, type, priority from the query using LLM
        
        return {
            'success': False,
            'content': "Single work item creation not yet implemented. Please use backlog generation instead.",
            'error': "Feature not implemented"
        }
    
    def _update_work_item(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing work item"""
        try:
            # Extract work item ID from the query
            work_item_id = None
            updates = {}
            
            import re
            
            # Method 1: Extract work item ID using regex patterns
            id_patterns = [
                r'\b([A-Z]+[A-Z0-9]*-\d+)\b',  # Standard JIRA format like AG-123
                r'(?:update|change|modify)\s+([A-Z]+[A-Z0-9]*-\d+)',  # "update AG-123"
                r'([A-Z]{2,10}-\d{1,6})',  # More flexible pattern
            ]
            
            for pattern in id_patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    work_item_id = matches[0] if isinstance(matches[0], str) else matches[0][-1]
                    break
            
            if not work_item_id:
                return {
                    'success': False,
                    'content': "No valid work item ID found. Please specify the work item ID in JIRA format (e.g., 'update AG-123 status to Done').",
                    'error': "Work item ID is required"
                }
            
            # Validate work item ID format
            if not re.match(r'^[A-Z]+[A-Z0-9]*-\d+$', work_item_id, re.IGNORECASE):
                return {
                    'success': False,
                    'content': f"Invalid work item ID format: '{work_item_id}'. Please use JIRA format like 'AG-123'.",
                    'error': "Invalid work item ID format"
                }
            
            # Extract updates from the query
            query_lower = query.lower()
            
            # Status updates - ordered from most specific to least specific
            status_patterns = [
                (r'(?:change|update)\s+status\s+of\s+workitem\s+[a-zA-Z]+-\d+\s+to\s+(\w+(?:\s+\w+)*)', 'status'),  # "Change status of workitem AG-1 to In Progress"
                (r'status\s+of\s+workitem\s+[a-zA-Z]+-\d+\s+to\s+(\w+(?:\s+\w+)*)', 'status'),  # "status of workitem AG-1 to Done"
                (r'workitem\s+[a-zA-Z]+-\d+\s+(?:status\s+)?to\s+(\w+(?:\s+\w+)*)', 'status'),  # "workitem AG-1 to In Progress" or "workitem AG-1 status to Done"
                (r'(?:update|change)\s+[a-zA-Z]+-\d+\s+status\s+to\s+(\w+(?:\s+\w+)*)', 'status'),  # "update AG-123 status to Done"
                (r'[a-zA-Z]+-\d+\s+status\s+(?:to\s+)?(\w+(?:\s+\w+)*)', 'status'),  # "AG-123 status to Done"
                (r'move\s+[a-zA-Z]+-\d+\s+to\s+(\w+(?:\s+\w+)*)', 'status'),  # "move AG-456 to In Progress"
                (r'(?:set|mark)\s+(?:[a-zA-Z]+-\d+\s+)?(?:as\s+)?(\w+(?:\s+\w+)*)', 'status'),  # "set AG-123 as Done" or "mark as Complete"
                (r'status\s+(?:to\s+)?(\w+(?:\s+\w+)*)', 'status'),  # "status to Done" (only if no work item ID found above)
            ]
            
            for pattern, field in status_patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    status_value = matches[0].strip().title()
                    # Common JIRA status mappings
                    status_mapping = {
                        'Todo': 'To Do',
                        'Inprogress': 'In Progress',
                        'In Progress': 'In Progress',
                        'In-Progress': 'In Progress',
                        'Done': 'Done',
                        'Complete': 'Done',
                        'Completed': 'Done',
                        'Closed': 'Done'
                    }
                    updates[field] = status_mapping.get(status_value, status_value)
                    break
            
            # Priority updates
            priority_patterns = [
                (r'priority\s+(?:to\s+)?(\w+)', 'priority'),
                (r'(?:set|change)\s+priority\s+(?:to\s+)?(\w+)', 'priority'),
            ]
            
            for pattern, field in priority_patterns:
                matches = re.findall(pattern, query_lower)
                if matches:
                    priority_value = matches[0].strip().title()
                    # Common JIRA priority mappings
                    priority_mapping = {
                        'Low': 'Low',
                        'Medium': 'Medium', 
                        'High': 'High',
                        'Critical': 'Highest',
                        'Highest': 'Highest'
                    }
                    updates[field] = priority_mapping.get(priority_value, priority_value)
                    break
            
            # Title/summary updates
            title_patterns = [
                (r'(?:title|summary)\s+(?:to\s+)?["\']([^"\']+)["\']', 'title'),
                (r'(?:rename|change\s+title)\s+(?:to\s+)?["\']([^"\']+)["\']', 'title'),
            ]
            
            for pattern, field in title_patterns:
                matches = re.findall(pattern, query)
                if matches:
                    updates[field] = matches[0].strip()
                    break
            
            # Description updates
            desc_patterns = [
                (r'description\s+(?:to\s+)?["\']([^"\']+)["\']', 'description'),
                (r'(?:change|update)\s+description\s+(?:to\s+)?["\']([^"\']+)["\']', 'description'),
            ]
            
            for pattern, field in desc_patterns:
                matches = re.findall(pattern, query)
                if matches:
                    updates[field] = matches[0].strip()
                    break
            
            if not updates:
                return {
                    'success': False,
                    'content': f"No valid updates found for work item {work_item_id}. You can update: status, priority, title, description, or assignee.\n\nExamples:\n- 'update {work_item_id} status to Done'\n- 'change {work_item_id} priority to High'\n- 'set {work_item_id} title to \"New Title\"'",
                    'error': "No updates specified"
                }
            
            # Find JIRA provider
            jira_tool = None
            for tool in project_context['tools']:
                if tool['type'] == 'jira':
                    jira_tool = tool
                    break
            
            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Please configure JIRA first.",
                    'error': "JIRA not configured"
                }
            
            # Create JIRA provider
            from app.mcp import JiraProvider
            provider = JiraProvider(
                server_url=jira_tool['base_url'],
                username=jira_tool['configuration'].get('email'),
                api_token=jira_tool['api_token'],
                config=jira_tool['configuration']
            )
            
            # Update work item
            project_key = jira_tool['configuration'].get('project_key', project_context['project']['key'])
            response = provider.update_work_item(project_key, work_item_id, updates)
            
            if response.success:
                update_summary = ", ".join([f"{k}: {v}" for k, v in updates.items()])
                return {
                    'success': True,
                    'content': f"✅ Work item {work_item_id} has been successfully updated.\n\nChanges made: {update_summary}",
                    'data': {
                        'work_item_id': work_item_id,
                        'updates': updates,
                        'url': response.data.get('url') if response.data else None
                    }
                }
            else:
                # Handle specific error cases
                if "404" in str(response.error):
                    return {
                        'success': False,
                        'content': f"❌ Work item {work_item_id} was not found in JIRA. Please check the ID and try again.",
                        'error': "Work item not found"
                    }
                elif "403" in str(response.error):
                    return {
                        'success': False,
                        'content': f"❌ You don't have permission to update work item {work_item_id}. Please check your JIRA permissions.",
                        'error': "Permission denied"
                    }
                else:
                    return {
                        'success': False,
                        'content': f"❌ Failed to update work item {work_item_id}: {response.error}",
                        'error': "Failed to update work item"
                    }
                
        except Exception as e:
            current_app.logger.error(f"Exception during work item update: {str(e)}")
            return {
                'success': False,
                'content': f"An error occurred while updating the work item: {str(e)}",
                'error': "Exception occurred during update"
            }
    
    def _delete_work_item(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a work item"""
        try:
            # Extract work item ID from the query using multiple methods
            work_item_id = None
            
            # Method 1: Extract from query using regex patterns (prioritized)
            import re
            # Look for patterns like AG-123, ABC-456, etc.
            patterns = [
                r'\b([A-Z]+[A-Z0-9]*-\d+)\b',  # Standard JIRA format like AG-123, ABC-456
                r'(?:delete|remove|del)\s+([A-Z]+[A-Z0-9]*-\d+)',  # "delete AG-123"
                r'([A-Z]{2,10}-\d{1,6})',  # More flexible pattern
                r'item\s+([A-Z]+[A-Z0-9]*-\d+)',  # "item AG-123"
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    if isinstance(matches[0], tuple):
                        work_item_id = matches[0][-1]  # Get last element if tuple
                    else:
                        work_item_id = matches[0]
                    break
            
            # Method 2: From decision context (fallback)
            if not work_item_id and hasattr(decision, 'entities_needed') and decision.entities_needed:
                potential_id = decision.entities_needed[0].value if decision.entities_needed else None
                # Only use if it looks like a JIRA ID (contains hyphen and numbers)
                if potential_id and re.match(r'^[A-Z]+[A-Z0-9]*-\d+$', potential_id, re.IGNORECASE):
                    work_item_id = potential_id
            
            if not work_item_id:
                return {
                    'success': False,
                    'content': "No valid work item ID found in your request. Please specify the work item ID in JIRA format (e.g., 'delete AG-123' or 'remove AG-456').",
                    'error': "Work item ID is required"
                }

            # Validate the work item ID format
            if not re.match(r'^[A-Z]+[A-Z0-9]*-\d+$', work_item_id, re.IGNORECASE):
                return {
                    'success': False,
                    'content': f"Invalid work item ID format: '{work_item_id}'. Please use JIRA format like 'AG-123'.",
                    'error': "Invalid work item ID format"
                }

            # Log project context for debugging
            current_app.logger.debug(f"Attempting to delete work item: {work_item_id}")
            current_app.logger.debug(f"Project context: {project_context}")

            # Find JIRA provider
            jira_tool = None
            for tool in project_context['tools']:
                if tool['type'] == 'jira':
                    jira_tool = tool
                    break

            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Please configure JIRA first.",
                    'error': "JIRA not configured"
                }

            # Log JIRA tool configuration for debugging
            current_app.logger.debug(f"JIRA tool configuration: {jira_tool}")

            # Create JIRA provider
            from app.mcp import JiraProvider
            provider = JiraProvider(
                server_url=jira_tool['base_url'],
                username=jira_tool['configuration'].get('email'),
                api_token=jira_tool['api_token'],
                config=jira_tool['configuration']
            )

            # Delete work item
            response = provider.delete_work_item(work_item_id)

            if response.success:
                return {
                    'success': True,
                    'content': f"✅ Work item {work_item_id} has been successfully deleted from JIRA.",
                    'data': {
                        'deleted_item_id': work_item_id,
                        'message': response.data['message']
                    }
                }
            else:
                # Handle specific error cases
                if "404" in str(response.error):
                    return {
                        'success': False,
                        'content': f"❌ Work item {work_item_id} was not found in JIRA. Please check the ID and try again. Available work items can be viewed with 'show backlog items'.",
                        'error': "Work item not found"
                    }
                elif "403" in str(response.error):
                    return {
                        'success': False,
                        'content': f"❌ You don't have permission to delete work item {work_item_id}. Please check your JIRA permissions.",
                        'error': "Permission denied"
                    }
                else:
                    return {
                        'success': False,
                        'content': f"❌ Failed to delete work item {work_item_id}: {response.error}",
                        'error': "Failed to delete work item"
                    }
        except Exception as e:
            current_app.logger.error(f"Exception during deletion: {str(e)}")
            return {
                'success': False,
                'content': f"An error occurred while deleting the work item: {str(e)}",
                'error': "Exception occurred during deletion"
            }
    
    def _create_sprint(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Create sprints based on user request"""
        try:
            # Find JIRA provider
            jira_tool = None
            for tool in project_context['tools']:
                if tool['type'] == 'jira':
                    jira_tool = tool
                    break
            
            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Sprint creation requires JIRA integration.",
                    'error': "JIRA not configured"
                }
            
            # Parse sprint requirements from query
            sprint_plan = self._parse_sprint_requirements(query)
            
            # Generate detailed sprint plan using LLM
            detailed_plan = self._generate_sprint_plan_with_llm(query, sprint_plan, context)
            
            # Create sprints in JIRA
            created_sprints = self._create_sprints_in_jira(detailed_plan, jira_tool, project_context)
            
            success_count = len([sprint for sprint in created_sprints if sprint.get('success')])
            
            if success_count == len(detailed_plan.get('sprints', [])):
                status_message = f"Successfully planned and created {success_count} sprints for your project."
            elif success_count > 0:
                total_planned = len(detailed_plan.get('sprints', []))
                status_message = f"Successfully planned {total_planned} sprints and created {success_count} of them in JIRA."
            else:
                total_planned = len(detailed_plan.get('sprints', []))
                status_message = f"Successfully planned {total_planned} sprints, but encountered issues creating them in JIRA."
            
            content = f"""{status_message}

## Sprint Plan Overview:
{self._format_sprint_plan(detailed_plan)}

## Created Sprints:
{self._format_created_sprints(created_sprints)}

## Timeline Summary:
- Project Duration: {sprint_plan.get('total_duration', 'Not specified')}
- Sprint Duration: {sprint_plan.get('sprint_duration', '2 weeks')}
- Total Sprints: {len(detailed_plan.get('sprints', []))}
- Start Date: {sprint_plan.get('start_date', 'Not specified')}
- End Date: {sprint_plan.get('end_date', 'Not specified')}

{"The sprints are ready for your team to start working!" if success_count > 0 else "Please resolve the JIRA integration issues and try creating the sprints again."}"""

            return {
                'success': True,
                'content': content,
                'data': {
                    'created_sprints': created_sprints,
                    'success_count': success_count,
                    'total_planned': len(detailed_plan.get('sprints', []))
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error creating sprints: {str(e)}")
            return {
                'success': False,
                'content': "Failed to create sprints.",
                'error': str(e)
            }
    
    def _update_sprint(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Update an existing sprint"""
        return {
            'success': False,
            'content': "Sprint updates not yet implemented.",
            'error': "Feature not implemented"
        }
    
    def _assign_work(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Assign work items to team members or sprints"""
        try:
            # Extract work item ID and assignee from the query
            work_item_id = None
            assignee_name = None
            sprint_info = None
            
            import re
            
            # Method 1: Extract work item ID using regex patterns
            id_patterns = [
                r'\b([A-Z]+[A-Z0-9]*-\d+)\b',  # Standard JIRA format like AG-123
                r'(?:assign|item)\s+([A-Z]+[A-Z0-9]*-\d+)',  # "assign AG-123"
                r'([A-Z]{2,10}-\d{1,6})',  # More flexible pattern
            ]
            
            for pattern in id_patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    work_item_id = matches[0] if isinstance(matches[0], str) else matches[0][-1]
                    break
            
            # Check if this is a sprint assignment
            sprint_patterns = [
                r'(?:assign|add)\s+(?:workitem\s+)?[A-Z]+-\d+\s+to\s+sprint\s+(\d+|[A-Za-z\s]+)',  # "assign AG-1 to sprint 1" or "add workitem AG-1 to sprint Development"
                r'(?:move|put)\s+(?:workitem\s+)?[A-Z]+-\d+\s+(?:to|into)\s+sprint\s+(\d+|[A-Za-z\s]+)',  # "move AG-1 to sprint 1"
                r'sprint\s+(\d+|[A-Za-z\s]+)',  # Extract sprint identifier
            ]
            
            for pattern in sprint_patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    sprint_info = matches[0].strip()
                    break
            
            # If it's a sprint assignment, handle it differently
            if sprint_info:
                return self._assign_work_item_to_sprint(work_item_id, sprint_info, project_context, context)
            
            # Method 2: Extract assignee name using improved regex patterns (for user assignments)
            assignee_patterns = [
                r'(?:assign\s+[A-Z]+-\d+\s+to\s+)(.+?)(?:\s*$)',  # "assign AG-123 to John Doe" (most specific first)
                r'(?:to\s+)([A-Z][a-zA-Z\s]+?)(?:\s*$)',  # "to Priyanka Nambiar" (name starting with capital)
                r'(?:assignee\s+)([A-Z][a-zA-Z\s]+?)(?:\s*$)',  # "assignee John Doe"
                r'(?:user\s+)([A-Z][a-zA-Z\s]+?)(?:\s*$)',  # "user Jane Smith"
            ]
            
            for pattern in assignee_patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                if matches:
                    assignee_name = matches[0].strip()
                    # Clean up common words that might be captured, but preserve proper names
                    cleaned_name = re.sub(r'\b(assign|assignee|user|item|work)\b', '', assignee_name, flags=re.IGNORECASE).strip()
                    # Only use cleaned name if it's not empty and still looks like a name
                    if cleaned_name and len(cleaned_name) > 1:
                        assignee_name = cleaned_name
                    break
            
            # Validation
            if not work_item_id:
                return {
                    'success': False,
                    'content': "No valid work item ID found. Please specify the work item ID in JIRA format (e.g., 'assign AG-123 to John Doe' or 'assign AG-123 to sprint 1').",
                    'error': "Work item ID is required"
                }
            
            if not assignee_name:
                return {
                    'success': False,
                    'content': "No assignee name found. Please specify who to assign the work item to (e.g., 'assign AG-123 to John Doe') or which sprint to assign it to (e.g., 'assign AG-123 to sprint 1').",
                    'error': "Assignee name is required"
                }
            
            # Validate work item ID format
            if not re.match(r'^[A-Z]+[A-Z0-9]*-\d+$', work_item_id, re.IGNORECASE):
                return {
                    'success': False,
                    'content': f"Invalid work item ID format: '{work_item_id}'. Please use JIRA format like 'AG-123'.",
                    'error': "Invalid work item ID format"
                }
            
            # Find JIRA provider
            jira_tool = None
            for tool in project_context['tools']:
                if tool['type'] == 'jira':
                    jira_tool = tool
                    break
            
            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Please configure JIRA first.",
                    'error': "JIRA not configured"
                }
            
            # Create JIRA provider
            from app.mcp import JiraProvider
            provider = JiraProvider(
                server_url=jira_tool['base_url'],
                username=jira_tool['configuration'].get('email'),
                api_token=jira_tool['api_token'],
                config=jira_tool['configuration']
            )
            
            # Update work item with new assignee
            project_key = jira_tool['configuration'].get('project_key', project_context['project']['key'])
            updates = {
                'assignee': assignee_name
            }
            
            response = provider.update_work_item(project_key, work_item_id, updates)
            
            if response.success:
                return {
                    'success': True,
                    'content': f"✅ Work item {work_item_id} has been successfully assigned to {assignee_name}.",
                    'data': {
                        'work_item_id': work_item_id,
                        'assignee': assignee_name,
                        'url': response.data.get('url') if response.data else None
                    }
                }
            else:
                # Handle specific error cases
                if "404" in str(response.error):
                    return {
                        'success': False,
                        'content': f"❌ Work item {work_item_id} was not found in JIRA. Please check the ID and try again.",
                        'error': "Work item not found"
                    }
                elif "403" in str(response.error):
                    return {
                        'success': False,
                        'content': f"❌ You don't have permission to assign work item {work_item_id}. Please check your JIRA permissions.",
                        'error': "Permission denied"
                    }
                elif "assignee" in str(response.error).lower():
                    return {
                        'success': False,
                        'content': f"❌ Could not assign '{assignee_name}' to work item {work_item_id}. Please check that the user exists in JIRA and has access to the project.",
                        'error': "Invalid assignee"
                    }
                else:
                    return {
                        'success': False,
                        'content': f"❌ Failed to assign work item {work_item_id}: {response.error}",
                        'error': "Failed to assign work item"
                    }
                
        except Exception as e:
            current_app.logger.error(f"Exception during work assignment: {str(e)}")
            return {
                'success': False,
                'content': f"An error occurred while assigning the work item: {str(e)}",
                'error': "Exception occurred during assignment"
            }
    
    def _move_items_status(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Move work items across statuses"""
        return {
            'success': False,
            'content': "Status transitions not yet implemented.",
            'error': "Feature not implemented"
        }
    
    def _remove_duplicate_items(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Remove duplicate work items from the backlog"""
        try:
            # Find JIRA provider
            jira_tool = None
            for tool in project_context['tools']:
                if tool['type'] == 'jira':
                    jira_tool = tool
                    break
            
            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Duplicate removal requires JIRA integration.",
                    'error': "JIRA not configured"
                }
            
            # Get all work items from JIRA
            work_items = self._get_all_work_items(jira_tool, project_context)
            
            if not work_items:
                return {
                    'success': False,
                    'content': "No work items found in the project or failed to retrieve them.",
                    'error': "No work items found"
                }
            
            # Identify duplicates
            duplicates = self._identify_duplicates(work_items)
            
            if not duplicates:
                return {
                    'success': True,
                    'content': "No duplicate work items found in your backlog. Your backlog is already clean!",
                    'data': {
                        'total_items_analyzed': len(work_items),
                        'duplicates_found': 0,
                        'duplicates_removed': 0
                    }
                }
            
            # Remove duplicates from JIRA
            removed_items = self._delete_duplicate_items(duplicates, jira_tool, project_context)
            
            success_count = len([item for item in removed_items if item.get('success')])
            
            content = f"""Successfully cleaned up your backlog by removing {success_count} duplicate work items.

## Duplicates Removed:
{self._format_removed_duplicates(duplicates, removed_items)}

## Cleanup Summary:
- Total items analyzed: {len(work_items)}
- Duplicate groups found: {len(duplicates)}
- Items removed: {success_count}
- Items kept: {sum(len(group['duplicates']) for group in duplicates)}

Your backlog is now cleaner and easier to manage!"""

            return {
                'success': True,
                'content': content,
                'data': {
                    'total_items_analyzed': len(work_items),
                    'duplicate_groups': len(duplicates),
                    'duplicates_removed': success_count
                }
            }
            
        except Exception as e:
            current_app.logger.error(f"Error removing duplicates: {str(e)}")
            return {
                'success': False,
                'content': "Failed to remove duplicate items.",
                'error': str(e)
            }
    
    def _manage_backlog(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """General backlog management operations"""
        return {
            'success': False,
            'content': "General backlog management not yet implemented.",
            'error': "Feature not implemented"
        }
    
    def _general_management(self, query: str, project_context: Dict[str, Any], context: AgentContext, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general management requests with intelligent context"""
        
        # Use the decision context to provide intelligent guidance
        reasoning = decision.reasoning if hasattr(decision, 'reasoning') else "Request analysis"
        confidence = decision.confidence if hasattr(decision, 'confidence') else 0.5
        
        if confidence > 0.7:
            # High confidence - provide specific guidance
            content = f"""I understand you want to perform a management operation, but I need more specific information to help you effectively.

## Analysis:
**Request Understanding**: {reasoning}
**Confidence**: {confidence}

## Available Operations:
Based on your project's configured tools ({', '.join([tool['name'] for tool in project_context.get('tools', [])])}), I can help you with:

- **Create Work Items**: "Create a new task for user authentication"
- **Create Sprints**: "Create a 2-week sprint starting next Monday"
- **Update Work Items**: "Update task ABC-123 to in progress"
- **Assign Work**: "Assign task ABC-123 to John"
- **Move Items**: "Move task ABC-123 to done"
- **Remove Duplicates**: "Clean up duplicate items in the backlog"

## Next Steps:
Please be more specific about what you'd like me to do. For example:
- What type of item do you want to create/update?
- Which specific work items are you referring to?
- What changes do you want to make?

I'm here to help make your project management tasks easier!"""
        else:
            # Lower confidence - ask for clarification
            content = f"""I want to help you with your project management request, but I need some clarification to ensure I provide the right assistance.

## What I understood:
{reasoning}

## What I can help with:
- Creating and managing work items (tasks, stories, bugs)
- Sprint planning and management
- Assigning work to team members
- Updating work item statuses
- Organizing and cleaning up backlogs

## Please clarify:
Could you be more specific about what you'd like me to do? For example:
- Are you looking to create something new?
- Do you want to update existing items?
- Are you planning upcoming work?
- Do you need help organizing your backlog?

The more details you provide, the better I can assist you!"""
        
        return {
            'success': True,
            'content': content,
            'data': {
                'analysis': {
                    'reasoning': reasoning,
                    'confidence': confidence,
                    'available_tools': [tool['name'] for tool in project_context.get('tools', [])],
                    'suggested_actions': [
                        'create_work_items',
                        'create_sprint',
                        'update_work_item',
                        'assign_work',
                        'remove_duplicates'
                    ]
                }
            }
        }
    
    # Helper methods from existing agents
    def _generate_work_items_with_llm(self, query: str, project_context: Dict[str, Any], context: AgentContext) -> List[Dict[str, Any]]:
        """Generate work items using LLM"""
        # This uses the same logic as the original backlog generator
        # For now, return predefined work items
        return [
            {
                "title": "Implement comprehensive API input validation",
                "user_story": "As a developer, I want all API endpoints to validate input data so that the system is protected from invalid requests and security vulnerabilities.",
                "description": "Add request validation middleware to all API endpoints to ensure data integrity, prevent injection attacks, and provide clear error messages for invalid inputs.",
                "acceptance_criteria": [
                    "Given a user sends a request with invalid JSON, When the API processes the request, Then it returns a 400 error with clear validation message",
                    "Given a user sends a request with missing required fields, When the API validates the request, Then it returns specific field-level error messages"
                ],
                "priority": "High",
                "story_points": 5,
                "labels": ["backend", "security", "validation"],
                "type": "Story"
            },
            {
                "title": "Add rate limiting to prevent API abuse",
                "user_story": "As a system administrator, I want API rate limiting implemented so that the service remains available and performs well under load.",
                "description": "Implement rate limiting middleware to prevent API abuse, ensure fair usage, and protect against DoS attacks.",
                "acceptance_criteria": [
                    "Given a user exceeds the rate limit, When they make additional requests, Then they receive a 429 Too Many Requests response",
                    "Given a user is within rate limits, When they make requests, Then requests are processed normally"
                ],
                "priority": "High",
                "story_points": 3,
                "labels": ["backend", "security", "performance"],
                "type": "Story"
            }
        ]
    
    def _create_jira_work_items(self, work_items: List[Dict[str, Any]], jira_tool: Dict[str, Any], project_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create work items in JIRA"""
        try:
            from app.models import Project, ProjectTool, Tool
            from app.mcp import JiraProvider
            
            # Get project tool configuration
            project_tools = ProjectTool.query.filter_by(
                project_id=project_context['project']['id'],
                is_active=True
            ).all()
            
            jira_project_tool = None
            for pt in project_tools:
                if pt.tool.tool_type.value == 'jira':
                    jira_project_tool = pt
                    break
            
            if not jira_project_tool:
                return []
            
            tool = jira_project_tool.tool
            
            # Create JIRA provider
            provider = JiraProvider(
                server_url=tool.base_url,
                username=tool.configuration.get('email'),
                api_token=tool.api_token,
                config=tool.configuration
            )
            
            created_items = []
            project_key = tool.configuration.get('project_key')
            
            for item in work_items:
                try:
                    from app.mcp.base import WorkItem
                    
                    # Format description with acceptance criteria
                    description = f"""{item['description']}

## Acceptance Criteria:
{chr(10).join([f"- {criteria}" for criteria in item['acceptance_criteria']])}

## Additional Details:
- Priority: {item['priority']}
- Story Points: {item['story_points']}
- Labels: {', '.join(item['labels'])}
"""
                    
                    work_item = WorkItem(
                        id="",
                        title=item['title'],
                        description=description,
                        status="To Do",
                        assignee=None,
                        labels=item['labels'],
                        priority=item['priority'],
                        story_points=item['story_points'],
                        metadata={
                            'issue_type': item['type'],
                            'user_story': item['user_story']
                        }
                    )
                    
                    # Create in JIRA
                    response = provider.create_work_item(project_key, work_item)
                    
                    created_items.append({
                        'title': item['title'],
                        'success': response.success,
                        'jira_key': response.data.get('key') if response.success else None,
                        'url': response.data.get('url') if response.success else None,
                        'error': response.error if not response.success else None
                    })
                    
                except Exception as e:
                    created_items.append({
                        'title': item['title'],
                        'success': False,
                        'error': str(e)
                    })
            
            return created_items
            
        except Exception as e:
            current_app.logger.error(f"Error creating JIRA work items: {str(e)}")
            return []
    
    # Sprint management helper methods
    def _parse_sprint_requirements(self, query: str) -> Dict[str, Any]:
        """Parse sprint requirements from query"""
        sprint_plan = {
            'sprint_duration': '2 weeks',
            'start_date': None,
            'end_date': None,
            'total_duration': None,
            'create_sprints': True
        }
        
        # Parse dates and durations from query
        date_patterns = [
            r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})',  # 7th July 2025
            r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s+\d{4})',  # July 7th, 2025
            r'(\w+\s+\d{1,2}\s+\d{4})',  # December 30 2025
            r'(\d{4}-\d{2}-\d{2})',  # 2025-07-07
            r'(\d{1,2}/\d{1,2}/\d{4})',  # 7/7/2025
        ]
        
        dates_found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            dates_found.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_dates = []
        for date in dates_found:
            if date not in seen:
                seen.add(date)
                unique_dates.append(date)
        
        if len(unique_dates) >= 1:
            sprint_plan['start_date'] = unique_dates[0]
        if len(unique_dates) >= 2:
            sprint_plan['end_date'] = unique_dates[1]
        
        return sprint_plan
    
    def _generate_sprint_plan_with_llm(self, query: str, sprint_plan: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Generate detailed sprint plan"""
        return {
            'plan_description': 'Sprint plan generated based on your requirements.',
            'sprints': self._extract_sprints_from_plan('', sprint_plan),
            'total_sprints': 0,
            'project_timeline': {
                'start_date': sprint_plan.get('start_date'),
                'end_date': sprint_plan.get('end_date'),
                'duration': sprint_plan.get('sprint_duration')
            }
        }
    
    def _extract_sprints_from_plan(self, plan_text: str, sprint_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract sprint details from plan"""
        sprints = []
        
        start_date_str = sprint_plan.get('start_date')
        end_date_str = sprint_plan.get('end_date')
        
        if start_date_str and end_date_str:
            try:
                from dateutil import parser
                start_date = parser.parse(start_date_str)
                end_date = parser.parse(end_date_str)
                
                sprint_duration = timedelta(weeks=2)
                current_date = start_date
                sprint_number = 1
                
                while current_date < end_date:
                    sprint_end = min(current_date + sprint_duration, end_date)
                    
                    sprints.append({
                        'name': f'Sprint {sprint_number}',
                        'start_date': current_date.isoformat(),
                        'end_date': sprint_end.isoformat(),
                        'goal': f'Sprint {sprint_number} objectives',
                        'duration_days': (sprint_end - current_date).days
                    })
                    
                    current_date = sprint_end
                    sprint_number += 1
                    
                    if sprint_number > 50:  # Safety limit
                        break
                        
            except Exception as e:
                current_app.logger.error(f"Error parsing sprint dates: {str(e)}")
        
        return sprints
    
    def _create_sprints_in_jira(self, plan: Dict[str, Any], jira_tool: Dict[str, Any], project_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create sprints in JIRA"""
        created_sprints = []
        
        try:
            from app.models import Project, ProjectTool, Tool
            from app.mcp import JiraProvider
            from app.mcp.base import Sprint
            
            # Get project tool configuration
            project_tools = ProjectTool.query.filter_by(
                project_id=project_context['project']['id'],
                is_active=True
            ).all()
            
            jira_project_tool = None
            for pt in project_tools:
                if pt.tool.tool_type.value == 'jira':
                    jira_project_tool = pt
                    break
            
            if not jira_project_tool:
                return []
            
            tool = jira_project_tool.tool
            
            # Create JIRA provider
            provider = JiraProvider(
                server_url=tool.base_url,
                username=tool.configuration.get('email'),
                api_token=tool.api_token,
                config=tool.configuration
            )
            
            project_key = tool.configuration.get('project_key')
            
            # Create each sprint in JIRA
            for sprint_data in plan.get('sprints', []):
                try:
                    start_date = None
                    end_date = None
                    
                    if sprint_data.get('start_date'):
                        start_date = datetime.fromisoformat(sprint_data['start_date'].replace('Z', '+00:00'))
                    
                    if sprint_data.get('end_date'):
                        end_date = datetime.fromisoformat(sprint_data['end_date'].replace('Z', '+00:00'))
                    
                    sprint = Sprint(
                        id="",
                        name=sprint_data['name'],
                        state="future",
                        start_date=start_date,
                        end_date=end_date,
                        goal=sprint_data.get('goal', f"Objectives for {sprint_data['name']}")
                    )
                    
                    response = provider.create_sprint(project_key, sprint)
                    
                    created_sprints.append({
                        'name': sprint_data['name'],
                        'success': response.success,
                        'jira_id': response.data.get('id') if response.success else None,
                        'start_date': sprint_data['start_date'],
                        'end_date': sprint_data['end_date'],
                        'url': f"https://newtuple.atlassian.net/secure/RapidBoard.jspa?rapidView=133&view=planning.nodetail&selectedSprint={response.data.get('id')}" if response.success else None,
                        'error': response.error if not response.success else None
                    })
                    
                except Exception as e:
                    created_sprints.append({
                        'name': sprint_data.get('name', 'Unknown Sprint'),
                        'success': False,
                        'error': str(e)
                    })
        
        except Exception as e:
            created_sprints.append({
                'name': 'Sprint Creation Failed',
                'success': False,
                'error': str(e)
            })
        
        return created_sprints
    
    # Duplicate removal helper methods
    def _get_all_work_items(self, jira_tool: Dict[str, Any], project_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all work items from JIRA"""
        try:
            from app.models import Project, ProjectTool, Tool
            from app.mcp import JiraProvider
            
            # Get project tool configuration
            project_tools = ProjectTool.query.filter_by(
                project_id=project_context['project']['id'],
                is_active=True
            ).all()
            
            jira_project_tool = None
            for pt in project_tools:
                if pt.tool.tool_type.value == 'jira':
                    jira_project_tool = pt
                    break
            
            if not jira_project_tool:
                return []
            
            tool = jira_project_tool.tool
            
            provider = JiraProvider(
                server_url=tool.base_url,
                username=tool.configuration.get('email'),
                api_token=tool.api_token,
                config=tool.configuration
            )
            
            project_key = tool.configuration.get('project_key')
            response = provider.get_work_items(project_key, max_results=1000)
            
            if not response.success:
                return []
            
            # Convert WorkItem objects to dictionaries
            work_items = []
            for work_item in response.data:
                work_items.append({
                    'id': work_item.id,
                    'title': work_item.title,
                    'description': work_item.description,
                    'status': work_item.status,
                    'created_date': work_item.created_date,
                    'url': work_item.metadata.get('url') if work_item.metadata else None
                })
            
            return work_items
            
        except Exception as e:
            current_app.logger.error(f"Error getting work items: {str(e)}")
            return []
    
    def _identify_duplicates(self, work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify duplicate work items"""
        duplicates = []
        processed_items = set()
        
        for i, item1 in enumerate(work_items):
            if item1['id'] in processed_items:
                continue
                
            similar_items = []
            
            for j, item2 in enumerate(work_items):
                if i != j and item2['id'] not in processed_items:
                    similarity = difflib.SequenceMatcher(None, 
                        item1['title'].lower().strip(), 
                        item2['title'].lower().strip()
                    ).ratio()
                    
                    if similarity >= 0.9:  # 90% similarity threshold
                        similar_items.append(item2)
                        processed_items.add(item2['id'])
            
            if similar_items:
                all_items = [item1] + similar_items
                all_items.sort(key=lambda x: x['created_date'] if x['created_date'] else datetime.min)
                
                kept_item = all_items[0]
                duplicate_items = all_items[1:]
                
                duplicates.append({
                    'kept_item': kept_item,
                    'duplicates': duplicate_items,
                    'group_title': kept_item['title']
                })
                
                processed_items.add(kept_item['id'])
        
        return duplicates
    
    def _delete_duplicate_items(self, duplicates: List[Dict[str, Any]], jira_tool: Dict[str, Any], project_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Delete duplicate items in JIRA"""
        try:
            from app.models import Project, ProjectTool, Tool
            from app.mcp import JiraProvider
            
            # Get project tool configuration
            project_tools = ProjectTool.query.filter_by(
                project_id=project_context['project']['id'],
                is_active=True
            ).all()
            
            jira_project_tool = None
            for pt in project_tools:
                if pt.tool.tool_type.value == 'jira':
                    jira_project_tool = pt
                    break
            
            if not jira_project_tool:
                return []
            
            tool = jira_project_tool.tool
            
            provider = JiraProvider(
                server_url=tool.base_url,
                username=tool.configuration.get('email'),
                api_token=tool.api_token,
                config=tool.configuration
            )
            
            project_key = tool.configuration.get('project_key')
            removed_items = []
            
            for duplicate_group in duplicates:
                kept_item = duplicate_group['kept_item']
                
                for duplicate_item in duplicate_group['duplicates']:
                    try:
                        updates = {
                            'status': 'Done',
                            'resolution': 'Duplicate'
                        }
                        
                        response = provider.update_work_item(project_key, duplicate_item['id'], updates)
                        
                        removed_items.append({
                            'id': duplicate_item['id'],
                            'title': duplicate_item['title'],
                            'success': response.success,
                            'action': 'marked_as_duplicate' if response.success else 'failed',
                            'kept_item_id': kept_item['id'],
                            'error': response.error if not response.success else None
                        })
                        
                    except Exception as e:
                        removed_items.append({
                            'id': duplicate_item['id'],
                            'title': duplicate_item['title'],
                            'success': False,
                            'action': 'failed',
                            'kept_item_id': kept_item['id'],
                            'error': str(e)
                        })
            
            return removed_items
            
        except Exception as e:
            current_app.logger.error(f"Error removing duplicate items: {str(e)}")
            return []
    
    # Formatting helper methods
    def _format_created_items(self, created_items: List[Dict[str, Any]]) -> str:
        """Format created items for display"""
        formatted = []
        
        for item in created_items:
            if item['success']:
                formatted.append(f"✅ **{item['title']}** - [{item['jira_key']}]({item['url']})")
            else:
                formatted.append(f"❌ **{item['title']}** - Error: {item['error']}")
        
        return "\n".join(formatted)
    
    def _format_sprint_plan(self, plan: Dict[str, Any]) -> str:
        """Format sprint plan for display"""
        if not plan.get('sprints'):
            return "No sprints planned."
        
        formatted = ""
        for i, sprint in enumerate(plan['sprints'], 1):
            formatted += f"{i}. **{sprint['name']}**\n"
            formatted += f"   - Start: {sprint['start_date']}\n"
            formatted += f"   - End: {sprint['end_date']}\n"
            formatted += f"   - Duration: {sprint.get('duration_days', 14)} days\n"
            formatted += f"   - Goal: {sprint['goal']}\n\n"
        
        return formatted
    
    def _format_created_sprints(self, created_sprints: List[Dict[str, Any]]) -> str:
        """Format created sprints for display"""
        if not created_sprints:
            return "No sprints were created."
        
        formatted = ""
        success_count = 0
        error_count = 0
        
        for sprint in created_sprints:
            status = "✅" if sprint.get('success') else "❌"
            formatted += f"{status} **{sprint['name']}**"
            
            if sprint.get('success'):
                success_count += 1
                formatted += f" - Created in JIRA (ID: {sprint.get('jira_id')})\n"
                if sprint.get('url'):
                    formatted += f"   - View: {sprint['url']}\n"
            else:
                error_count += 1
                formatted += f" - Failed to create in JIRA\n"
                if sprint.get('error'):
                    formatted += f"   - Error: {sprint['error']}\n"
        
        if error_count > 0:
            formatted += f"\n**Summary**: {success_count} sprints created successfully, {error_count} failed.\n"
            if error_count > 0:
                formatted += "Please check your JIRA permissions and project configuration for failed sprints."
        
        return formatted
    
    def _format_removed_duplicates(self, duplicates: List[Dict[str, Any]], removed_items: List[Dict[str, Any]]) -> str:
        """Format removed duplicates for display"""
        if not duplicates:
            return "No duplicates were found to remove."
        
        formatted = []
        
        for duplicate_group in duplicates:
            kept_item = duplicate_group['kept_item']
            duplicate_items = duplicate_group['duplicates']
            
            formatted.append(f"**{kept_item['title']}**")
            formatted.append(f"  ✅ **Kept**: {kept_item['id']} (oldest)")
            
            for duplicate in duplicate_items:
                status = "✅ Removed" if any(r['id'] == duplicate['id'] and r['success'] for r in removed_items) else "❌ Failed"
                formatted.append(f"  🗑️ **{status}**: {duplicate['id']}")
            
            formatted.append("")  # Empty line for separation
        
        return "\n".join(formatted)

    def delete_work_item(self, work_item_id: str, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a work item in JIRA"""
        try:
            # Find JIRA provider
            jira_tool = None
            for tool in project_context['tools']:
                if tool['type'] == 'jira':
                    jira_tool = tool
                    break
            
            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Please configure JIRA first.",
                    'error': "JIRA not configured"
                }
            
            # Create JIRA provider
            from app.mcp import JiraProvider
            provider = JiraProvider(
                server_url=jira_tool['base_url'],
                username=jira_tool['configuration'].get('email'),
                api_token=jira_tool['api_token'],
                config=jira_tool['configuration']
            )
            
            # Delete work item
            response = provider.delete_work_item(work_item_id)
            
            if response.success:
                return {
                    'success': True,
                    'content': response.data['message']
                }
            else:
                return {
                    'success': False,
                    'content': response.error,
                    'error': "Failed to delete work item"
                }
        except Exception as e:
            return {
                'success': False,
                'content': str(e),
                'error': "Exception occurred during deletion"
            }

    def _assign_work_item_to_sprint(self, work_item_id: str, sprint_info: str, project_context: Dict[str, Any], context: AgentContext) -> Dict[str, Any]:
        """Assign a work item to a specific sprint"""
        try:
            if not work_item_id:
                return {
                    'success': False,
                    'content': "No valid work item ID found. Please specify the work item ID in JIRA format.",
                    'error': "Work item ID is required"
                }
            
            # Validate work item ID format
            if not re.match(r'^[A-Z]+[A-Z0-9]*-\d+$', work_item_id, re.IGNORECASE):
                return {
                    'success': False,
                    'content': f"Invalid work item ID format: '{work_item_id}'. Please use JIRA format like 'AG-123'.",
                    'error': "Invalid work item ID format"
                }
            
            # Find JIRA provider
            jira_tool = None
            for tool in project_context['tools']:
                if tool['type'] == 'jira':
                    jira_tool = tool
                    break
            
            if not jira_tool:
                return {
                    'success': False,
                    'content': "JIRA integration not found. Please configure JIRA first.",
                    'error': "JIRA not configured"
                }
            
            # Create JIRA provider
            from app.mcp import JiraProvider
            provider = JiraProvider(
                server_url=jira_tool['base_url'],
                username=jira_tool['configuration'].get('email'),
                api_token=jira_tool['api_token'],
                config=jira_tool['configuration']
            )
            
            # Get available sprints for the project
            project_key = jira_tool['configuration'].get('project_key', project_context['project']['key'])
            sprints_response = provider.get_sprints(project_key)
            
            if not sprints_response.success:
                return {
                    'success': False,
                    'content': f"Failed to get sprints for project: {sprints_response.error}",
                    'error': "Could not retrieve sprints"
                }
            
            # Find the matching sprint
            target_sprint = None
            sprints = sprints_response.data
            
            # Try to match by sprint number first (e.g., "1", "2")
            if sprint_info.isdigit():
                sprint_number = int(sprint_info)
                # Look for sprint names like "Sprint 1", "Sprint 2", etc.
                for sprint in sprints:
                    if f"sprint {sprint_number}" in sprint.name.lower() or sprint.name.lower() == f"sprint {sprint_number}":
                        target_sprint = sprint
                        break
            else:
                # Try to match by name (partial match)
                for sprint in sprints:
                    if sprint_info.lower() in sprint.name.lower():
                        target_sprint = sprint
                        break
            
            if not target_sprint:
                # Show available sprints to help user
                available_sprints = [f"'{sprint.name}' (ID: {sprint.id})" for sprint in sprints[:5]]  # Show first 5
                sprint_list = ", ".join(available_sprints)
                
                return {
                    'success': False,
                    'content': f"❌ Sprint '{sprint_info}' not found. Available sprints: {sprint_list}",
                    'error': "Sprint not found"
                }
            
            # Add work item to sprint using JIRA Agile API
            response = self._add_work_item_to_sprint_in_jira(provider, work_item_id, target_sprint.id)
            
            if response['success']:
                return {
                    'success': True,
                    'content': f"✅ Work item {work_item_id} has been successfully assigned to sprint '{target_sprint.name}'.",
                    'data': {
                        'work_item_id': work_item_id,
                        'sprint_id': target_sprint.id,
                        'sprint_name': target_sprint.name,
                        'url': f"{provider.base_url}/browse/{work_item_id}"
                    }
                }
            else:
                return {
                    'success': False,
                    'content': f"❌ Failed to assign work item {work_item_id} to sprint '{target_sprint.name}': {response['error']}",
                    'error': response['error']
                }
                
        except Exception as e:
            current_app.logger.error(f"Exception during sprint assignment: {str(e)}")
            return {
                'success': False,
                'content': f"An error occurred while assigning the work item to sprint: {str(e)}",
                'error': "Exception occurred during sprint assignment"
            }
    
    def _add_work_item_to_sprint_in_jira(self, provider: 'JiraProvider', work_item_id: str, sprint_id: str) -> Dict[str, Any]:
        """Add a work item to a sprint using JIRA Agile API"""
        try:
            # Use JIRA Agile API to move issue to sprint
            sprint_data = {
                "issues": [work_item_id]
            }
            
            response = provider._make_request('POST', f'../../rest/agile/1.0/sprint/{sprint_id}/issue', json=sprint_data)
            
            if response.status_code == 204:  # No content - success
                return {
                    'success': True,
                    'message': f'Work item {work_item_id} successfully added to sprint {sprint_id}'
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': f'Sprint {sprint_id} or work item {work_item_id} not found'
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'error': 'Permission denied. You may not have permission to modify this sprint.'
                }
            else:
                error_msg = f"Failed to add work item to sprint: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            } 