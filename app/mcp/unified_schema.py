from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

class EntityType(Enum):
    WORK_ITEM = "work_item"
    SPRINT = "sprint"
    USER = "user"
    PROJECT = "project"
    REPOSITORY = "repository"
    PULL_REQUEST = "pull_request"
    COMMIT = "commit"
    MILESTONE = "milestone"
    LABEL = "label"
    COMMENT = "comment"

class WorkItemType(Enum):
    TASK = "task"
    STORY = "story"
    BUG = "bug"
    EPIC = "epic"
    FEATURE = "feature"
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"

class WorkItemStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class UnifiedUser:
    id: str
    name: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    source_tool: Optional[str] = None
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnifiedWorkItem:
    id: str
    title: str
    description: Optional[str] = None
    type: WorkItemType = WorkItemType.TASK
    status: WorkItemStatus = WorkItemStatus.TODO
    priority: Priority = Priority.MEDIUM
    assignee: Optional[UnifiedUser] = None
    reporter: Optional[UnifiedUser] = None
    labels: List[str] = field(default_factory=list)
    story_points: Optional[int] = None
    epic_link: Optional[str] = None
    sprint_id: Optional[str] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    source_tool: Optional[str] = None
    source_url: Optional[str] = None
    comments: List['UnifiedComment'] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnifiedSprint:
    id: str
    name: str
    state: str  # future, active, closed
    goal: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    capacity: Optional[int] = None
    work_items: List[UnifiedWorkItem] = field(default_factory=list)
    source_tool: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnifiedRepository:
    id: str
    name: str
    full_name: str
    description: Optional[str] = None
    url: Optional[str] = None
    default_branch: str = "main"
    language: Optional[str] = None
    stars: int = 0
    forks: int = 0
    open_issues: int = 0
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    source_tool: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnifiedPullRequest:
    id: str
    title: str
    description: Optional[str] = None
    state: Optional[str] = "open"  # open, closed, merged
    author: Optional[UnifiedUser] = None
    assignees: List[UnifiedUser] = field(default_factory=list)
    reviewers: List[UnifiedUser] = field(default_factory=list)
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    merged_date: Optional[datetime] = None
    commits_count: int = 0
    additions: int = 0
    deletions: int = 0
    source_tool: Optional[str] = None
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnifiedCommit:
    id: str
    sha: str
    message: str
    author: Optional[UnifiedUser] = None
    committer: Optional[UnifiedUser] = None
    timestamp: Optional[datetime] = None
    additions: int = 0
    deletions: int = 0
    files_changed: List[str] = field(default_factory=list)
    source_tool: Optional[str] = None
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnifiedComment:
    id: str
    content: str
    author: Optional[UnifiedUser] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    parent_id: Optional[str] = None
    source_tool: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UnifiedProject:
    id: str
    name: str
    key: str
    description: Optional[str] = None
    lead: Optional[UnifiedUser] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = "active"
    work_items: List[UnifiedWorkItem] = field(default_factory=list)
    sprints: List[UnifiedSprint] = field(default_factory=list)
    repositories: List[UnifiedRepository] = field(default_factory=list)
    source_tool: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# Query and response structures for unified operations
@dataclass
class UnifiedQuery:
    """Represents a query that can be executed across multiple tools"""
    entities: List[EntityType]
    filters: Dict[str, Any] = field(default_factory=dict)
    include_related: List[EntityType] = field(default_factory=list)
    limit: Optional[int] = None
    offset: Optional[int] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"

@dataclass
class UnifiedResponse:
    """Unified response containing data from multiple tools"""
    success: bool
    data: Dict[EntityType, List[Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    source_tools: List[str] = field(default_factory=list)

# Tool capability definitions
@dataclass
class ToolCapabilities:
    """Defines what capabilities a tool has"""
    tool_name: str
    supported_entities: List[EntityType]
    supported_operations: List[str]  # read, create, update, delete
    real_time_data: bool = True
    rate_limits: Dict[str, int] = field(default_factory=dict)
    authentication_required: bool = True

# Standard tool capabilities
TOOL_CAPABILITIES = {
    "jira": ToolCapabilities(
        tool_name="jira",
        supported_entities=[EntityType.WORK_ITEM, EntityType.SPRINT, EntityType.USER, EntityType.PROJECT, EntityType.COMMENT],
        supported_operations=["read", "create", "update", "delete"],
        real_time_data=True,
        rate_limits={"requests_per_minute": 300}
    ),
    "github": ToolCapabilities(
        tool_name="github",
        supported_entities=[EntityType.REPOSITORY, EntityType.WORK_ITEM, EntityType.PULL_REQUEST, EntityType.COMMIT, EntityType.USER, EntityType.COMMENT],
        supported_operations=["read", "create", "update"],
        real_time_data=True,
        rate_limits={"requests_per_hour": 5000}
    ),
    "azure_devops": ToolCapabilities(
        tool_name="azure_devops",
        supported_entities=[EntityType.WORK_ITEM, EntityType.SPRINT, EntityType.USER, EntityType.PROJECT, EntityType.REPOSITORY],
        supported_operations=["read", "create", "update", "delete"],
        real_time_data=True,
        rate_limits={"requests_per_minute": 200}
    )
} 