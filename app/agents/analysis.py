import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from flask import current_app
from .base import BaseAgent, AgentContext, AgentResponse
from .intelligence import agent_intelligence
from app.mcp.unified_service import unified_service
from app.mcp.unified_schema import EntityType, UnifiedQuery

class AnalysisAgent(BaseAgent):
    """Agent for project analysis, reporting, metrics, and insights"""
    
    def __init__(self):
        super().__init__(
            name="analysis",
            description="Provides intelligent project analysis, status reports, metrics dashboards, progress summaries, and predictive analytics"
        )
        # Register providers with unified service
        self._register_providers()
    
    def _register_providers(self):
        """Register MCP providers with the unified service"""
        try:
            from app.mcp import JiraProvider, GitHubProvider, AzureDevOpsProvider
            # Note: In a real implementation, these would be instantiated with proper credentials
            # For now, we'll register them when needed
            pass
        except Exception as e:
            current_app.logger.error(f"Error registering providers: {str(e)}")
    
    def execute(self, query: str, context: AgentContext) -> AgentResponse:
        """Execute intelligent project analysis and reporting tasks"""
        start_time = time.time()
        
        try:
            if not context.project_id:
                return AgentResponse(
                    success=False,
                    content="No project specified for analysis.",
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
            decision = agent_intelligence.analyze_query_and_decide(
                query=query,
                project_context=project_context,
                conversation_history=context.conversation_history
            )
            
            current_app.logger.info(f"AnalysisAgent decision: {decision.action_type}, entities: {[e.value for e in decision.entities_needed]}, tools: {decision.tools_to_use}")
            
            # Register the actual providers with proper credentials
            self._register_actual_providers(project_context)
            
            # Create unified query based on the decision
            unified_query = agent_intelligence.create_unified_query(decision)
            
            # Execute the unified query to get data from relevant tools
            unified_response = unified_service.execute_unified_query(unified_query, project_context)
            
            if not unified_response.success:
                return AgentResponse(
                    success=False,
                    content="Failed to retrieve data from the configured tools.",
                    error="; ".join(unified_response.errors)
                )
            
            # Perform intelligent analysis based on the decision and retrieved data
            analysis_result = self._perform_intelligent_analysis(
                decision=decision,
                unified_data=unified_response,
                query=query,
                context=context
            )
            
            # Generate insights using LLM
            insights = self._generate_contextual_insights(
                analysis_result=analysis_result,
                decision=decision,
                query=query,
                context=context
            )
            
            # Format response
            end_time = time.time()
            execution_time = end_time - start_time
            
            content = self._format_intelligent_response(
                insights=insights,
                analysis_result=analysis_result,
                decision=decision,
                unified_response=unified_response
            )

            response = AgentResponse(
                success=True,
                content=content,
                data={
                    'analysis_type': decision.action_type,
                    'decision_reasoning': decision.reasoning,
                    'confidence': decision.confidence,
                    'entities_analyzed': [e.value for e in decision.entities_needed],
                    'tools_used': unified_response.source_tools,
                    'analysis_result': analysis_result,
                    'unified_data': self._serialize_unified_data(unified_response),
                    'insights_generated': True,
                    'analysis_timestamp': datetime.utcnow().isoformat()
                },
                tokens_used=0,  # Will be updated by LLM calls
                cost=0.0,
                execution_time=execution_time
            )
            
            return response
            
        except Exception as e:
            end_time = time.time()
            execution_time = end_time - start_time
            
            current_app.logger.error(f"AnalysisAgent error: {str(e)}")
            
            return AgentResponse(
                success=False,
                content="I encountered an error while analyzing your project data.",
                error=str(e),
                execution_time=execution_time
            )
    
    def _register_actual_providers(self, project_context: Dict[str, Any]):
        """Register actual providers with proper credentials"""
        try:
            from app.models import ProjectTool, Tool
            from app.mcp import JiraProvider, GitHubProvider, AzureDevOpsProvider
            
            project_tools = ProjectTool.query.filter_by(
                project_id=project_context['project']['id'],
                is_active=True
            ).all()
            
            for project_tool in project_tools:
                tool = project_tool.tool
                
                try:
                    if tool.tool_type.value == 'jira':
                        provider = JiraProvider(
                            server_url=tool.base_url,
                            username=tool.configuration.get('email'),
                            api_token=tool.api_token,
                            config=tool.configuration
                        )
                        unified_service.register_provider('jira', provider)
                        
                    elif tool.tool_type.value == 'github':
                        provider = GitHubProvider(
                            auth_token=tool.api_token,
                            config=tool.configuration
                        )
                        unified_service.register_provider('github', provider)
                        
                    elif tool.tool_type.value == 'azure_devops':
                        provider = AzureDevOpsProvider(
                            server_url=tool.base_url,
                            auth_token=tool.api_token,
                            config=tool.configuration
                        )
                        unified_service.register_provider('azure_devops', provider)
                        
                except Exception as e:
                    current_app.logger.error(f"Error registering {tool.name} provider: {str(e)}")
                    
        except Exception as e:
            current_app.logger.error(f"Error in _register_actual_providers: {str(e)}")
    
    def _perform_intelligent_analysis(self, decision, unified_data, query: str, context: AgentContext) -> Dict[str, Any]:
        """Perform intelligent analysis based on the decision and retrieved data"""
        analysis_result = {
            'decision_context': {
                'action_type': decision.action_type,
                'reasoning': decision.reasoning,
                'confidence': decision.confidence
            },
            'data_summary': {},
            'key_insights': [],
            'metrics': {},
            'recommendations': []
        }
        
        # Analyze each type of entity retrieved
        for entity_type, entities in unified_data.data.items():
            if not entities:
                continue
                
            entity_analysis = self._analyze_entity_type(entity_type, entities, decision)
            analysis_result['data_summary'][entity_type.value] = entity_analysis
        
        # Generate cross-entity insights
        analysis_result['cross_entity_insights'] = self._generate_cross_entity_insights(unified_data.data)
        
        # Calculate key metrics based on decision type
        if decision.action_type in ['analyze', 'report']:
            analysis_result['metrics'] = self._calculate_intelligent_metrics(unified_data.data, decision)
        
        return analysis_result
    
    def _analyze_entity_type(self, entity_type: EntityType, entities: List, decision) -> Dict[str, Any]:
        """Analyze a specific type of entity"""
        if entity_type == EntityType.WORK_ITEM:
            return self._analyze_work_items(entities, decision)
        elif entity_type == EntityType.SPRINT:
            return self._analyze_sprints(entities, decision)
        elif entity_type == EntityType.PULL_REQUEST:
            return self._analyze_pull_requests(entities, decision)
        elif entity_type == EntityType.COMMIT:
            return self._analyze_commits(entities, decision)
        elif entity_type == EntityType.REPOSITORY:
            return self._analyze_repositories(entities, decision)
        else:
            return {
                'total_count': len(entities),
                'entity_type': entity_type.value,
                'analysis': 'Basic count analysis'
            }
    
    def _analyze_work_items(self, work_items: List, decision) -> Dict[str, Any]:
        """Intelligent analysis of work items"""
        if not work_items:
            return {'total_count': 0, 'message': 'No work items found'}
        
        # Group by status
        status_distribution = {}
        priority_distribution = {}
        assignee_distribution = {}
        type_distribution = {}
        
        for item in work_items:
            # Status analysis
            status = item.status.value if hasattr(item.status, 'value') else str(item.status)
            status_distribution[status] = status_distribution.get(status, 0) + 1
            
            # Priority analysis
            priority = item.priority.value if hasattr(item.priority, 'value') else str(item.priority)
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
            
            # Assignee analysis
            assignee = item.assignee.name if item.assignee else 'Unassigned'
            assignee_distribution[assignee] = assignee_distribution.get(assignee, 0) + 1
            
            # Type analysis
            item_type = item.type.value if hasattr(item.type, 'value') else str(item.type)
            type_distribution[item_type] = type_distribution.get(item_type, 0) + 1
        
        # Calculate completion rate
        completed_statuses = ['done', 'closed', 'resolved']
        completed_count = sum(count for status, count in status_distribution.items() 
                            if status.lower() in completed_statuses)
        completion_rate = (completed_count / len(work_items)) * 100
        
        return {
            'total_count': len(work_items),
            'completion_rate': round(completion_rate, 1),
            'status_distribution': status_distribution,
            'priority_distribution': priority_distribution,
            'assignee_distribution': assignee_distribution,
            'type_distribution': type_distribution,
            'completed_items': completed_count,
            'tools_sources': list(set(item.source_tool for item in work_items if item.source_tool))
        }
    
    def _analyze_sprints(self, sprints: List, decision) -> Dict[str, Any]:
        """Intelligent analysis of sprints"""
        if not sprints:
            return {'total_count': 0, 'message': 'No sprints found'}
        
        # Group by state
        state_distribution = {}
        active_sprint = None
        
        for sprint in sprints:
            state = sprint.state
            state_distribution[state] = state_distribution.get(state, 0) + 1
            
            if state.lower() == 'active':
                active_sprint = sprint
        
        return {
            'total_count': len(sprints),
            'state_distribution': state_distribution,
            'active_sprint': {
                'name': active_sprint.name,
                'id': active_sprint.id,
                'start_date': active_sprint.start_date.isoformat() if active_sprint.start_date else None,
                'end_date': active_sprint.end_date.isoformat() if active_sprint.end_date else None,
                'goal': active_sprint.goal
            } if active_sprint else None,
            'tools_sources': list(set(sprint.source_tool for sprint in sprints if sprint.source_tool))
        }
    
    def _analyze_pull_requests(self, pull_requests: List, decision) -> Dict[str, Any]:
        """Intelligent analysis of pull requests"""
        if not pull_requests:
            return {'total_count': 0, 'message': 'No pull requests found'}
        
        # Group by state
        state_distribution = {}
        author_distribution = {}
        
        for pr in pull_requests:
            state = pr.state
            state_distribution[state] = state_distribution.get(state, 0) + 1
            
            author = pr.author.name if pr.author else 'Unknown'
            author_distribution[author] = author_distribution.get(author, 0) + 1
        
        return {
            'total_count': len(pull_requests),
            'state_distribution': state_distribution,
            'author_distribution': author_distribution,
            'tools_sources': list(set(pr.source_tool for pr in pull_requests if pr.source_tool))
        }
    
    def _analyze_commits(self, commits: List, decision) -> Dict[str, Any]:
        """Intelligent analysis of commits"""
        if not commits:
            return {'total_count': 0, 'message': 'No commits found'}
        
        # Group by author
        author_distribution = {}
        total_additions = 0
        total_deletions = 0
        
        for commit in commits:
            author = commit.author.name if commit.author else 'Unknown'
            author_distribution[author] = author_distribution.get(author, 0) + 1
            
            total_additions += commit.additions
            total_deletions += commit.deletions
        
        return {
            'total_count': len(commits),
            'author_distribution': author_distribution,
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'net_changes': total_additions - total_deletions,
            'tools_sources': list(set(commit.source_tool for commit in commits if commit.source_tool))
        }
    
    def _analyze_repositories(self, repositories: List, decision) -> Dict[str, Any]:
        """Intelligent analysis of repositories"""
        if not repositories:
            return {'total_count': 0, 'message': 'No repositories found'}
        
        # Analyze repository characteristics
        language_distribution = {}
        total_stars = 0
        total_forks = 0
        
        for repo in repositories:
            if repo.language:
                language_distribution[repo.language] = language_distribution.get(repo.language, 0) + 1
            
            total_stars += repo.stars
            total_forks += repo.forks
        
        return {
            'total_count': len(repositories),
            'language_distribution': language_distribution,
            'total_stars': total_stars,
            'total_forks': total_forks,
            'average_stars': round(total_stars / len(repositories), 1) if repositories else 0,
            'tools_sources': list(set(repo.source_tool for repo in repositories if repo.source_tool))
        }
    
    def _generate_cross_entity_insights(self, unified_data: Dict[EntityType, List]) -> List[str]:
        """Generate insights by analyzing relationships between different entity types"""
        insights = []
        
        work_items = unified_data.get(EntityType.WORK_ITEM, [])
        sprints = unified_data.get(EntityType.SPRINT, [])
        pull_requests = unified_data.get(EntityType.PULL_REQUEST, [])
        commits = unified_data.get(EntityType.COMMIT, [])
        
        # Work items vs sprints correlation
        if work_items and sprints:
            active_sprints = [s for s in sprints if s.state.lower() == 'active']
            if active_sprints:
                sprint_work_items = [w for w in work_items if w.sprint_id == active_sprints[0].id]
                if sprint_work_items:
                    completion_rate = len([w for w in sprint_work_items if w.status.value.lower() in ['done', 'closed']]) / len(sprint_work_items) * 100
                    insights.append(f"Current sprint has {len(sprint_work_items)} work items with {completion_rate:.1f}% completion rate")
        
        # Development activity correlation
        if pull_requests and commits:
            recent_prs = len([pr for pr in pull_requests if pr.state == 'open'])
            insights.append(f"Development activity shows {len(commits)} recent commits and {recent_prs} open pull requests")
        
        return insights
    
    def _calculate_intelligent_metrics(self, unified_data: Dict[EntityType, List], decision) -> Dict[str, Any]:
        """Calculate intelligent metrics based on the data and decision context"""
        metrics = {}
        
        work_items = unified_data.get(EntityType.WORK_ITEM, [])
        if work_items:
            completed_items = len([w for w in work_items if w.status.value.lower() in ['done', 'closed']])
            metrics['completion_rate'] = round((completed_items / len(work_items)) * 100, 1)
            metrics['total_work_items'] = len(work_items)
            metrics['completed_work_items'] = completed_items
        
        pull_requests = unified_data.get(EntityType.PULL_REQUEST, [])
        if pull_requests:
            merged_prs = len([pr for pr in pull_requests if pr.state == 'merged'])
            metrics['pr_merge_rate'] = round((merged_prs / len(pull_requests)) * 100, 1) if pull_requests else 0
            metrics['total_pull_requests'] = len(pull_requests)
        
        commits = unified_data.get(EntityType.COMMIT, [])
        if commits:
            metrics['total_commits'] = len(commits)
            metrics['total_code_changes'] = sum(c.additions + c.deletions for c in commits)
        
        return metrics
    
    def _generate_contextual_insights(self, analysis_result: Dict[str, Any], decision, query: str, context: AgentContext) -> str:
        """Generate contextual insights using LLM based on analysis results"""
        
        # Check if we have any actual data to analyze
        has_data = False
        total_items = 0
        
        for entity_type, summary in analysis_result.get('data_summary', {}).items():
            count = summary.get('total_count', 0)
            total_items += count
            if count > 0:
                has_data = True
        
        # If no data found, return appropriate message instead of hallucinating
        if not has_data or total_items == 0:
            return f"""## No Data Retrieved

I attempted to retrieve your JIRA backlog data but found 0 work items. This could be due to:

**Possible Issues:**
1. **Connection Problem**: The JIRA integration may not be properly connected
2. **Project Key Mismatch**: The system might be looking in the wrong JIRA project  
3. **Permission Issues**: The API token may not have access to view work items
4. **Filter Issues**: The query filters might be too restrictive

**What You Can Do:**
1. **Check JIRA Integration**: Verify that your JIRA tool is properly configured in the project settings
2. **Verify Project Key**: Ensure the JIRA project key matches your actual project (I see "AGILO" in your image)
3. **Test Connection**: Try accessing JIRA directly to confirm the items exist
4. **Check Permissions**: Ensure the API token has read access to work items

**Expected Data**: Based on your screenshot, I should be seeing 8 work items (AG-1 through AG-8) including:
- AG-1: Implement comprehensive API input validation
- AG-2: Add rate limiting to prevent API abuse
- AG-3: Create comprehensive API documentation with Swagger/OpenAPI

Please check your JIRA integration configuration and try again."""
        
        # If we have data, proceed with normal LLM analysis
        system_prompt = self.get_system_prompt(context)
        
        # Format analysis data for LLM
        analysis_summary = self._format_analysis_for_llm(analysis_result, decision)
        
        user_prompt = f"""Based on the intelligent analysis of project data, provide actionable insights and recommendations.

Original User Query: "{query}"

Agent Decision Context:
- Action Type: {decision.action_type}
- Reasoning: {decision.reasoning}
- Confidence: {decision.confidence}
- Tools Used: {', '.join(decision.tools_to_use)}

Analysis Results:
{analysis_summary}

IMPORTANT: Only analyze the actual data provided above. Do not make up statistics or numbers. If the data shows 0 items or empty results, acknowledge that no data was found.

Please provide:
1. Key findings and insights relevant to the user's question
2. Actionable recommendations based on the data
3. Areas of concern or opportunity
4. Next steps for the project team
5. Data-driven conclusions

Focus on being specific and actionable, using ONLY the actual data retrieved from the tools."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self._call_llm(messages, temperature=0.3, max_tokens=1000)
            return response.content
        except Exception as e:
            current_app.logger.error(f"Error generating contextual insights: {str(e)}")
            return self._generate_fallback_insights(analysis_result, decision)
    
    def _generate_fallback_insights(self, analysis_result: Dict[str, Any], decision) -> str:
        """Generate fallback insights when LLM fails"""
        insights = ["## Analysis Complete\n"]
        
        if 'data_summary' in analysis_result:
            for entity_type, summary in analysis_result['data_summary'].items():
                insights.append(f"**{entity_type.replace('_', ' ').title()}**: {summary.get('total_count', 0)} items analyzed")
        
        if 'metrics' in analysis_result:
            insights.append("\n**Key Metrics:**")
            for metric, value in analysis_result['metrics'].items():
                insights.append(f"- {metric.replace('_', ' ').title()}: {value}")
        
        return "\n".join(insights)
    
    def _format_analysis_for_llm(self, analysis_result: Dict[str, Any], decision) -> str:
        """Format analysis result for LLM consumption"""
        formatted = f"""
Decision Context:
- Action: {decision.action_type}
- Entities Analyzed: {', '.join([e.value for e in decision.entities_needed])}
- Reasoning: {decision.reasoning}

Data Summary:
"""
        
        for entity_type, summary in analysis_result.get('data_summary', {}).items():
            formatted += f"\n{entity_type.replace('_', ' ').title()}:\n"
            for key, value in summary.items():
                if isinstance(value, dict):
                    formatted += f"  {key}: {value}\n"
                else:
                    formatted += f"  {key}: {value}\n"
        
        if analysis_result.get('metrics'):
            formatted += f"\nKey Metrics:\n"
            for metric, value in analysis_result['metrics'].items():
                formatted += f"  {metric}: {value}\n"
        
        if analysis_result.get('cross_entity_insights'):
            formatted += f"\nCross-Entity Insights:\n"
            for insight in analysis_result['cross_entity_insights']:
                formatted += f"  - {insight}\n"
        
        return formatted
    
    def _format_intelligent_response(self, insights: str, analysis_result: Dict[str, Any], decision, unified_response) -> str:
        """Format the final intelligent response"""
        content = f"""## Intelligent Project Analysis

{insights}

## Analysis Details:

**Decision Context:**
- **Action Taken**: {decision.action_type.replace('_', ' ').title()}
- **Reasoning**: {decision.reasoning}
- **Confidence**: {decision.confidence}
- **Tools Used**: {', '.join(unified_response.source_tools)}
- **Entities Analyzed**: {', '.join([e.value for e in decision.entities_needed])}

**Data Retrieved:**
"""
        
        for entity_type, count in unified_response.metadata.get('entity_counts', {}).items():
            content += f"- {entity_type.replace('_', ' ').title()}: {count} items\n"
        
        if analysis_result.get('metrics'):
            content += f"\n**Key Metrics:**\n"
            for metric, value in analysis_result['metrics'].items():
                content += f"- {metric.replace('_', ' ').title()}: {value}\n"
        
        content += f"\n**Analysis Timestamp**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        
        return content
    
    def _serialize_unified_data(self, unified_response) -> Dict[str, Any]:
        """Serialize unified data for response"""
        serialized = {}
        
        for entity_type, entities in unified_response.data.items():
            serialized[entity_type.value] = []
            for entity in entities[:10]:  # Limit to first 10 for response size
                try:
                    entity_dict = {
                        'id': entity.id,
                        'title': getattr(entity, 'title', getattr(entity, 'name', 'Unknown')),
                        'source_tool': entity.source_tool
                    }
                    serialized[entity_type.value].append(entity_dict)
                except Exception as e:
                    current_app.logger.warning(f"Error serializing entity: {str(e)}")
        
        return serialized
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """Get system prompt for intelligent project analysis"""
        return """You are a Senior Project Manager and Data Analyst AI with advanced intelligence capabilities. Your role is to analyze project data from multiple tools and provide actionable insights.

## Your Enhanced Capabilities:
- **Intelligent Data Analysis**: Analyze data from JIRA, GitHub, Azure DevOps, and other tools in a unified manner
- **Cross-Tool Insights**: Generate insights by correlating data across different tools and platforms
- **Contextual Understanding**: Understand user intent and provide relevant analysis based on their specific questions
- **Predictive Analytics**: Identify trends and predict potential outcomes based on current data
- **Actionable Recommendations**: Provide specific, actionable recommendations based on data analysis

## Analysis Framework:
1. **Intelligent Query Understanding**: Understand what the user actually wants to know
2. **Multi-Tool Data Retrieval**: Fetch relevant data from all connected tools
3. **Unified Analysis**: Analyze data in a consistent, unified manner across all tools
4. **Contextual Insights**: Generate insights that are specific to the user's question and project context
5. **Actionable Recommendations**: Provide clear next steps and recommendations

## Output Format:
- Executive-level summaries with data-driven insights
- Specific recommendations with supporting evidence
- Risk assessments with mitigation strategies
- Performance metrics with trend analysis
- Clear explanations of data sources and analysis methods

Focus on providing valuable, actionable insights that help project managers make informed decisions and keep projects on track. Always be specific about what data was analyzed and from which tools.""" 