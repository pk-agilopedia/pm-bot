from datetime import datetime, timezone
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"

class ToolType(enum.Enum):
    JIRA = "jira"
    AZURE_DEVOPS = "azure_devops"
    GITHUB = "github"
    SLACK = "slack"
    TEAMS = "teams"

class LLMProvider(enum.Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"

class RequestStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Base model with common fields
class BaseModel(db.Model):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))

# Tenant model (top level)
class Tenant(BaseModel):
    __tablename__ = 'tenants'
    
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    users = db.relationship('User', backref='tenant', lazy='dynamic')
    projects = db.relationship('Project', backref='tenant', lazy='dynamic')
    tools = db.relationship('Tool', backref='tenant', lazy='dynamic')

# Users table
class User(BaseModel):
    __tablename__ = 'users'
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    role = db.Column(db.Enum(UserRole), default=UserRole.VIEWER)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    teams_user_id = db.Column(db.String(200), unique=True, nullable=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self):
        return create_access_token(identity=self.id)

# Projects table
class Project(BaseModel):
    __tablename__ = 'projects'
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key = db.Column(db.String(20), nullable=False)  # Project key like PROJ-001
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    
    # Project manager
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    manager = db.relationship('User', backref='managed_projects')
    
    # Relationships
    project_tools = db.relationship('ProjectTool', backref='project', lazy='dynamic')
    chat_sessions = db.relationship('ChatSession', backref='project', lazy='dynamic')

# Tools table (JIRA, Azure DevOps, GitHub, etc.)
class Tool(BaseModel):
    __tablename__ = 'tools'
    
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    tool_type = db.Column(db.Enum(ToolType), nullable=False)
    base_url = db.Column(db.String(255))
    api_token = db.Column(db.String(500))  # Encrypted
    configuration = db.Column(db.JSON)  # Additional tool-specific config
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    project_tools = db.relationship('ProjectTool', backref='tool', lazy='dynamic')

# Many-to-many relationship between Projects and Tools
class ProjectTool(BaseModel):
    __tablename__ = 'project_tools'
    
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    tool_id = db.Column(db.Integer, db.ForeignKey('tools.id'), nullable=False)
    configuration = db.Column(db.JSON)  # Project-specific tool configuration
    is_active = db.Column(db.Boolean, default=True)

# Chat sessions for tracking conversations
class ChatSession(BaseModel):
    __tablename__ = 'chat_sessions'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', backref='chat_sessions')
    messages = db.relationship('ChatMessage', backref='session', lazy='dynamic')

# Individual chat messages
class ChatMessage(BaseModel):
    __tablename__ = 'chat_messages'
    
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'), nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # user, assistant, system
    content = db.Column(db.Text, nullable=False)
    message_metadata = db.Column(db.JSON)  # Additional message metadata
    
    # LLM usage tracking
    llm_provider = db.Column(db.Enum(LLMProvider))
    model_name = db.Column(db.String(100))
    tokens_used = db.Column(db.Integer)
    cost = db.Column(db.Numeric(10, 6))

# Token usage tracking for cost analysis
class TokenUsage(BaseModel):
    __tablename__ = 'token_usage'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'))
    
    llm_provider = db.Column(db.Enum(LLMProvider), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    
    # Token details
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    
    # Cost details
    prompt_cost = db.Column(db.Numeric(10, 6), default=0)
    completion_cost = db.Column(db.Numeric(10, 6), default=0)
    total_cost = db.Column(db.Numeric(10, 6), default=0)
    
    # Request details
    request_id = db.Column(db.String(100))
    response_time_ms = db.Column(db.Integer)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.COMPLETED)
    
    # Relationships
    user = db.relationship('User', backref='token_usage')
    project = db.relationship('Project', backref='token_usage')
    session = db.relationship('ChatSession', backref='token_usage')

# API usage tracking
class APIUsage(BaseModel):
    __tablename__ = 'api_usage'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    
    tool_type = db.Column(db.Enum(ToolType), nullable=False)
    endpoint = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    
    # Request details
    request_size_bytes = db.Column(db.Integer)
    response_size_bytes = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    status_code = db.Column(db.Integer)
    
    # Cost tracking (if applicable)
    cost = db.Column(db.Numeric(10, 6), default=0)
    
    # Relationships
    user = db.relationship('User', backref='api_usage')
    project = db.relationship('Project', backref='api_usage')

# Agent execution tracking
class AgentExecution(BaseModel):
    __tablename__ = 'agent_executions'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    session_id = db.Column(db.Integer, db.ForeignKey('chat_sessions.id'))
    
    agent_type = db.Column(db.String(50), nullable=False)  # project_analysis, sprint_planning, etc.
    task_description = db.Column(db.Text)
    
    # Execution details
    start_time = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Integer)
    status = db.Column(db.Enum(RequestStatus), default=RequestStatus.PENDING)
    
    # Results
    output = db.Column(db.JSON)
    error_message = db.Column(db.Text)
    
    # Cost tracking
    total_tokens = db.Column(db.Integer, default=0)
    total_cost = db.Column(db.Numeric(10, 6), default=0)
    
    # Relationships
    user = db.relationship('User', backref='agent_executions')
    project = db.relationship('Project', backref='agent_executions')
    session = db.relationship('ChatSession', backref='agent_executions')

# System configuration for dynamic settings
class SystemConfig(BaseModel):
    __tablename__ = 'system_config'
    
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

# Model pricing for cost calculations
class ModelPricing(BaseModel):
    __tablename__ = 'model_pricing'
    
    provider = db.Column(db.Enum(LLMProvider), nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    prompt_price_per_1k = db.Column(db.Numeric(10, 6), nullable=False)
    completion_price_per_1k = db.Column(db.Numeric(10, 6), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    is_active = db.Column(db.Boolean, default=True) 