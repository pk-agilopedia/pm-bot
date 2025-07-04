from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from flask import current_app

from .unified_schema import (
    EntityType, UnifiedQuery, UnifiedResponse, UnifiedWorkItem, UnifiedSprint,
    UnifiedUser, UnifiedRepository, UnifiedPullRequest, UnifiedCommit,
    UnifiedComment, UnifiedProject, WorkItemType, WorkItemStatus, Priority,
    TOOL_CAPABILITIES
)
from .base import MCPResponse
from .jira import JiraProvider
from .github import GitHubProvider
from .azure_devops import AzureDevOpsProvider


class UnifiedMCPService:
    """Unified service that can fetch data from multiple tools and return unified entities"""
    
    def __init__(self):
        self.providers = {}
        self.tool_capabilities = TOOL_CAPABILITIES
    
    def register_provider(self, tool_type: str, provider):
        """Register a tool provider"""
        self.providers[tool_type] = provider
    
    def get_available_tools(self, project_context: Dict[str, Any]) -> List[str]:
        """Get list of available tools for the project"""
        available_tools = []
        for tool in project_context.get('tools', []):
            tool_type = tool.get('type')
            if tool_type in self.providers:
                available_tools.append(tool_type)
        return available_tools
    
    def determine_relevant_tools(self, query: UnifiedQuery, available_tools: List[str]) -> List[str]:
        """Determine which tools are relevant for the given query"""
        relevant_tools = []
        
        for tool_name in available_tools:
            if tool_name in self.tool_capabilities:
                capabilities = self.tool_capabilities[tool_name]
                
                # Check if the tool supports any of the requested entities
                for entity_type in query.entities:
                    if entity_type in capabilities.supported_entities:
                        if tool_name not in relevant_tools:
                            relevant_tools.append(tool_name)
                        break
        
        return relevant_tools
    
    def execute_unified_query(self, query: UnifiedQuery, project_context: Dict[str, Any]) -> UnifiedResponse:
        """Execute a unified query across multiple tools"""
        response = UnifiedResponse(success=True)
        
        # Get available tools for this project
        available_tools = self.get_available_tools(project_context)
        
        # Determine which tools are relevant for this query
        relevant_tools = self.determine_relevant_tools(query, available_tools)
        
        if not relevant_tools:
            response.success = False
            response.errors.append("No relevant tools available for this query")
            return response
        
        response.source_tools = relevant_tools
        
        # Initialize data structure for each requested entity type
        for entity_type in query.entities:
            response.data[entity_type] = []
        
        # Fetch data from each relevant tool
        for tool_name in relevant_tools:
            try:
                tool_data = self._fetch_from_tool(tool_name, query, project_context)
                
                # Merge data into response
                for entity_type, entities in tool_data.items():
                    if entity_type in response.data:
                        response.data[entity_type].extend(entities)
                
            except Exception as e:
                error_msg = f"Error fetching from {tool_name}: {str(e)}"
                response.errors.append(error_msg)
                current_app.logger.error(error_msg)
        
        # Apply post-processing (deduplication, sorting, filtering)
        response = self._post_process_response(response, query)
        
        return response
    
    def _fetch_from_tool(self, tool_name: str, query: UnifiedQuery, project_context: Dict[str, Any]) -> Dict[EntityType, List]:
        """Fetch data from a specific tool and convert to unified format"""
        tool_data = {}
        
        # Find the tool configuration
        tool_config = None
        for tool in project_context.get('tools', []):
            if tool.get('type') == tool_name:
                tool_config = tool
                break
        
        if not tool_config:
            return tool_data
        
        project_key = project_context['project']['key']
        
        # Fetch data based on entity types requested
        for entity_type in query.entities:
            entities = []
            
            try:
                if entity_type == EntityType.WORK_ITEM:
                    entities = self._fetch_work_items(tool_name, tool_config, project_key, query)
                elif entity_type == EntityType.SPRINT:
                    entities = self._fetch_sprints(tool_name, tool_config, project_key, query)
                elif entity_type == EntityType.USER:
                    entities = self._fetch_users(tool_name, tool_config, project_key, query)
                elif entity_type == EntityType.REPOSITORY:
                    entities = self._fetch_repositories(tool_name, tool_config, project_key, query)
                elif entity_type == EntityType.PULL_REQUEST:
                    entities = self._fetch_pull_requests(tool_name, tool_config, project_key, query)
                elif entity_type == EntityType.COMMIT:
                    entities = self._fetch_commits(tool_name, tool_config, project_key, query)
                
                tool_data[entity_type] = entities
                
            except Exception as e:
                current_app.logger.error(f"Error fetching {entity_type.value} from {tool_name}: {str(e)}")
                tool_data[entity_type] = []
        
        return tool_data
    
    def _fetch_work_items(self, tool_name: str, tool_config: Dict, project_key: str, query: UnifiedQuery) -> List[UnifiedWorkItem]:
        """Fetch work items from a tool and convert to unified format"""
        unified_items = []
        
        if tool_name == "jira":
            provider = self.providers.get("jira")
            if provider:
                response = provider.get_work_items(project_key, **query.filters)
                if response.success:
                    for item in response.data:
                        unified_item = self._convert_jira_work_item(item)
                        unified_items.append(unified_item)
                        # Add logging to track each item
                        current_app.logger.debug(f"Fetched JIRA work item: {unified_item.id} - {unified_item.title}")
        
        elif tool_name == "github":
            provider = self.providers.get("github")
            if provider:
                # GitHub issues/work items
                repo_name = query.filters.get('repository') or tool_config.get('repository_name')
                if repo_name:
                    response = provider.get_work_items(repo_name, **query.filters)
                    if response.success:
                        for item in response.data:
                            unified_item = self._convert_github_work_item(item)
                            unified_items.append(unified_item)
                            # Add logging to track each item
                            current_app.logger.debug(f"Fetched GitHub work item: {unified_item.id} - {unified_item.title}")
        
        elif tool_name == "azure_devops":
            provider = self.providers.get("azure_devops")
            if provider:
                response = provider.get_work_items(project_key, **query.filters)
                if response.success:
                    for item in response.data:
                        unified_item = self._convert_azure_work_item(item)
                        unified_items.append(unified_item)
                        # Add logging to track each item
                        current_app.logger.debug(f"Fetched Azure DevOps work item: {unified_item.id} - {unified_item.title}")
        
        return unified_items
    
    def _fetch_sprints(self, tool_name: str, tool_config: Dict, project_key: str, query: UnifiedQuery) -> List[UnifiedSprint]:
        """Fetch sprints from a tool and convert to unified format"""
        unified_sprints = []
        
        if tool_name in ["jira", "azure_devops"]:
            provider = self.providers.get(tool_name)
            if provider:
                response = provider.get_sprints(project_key, **query.filters)
                if response.success:
                    for sprint in response.data:
                        if tool_name == "jira":
                            unified_sprints.append(self._convert_jira_sprint(sprint))
                        else:
                            unified_sprints.append(self._convert_azure_sprint(sprint))
        
        return unified_sprints
    
    def _fetch_repositories(self, tool_name: str, tool_config: Dict, project_key: str, query: UnifiedQuery) -> List[UnifiedRepository]:
        """Fetch repositories from a tool and convert to unified format"""
        unified_repos = []
        
        if tool_name == "github":
            provider = self.providers.get("github")
            if provider:
                # Get repositories for the user/organization
                owner = query.filters.get('owner') or tool_config.get('owner')
                if owner:
                    response = provider.get_repositories(owner, **query.filters)
                    if response.success:
                        for repo in response.data:
                            unified_repos.append(self._convert_github_repository(repo))
        
        return unified_repos
    
    def _fetch_pull_requests(self, tool_name: str, tool_config: Dict, project_key: str, query: UnifiedQuery) -> List[UnifiedPullRequest]:
        """Fetch pull requests from a tool and convert to unified format"""
        unified_prs = []
        
        if tool_name == "github":
            provider = self.providers.get("github")
            if provider:
                repo_name = query.filters.get('repository') or tool_config.get('repository_name')
                if repo_name:
                    response = provider.get_pull_requests(repo_name, **query.filters)
                    if response.success:
                        for pr in response.data:
                            unified_prs.append(self._convert_github_pull_request(pr))
        
        return unified_prs
    
    def _fetch_commits(self, tool_name: str, tool_config: Dict, project_key: str, query: UnifiedQuery) -> List[UnifiedCommit]:
        """Fetch commits from a tool and convert to unified format"""
        unified_commits = []
        
        if tool_name == "github":
            provider = self.providers.get("github")
            if provider:
                repo_name = query.filters.get('repository') or tool_config.get('repository_name')
                if repo_name:
                    response = provider.get_commits(repo_name, **query.filters)
                    if response.success:
                        for commit in response.data:
                            unified_commits.append(self._convert_github_commit(commit))
        
        return unified_commits
    
    def _fetch_users(self, tool_name: str, tool_config: Dict, project_key: str, query: UnifiedQuery) -> List[UnifiedUser]:
        """Fetch users from a tool and convert to unified format"""
        # Implementation would depend on tool capabilities
        return []
    
    # Conversion methods for different tools
    def _convert_jira_work_item(self, item) -> UnifiedWorkItem:
        """Convert JIRA work item to unified format"""
        return UnifiedWorkItem(
            id=item.id,
            title=item.title,
            description=item.description,
            type=self._map_jira_type_to_unified(getattr(item, 'issue_type', 'Task')),
            status=self._map_jira_status_to_unified(item.status),
            priority=self._map_jira_priority_to_unified(getattr(item, 'priority', 'Medium')),
            assignee=UnifiedUser(id=item.assignee, name=item.assignee) if item.assignee else None,
            labels=item.labels or [],
            story_points=item.story_points,
            created_date=item.created_date,
            updated_date=item.updated_date,
            source_tool="jira",
            source_url=item.metadata.get('url') if item.metadata else None,
            metadata=item.metadata or {}
        )
    
    def _convert_github_work_item(self, item) -> UnifiedWorkItem:
        """Convert GitHub issue to unified format"""
        return UnifiedWorkItem(
            id=str(item.id),
            title=item.title,
            description=item.description,
            type=WorkItemType.ISSUE,
            status=self._map_github_status_to_unified(item.status),
            assignee=UnifiedUser(id=item.assignee, name=item.assignee) if item.assignee else None,
            labels=item.labels or [],
            created_date=item.created_date,
            updated_date=item.updated_date,
            source_tool="github",
            source_url=item.metadata.get('url') if item.metadata else None,
            metadata=item.metadata or {}
        )
    
    def _convert_azure_work_item(self, item) -> UnifiedWorkItem:
        """Convert Azure DevOps work item to unified format"""
        return UnifiedWorkItem(
            id=item.id,
            title=item.title,
            description=item.description,
            type=self._map_azure_type_to_unified(getattr(item, 'work_item_type', 'Task')),
            status=self._map_azure_status_to_unified(item.status),
            assignee=UnifiedUser(id=item.assignee, name=item.assignee) if item.assignee else None,
            labels=item.labels or [],
            story_points=item.story_points,
            created_date=item.created_date,
            updated_date=item.updated_date,
            source_tool="azure_devops",
            metadata=item.metadata or {}
        )
    
    def _convert_jira_sprint(self, sprint) -> UnifiedSprint:
        """Convert JIRA sprint to unified format"""
        return UnifiedSprint(
            id=sprint.id,
            name=sprint.name,
            state=sprint.state,
            goal=sprint.goal,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            source_tool="jira",
            metadata=sprint.metadata or {}
        )
    
    def _convert_azure_sprint(self, sprint) -> UnifiedSprint:
        """Convert Azure DevOps sprint to unified format"""
        return UnifiedSprint(
            id=sprint.id,
            name=sprint.name,
            state=sprint.state,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            source_tool="azure_devops",
            metadata=sprint.metadata or {}
        )
    
    def _convert_github_repository(self, repo) -> UnifiedRepository:
        """Convert GitHub repository to unified format"""
        return UnifiedRepository(
            id=str(repo.id),
            name=repo.name,
            full_name=repo.full_name,
            description=repo.description,
            url=repo.url,
            default_branch=getattr(repo, 'default_branch', 'main'),
            created_date=repo.created_date,
            updated_date=repo.updated_date,
            source_tool="github",
            metadata=repo.metadata or {}
        )
    
    def _convert_github_pull_request(self, pr) -> UnifiedPullRequest:
        """Convert GitHub pull request to unified format"""
        return UnifiedPullRequest(
            id=str(pr.id),
            title=pr.title,
            description=pr.description,
            state=pr.state,
            author=UnifiedUser(id=pr.author, name=pr.author) if pr.author else None,
            created_date=pr.created_date,
            updated_date=pr.updated_date,
            source_tool="github",
            source_url=pr.metadata.get('url') if pr.metadata else None,
            metadata=pr.metadata or {}
        )
    
    def _convert_github_commit(self, commit) -> UnifiedCommit:
        """Convert GitHub commit to unified format"""
        return UnifiedCommit(
            id=commit.id,
            sha=commit.sha,
            message=commit.message,
            author=UnifiedUser(id=commit.author, name=commit.author) if commit.author else None,
            timestamp=commit.timestamp,
            source_tool="github",
            metadata=commit.metadata or {}
        )
    
    # Status and type mapping methods
    def _map_jira_type_to_unified(self, jira_type: str) -> WorkItemType:
        """Map JIRA issue type to unified work item type"""
        mapping = {
            'story': WorkItemType.STORY,
            'task': WorkItemType.TASK,
            'bug': WorkItemType.BUG,
            'epic': WorkItemType.EPIC,
            'feature': WorkItemType.FEATURE
        }
        return mapping.get(jira_type.lower(), WorkItemType.TASK)
    
    def _map_jira_status_to_unified(self, jira_status: str) -> WorkItemStatus:
        """Map JIRA status to unified work item status"""
        mapping = {
            'to do': WorkItemStatus.TODO,
            'todo': WorkItemStatus.TODO,
            'open': WorkItemStatus.TODO,
            'in progress': WorkItemStatus.IN_PROGRESS,
            'doing': WorkItemStatus.IN_PROGRESS,
            'active': WorkItemStatus.IN_PROGRESS,
            'done': WorkItemStatus.DONE,
            'closed': WorkItemStatus.DONE,
            'resolved': WorkItemStatus.DONE,
            'blocked': WorkItemStatus.BLOCKED,
            'cancelled': WorkItemStatus.CANCELLED
        }
        return mapping.get(jira_status.lower(), WorkItemStatus.TODO)
    
    def _map_jira_priority_to_unified(self, jira_priority: str) -> Priority:
        """Map JIRA priority to unified priority"""
        mapping = {
            'highest': Priority.CRITICAL,
            'high': Priority.HIGH,
            'medium': Priority.MEDIUM,
            'low': Priority.LOW,
            'lowest': Priority.LOW
        }
        return mapping.get(jira_priority.lower(), Priority.MEDIUM)
    
    def _map_github_status_to_unified(self, github_status: str) -> WorkItemStatus:
        """Map GitHub issue status to unified work item status"""
        mapping = {
            'open': WorkItemStatus.TODO,
            'closed': WorkItemStatus.DONE
        }
        return mapping.get(github_status.lower(), WorkItemStatus.TODO)
    
    def _map_azure_type_to_unified(self, azure_type: str) -> WorkItemType:
        """Map Azure DevOps work item type to unified type"""
        mapping = {
            'user story': WorkItemType.STORY,
            'task': WorkItemType.TASK,
            'bug': WorkItemType.BUG,
            'epic': WorkItemType.EPIC,
            'feature': WorkItemType.FEATURE
        }
        return mapping.get(azure_type.lower(), WorkItemType.TASK)
    
    def _map_azure_status_to_unified(self, azure_status: str) -> WorkItemStatus:
        """Map Azure DevOps status to unified status"""
        mapping = {
            'new': WorkItemStatus.TODO,
            'active': WorkItemStatus.IN_PROGRESS,
            'resolved': WorkItemStatus.DONE,
            'closed': WorkItemStatus.DONE,
            'removed': WorkItemStatus.CANCELLED
        }
        return mapping.get(azure_status.lower(), WorkItemStatus.TODO)
    
    def _post_process_response(self, response: UnifiedResponse, query: UnifiedQuery) -> UnifiedResponse:
        """Apply post-processing to the response (deduplication, sorting, filtering)"""
        # Apply limit if specified
        if query.limit:
            for entity_type in response.data:
                response.data[entity_type] = response.data[entity_type][:query.limit]
        
        # Apply sorting if specified
        if query.sort_by:
            for entity_type in response.data:
                try:
                    reverse = query.sort_order.lower() == 'desc'
                    response.data[entity_type].sort(
                        key=lambda x: getattr(x, query.sort_by, ''),
                        reverse=reverse
                    )
                except Exception as e:
                    current_app.logger.warning(f"Could not sort {entity_type.value} by {query.sort_by}: {str(e)}")
        
        # Add metadata about the response
        response.metadata = {
            'total_entities': sum(len(entities) for entities in response.data.values()),
            'entity_counts': {entity_type.value: len(entities) for entity_type, entities in response.data.items()},
            'query_applied': {
                'limit': query.limit,
                'sort_by': query.sort_by,
                'sort_order': query.sort_order,
                'filters': query.filters
            }
        }
        
        return response

# Global unified service instance
unified_service = UnifiedMCPService() 