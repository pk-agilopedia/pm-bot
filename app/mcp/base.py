from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class MCPResponse:
    success: bool
    data: Any = None
    error: str = None
    metadata: Dict[str, Any] = None

@dataclass
class WorkItem:
    id: str
    title: str
    description: str
    status: str
    assignee: Optional[str] = None
    labels: List[str] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    priority: Optional[str] = None
    story_points: Optional[int] = None
    metadata: Dict[str, Any] = None

@dataclass
class Repository:
    id: str
    name: str
    full_name: str
    url: str
    default_branch: str
    language: str = None
    stars: int = 0
    forks: int = 0
    issues_count: int = 0
    pull_requests_count: int = 0

@dataclass
class PullRequest:
    id: str
    title: str
    description: str
    status: str
    source_branch: str
    target_branch: str
    author: str
    created_date: datetime
    updated_date: datetime
    url: str

@dataclass
class Sprint:
    id: str
    name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goal: Optional[str] = None
    capacity: Optional[int] = None
    work_items: List[WorkItem] = None

class BaseMCPProvider(ABC):
    """Base class for MCP (Model Context Protocol) providers"""
    
    def __init__(self, base_url: str, auth_token: str, config: Dict[str, Any] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.config = config or {}
    
    @abstractmethod
    def test_connection(self) -> MCPResponse:
        """Test the connection to the service"""
        pass
    
    @abstractmethod
    def get_projects(self) -> MCPResponse:
        """Get list of projects"""
        pass
    
    @abstractmethod
    def get_work_items(self, project_id: str, **filters) -> MCPResponse:
        """Get work items from a project"""
        pass
    
    @abstractmethod
    def create_work_item(self, project_id: str, work_item: WorkItem) -> MCPResponse:
        """Create a new work item"""
        pass
    
    @abstractmethod
    def update_work_item(self, project_id: str, work_item_id: str, 
                        updates: Dict[str, Any]) -> MCPResponse:
        """Update an existing work item"""
        pass
    
    @abstractmethod
    def get_work_item_comments(self, project_id: str, work_item_id: str) -> MCPResponse:
        """Get comments for a work item"""
        pass
    
    def get_team_members(self, project_id: str) -> MCPResponse:
        """Get team members for a project (optional implementation)"""
        return MCPResponse(success=False, error="Not implemented")
    
    def get_sprints(self, project_id: str) -> MCPResponse:
        """Get sprints for a project (optional implementation)"""
        return MCPResponse(success=False, error="Not implemented")
    
    def create_sprint(self, project_id: str, sprint: Sprint) -> MCPResponse:
        """Create a new sprint (optional implementation)"""
        return MCPResponse(success=False, error="Not implemented")

class BaseRepositoryProvider(ABC):
    """Base class for repository providers (GitHub, Azure Repos, etc.)"""
    
    def __init__(self, base_url: str, auth_token: str, config: Dict[str, Any] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.config = config or {}
    
    @abstractmethod
    def test_connection(self) -> MCPResponse:
        """Test the connection to the service"""
        pass
    
    @abstractmethod
    def get_repositories(self, org: str = None) -> MCPResponse:
        """Get list of repositories"""
        pass
    
    @abstractmethod
    def get_repository(self, repo_name: str, org: str = None) -> MCPResponse:
        """Get repository details"""
        pass
    
    @abstractmethod
    def get_pull_requests(self, repo_name: str, org: str = None, 
                         state: str = "open") -> MCPResponse:
        """Get pull requests"""
        pass
    
    @abstractmethod
    def get_issues(self, repo_name: str, org: str = None, 
                  state: str = "open") -> MCPResponse:
        """Get repository issues"""
        pass
    
    @abstractmethod
    def get_commits(self, repo_name: str, org: str = None, 
                   branch: str = None) -> MCPResponse:
        """Get repository commits"""
        pass
    
    @abstractmethod
    def get_branches(self, repo_name: str, org: str = None) -> MCPResponse:
        """Get repository branches"""
        pass

class MCPRegistry:
    """Registry for managing MCP providers"""
    
    def __init__(self):
        self._providers: Dict[str, BaseMCPProvider] = {}
        self._repo_providers: Dict[str, BaseRepositoryProvider] = {}
    
    def register_provider(self, name: str, provider: BaseMCPProvider):
        """Register an MCP provider"""
        self._providers[name] = provider
    
    def register_repo_provider(self, name: str, provider: BaseRepositoryProvider):
        """Register a repository provider"""
        self._repo_providers[name] = provider
    
    def get_provider(self, name: str) -> Optional[BaseMCPProvider]:
        """Get an MCP provider by name"""
        return self._providers.get(name)
    
    def get_repo_provider(self, name: str) -> Optional[BaseRepositoryProvider]:
        """Get a repository provider by name"""
        return self._repo_providers.get(name)
    
    def list_providers(self) -> List[str]:
        """List all registered MCP providers"""
        return list(self._providers.keys())
    
    def list_repo_providers(self) -> List[str]:
        """List all registered repository providers"""
        return list(self._repo_providers.keys())

# Global registry instance
mcp_registry = MCPRegistry() 