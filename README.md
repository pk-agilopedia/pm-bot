## PM Bot API

A sophisticated project management bot API that integrates with JIRA, Azure DevOps, and GitHub to provide intelligent project analysis and automation through AI agents.

### Key Features

- **Real-time Integration**: Direct API connections to JIRA, GitHub, and Azure DevOps
- **AI Agent System**: Specialized agents for different PM tasks (analysis, backlog generation, sprint planning)
- **Multi-tenant Architecture**: Support for multiple organizations
- **JWT Authentication**: Secure user authentication and authorization
- **LLM Integration**: Support for OpenAI GPT and Anthropic Claude models
- **Real Data Only**: No mock data or simulated responses - all functionality uses real API integrations

### Architecture

- **Flask-based API**: RESTful endpoints for all operations
- **SQLAlchemy ORM**: Database management with MySQL support
- **MCP (Model Context Protocol)**: Standardized integration layer for external tools
- **Agent Registry**: Intelligent routing system for AI agents
- **Real-time Data**: All project data comes from actual tool integrations

### Prerequisites

- Python 3.8+
- MySQL 8.0+
- Valid API tokens for:
  - JIRA (Atlassian API token)
  - GitHub (Personal Access Token)
  - Azure DevOps (Personal Access Token) - optional
- OpenAI API key or Anthropic API key

### Quick Start

1. **Clone and setup**
   ```bash
   git clone <repository-url>
   cd pm-bot-api
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and database credentials
   ```

3. **Initialize database**
   ```bash
   python init_db.py
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

### Required Environment Variables

```env
# Database
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/pmbot

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# LLM Provider (choose one)
OPENAI_API_KEY=sk-your-openai-key
# OR
ANTHROPIC_API_KEY=your-anthropic-key

# JIRA Integration (Required)
JIRA_SERVER_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=YOUR_PROJECT_KEY

# GitHub Integration (Required)
GITHUB_TOKEN=ghp_your-github-token
GITHUB_REPO_OWNER=your-github-username
GITHUB_REPO_NAME=your-repo-name
GITHUB_BASE_URL=https://api.github.com

# Azure DevOps Integration (Optional)
AZURE_DEVOPS_ORG=your-organization
AZURE_DEVOPS_TOKEN=your-pat-token
AZURE_DEVOPS_PROJECT=your-project-name
```

## Features

### 🤖 Intelligent Agent Architecture
The system uses a streamlined 3-agent architecture for optimal performance and maintainability:

- **Main Agent**: Intelligent request router that analyzes user intent using LLM and delegates to specialized agents
- **Analysis Agent**: Handles all analysis, reporting, metrics, and insights (project health, team performance, progress tracking, risk assessment)
- **Management Agent**: Handles all CRUD operations for work items, sprints, backlogs, and project resources (creating, updating, assigning, planning)

#### Agent Routing Flow:
1. User sends message to `/api/v1/messages` endpoint
2. MainAgent analyzes intent using LLM-powered classification
3. Routes to AnalysisAgent for reporting/metrics or ManagementAgent for creating/updating items
4. Specialized agent executes the task and returns results
5. Response includes routing information for transparency

### 🔌 Multi-LLM Support
- OpenAI GPT models
- Azure OpenAI
- Anthropic Claude
- Easy model switching with factory pattern
- Cost tracking and token usage monitoring

### 🛠️ MCP (Model Context Protocol) Integrations
- **Azure DevOps**: Work items, sprints, teams, and projects
- **JIRA**: Issues, boards, sprints, and projects
- **GitHub**: Repositories, issues, pull requests, and commits
- Extensible architecture for additional tools

### 💬 Multi-Interface Support
- Web interface
- Microsoft Teams integration
- Slack integration
- RESTful API for custom integrations

### 🏢 Multi-Tenant Architecture
- Tenant isolation
- User management with role-based access
- Project-level tool configurations

### 📊 Cost & Usage Tracking
- Token usage monitoring
- Cost analysis per user/project
- Performance metrics
- Execution history

## API Documentation

### Authentication Endpoints

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepassword",
  "tenant_slug": "demo",
  "first_name": "John",
  "last_name": "Doe"
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "johndoe",
  "password": "securepassword"
}
```

### Chat Interface

#### Send Message
```http
POST /api/v1/messages
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "message": "Analyze the current project health",
  "project_id": 1,
  "interface": "web"
}
```

#### Get Conversation History
```http
GET /api/v1/messages/history/<session_id>
Authorization: Bearer <jwt_token>
```

### Project Management

#### Get Projects
```http
GET /api/v1/projects
Authorization: Bearer <jwt_token>
```

#### Create Project
```http
POST /api/v1/projects
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "My Project",
  "key": "MYPROJ",
  "description": "Project description",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

### Tool Management

#### Get Tools
```http
GET /api/v1/tools
Authorization: Bearer <jwt_token>
```

#### Create Tool Configuration
```http
POST /api/v1/tools
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "name": "JIRA Production",
  "tool_type": "jira",
  "base_url": "https://company.atlassian.net",
  "api_token": "your-api-token",
  "configuration": {
    "username": "your-email@company.com"
  }
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application environment | `development` |
| `DEBUG` | Debug mode | `True` |
| `SECRET_KEY` | Flask secret key | Required |
| `JWT_SECRET_KEY` | JWT signing key | Required |
| `DATABASE_URL` | Database connection string | Required |
| `OPENAI_API_KEY` | OpenAI API key | Optional |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `DEFAULT_LLM_PROVIDER` | Default LLM provider | `openai` |

### Tool Integration Setup

#### JIRA Setup
1. Create an API token in your Atlassian account
2. Add tool configuration via API or admin interface
3. Configure project-tool associations

#### Azure DevOps Setup
1. Create a Personal Access Token (PAT)
2. Ensure PAT has required permissions for work items, projects
3. Add tool configuration with organization name

#### GitHub Setup
1. Create a Personal Access Token
2. Grant necessary repository permissions
3. Add tool configuration

## Architecture

### AI Agent System
The system uses a multi-agent architecture where different specialized agents handle specific types of queries:

- **Agent Registry**: Manages available agents and routes queries
- **Base Agent**: Common functionality and context management
- **Specialized Agents**: Domain-specific intelligence for different PM tasks

### MCP (Model Context Protocol)
Extensible integration layer that provides standardized interfaces for:
- Work item management across different tools
- Repository operations
- Project and team data access

### Database Schema
- **Multi-tenant**: Tenants → Projects → Tools
- **User Management**: Role-based access control
- **Chat History**: Conversation tracking and context
- **Usage Tracking**: Token usage, costs, performance metrics

## Deployment

### Production Deployment with Docker

1. **Build and deploy**
   ```bash
   # Build production image
   docker build -t pmbot-api:latest .
   
   # Run with production environment
   docker run -d \
     --name pmbot-api \
     -p 5000:5000 \
     -e ENVIRONMENT=production \
     -e DATABASE_URL=mysql+pymysql://user:pass@host:3306/pmbot \
     pmbot-api:latest
   ```

2. **With nginx reverse proxy**
   ```bash
   # Use docker-compose for full stack
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Environment Configuration

Create appropriate `.env` files for each environment:
- `.env.development`
- `.env.production`
- `.env.testing`

## Development

### Adding New Agents

1. **Create agent class**
   ```python
   from app.agents.base import BaseAgent, AgentContext, AgentResponse
   
   class MyCustomAgent(BaseAgent):
       def __init__(self):
           super().__init__("my_agent", "Description of my agent")
       
       def execute(self, query: str, context: AgentContext) -> AgentResponse:
           # Implementation
           pass
       
       def get_system_prompt(self, context: AgentContext) -> str:
           return "System prompt for the agent"
   ```

2. **Register agent**
   ```python
   from app.agents.base import agent_registry
   
   my_agent = MyCustomAgent()
   agent_registry.register_agent(my_agent)
   ```

### Adding New MCP Providers

1. **Implement provider interface**
   ```python
   from app.mcp.base import BaseMCPProvider, MCPResponse
   
   class MyToolProvider(BaseMCPProvider):
       def test_connection(self) -> MCPResponse:
           # Implementation
           pass
       
       def get_work_items(self, project_id: str, **filters) -> MCPResponse:
           # Implementation
           pass
   ```

2. **Register provider**
   ```python
   from app.mcp import mcp_registry
   
   provider = MyToolProvider(base_url, auth_token)
   mcp_registry.register_provider("my_tool", provider)
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the API examples

## Roadmap

- [ ] Additional AI agents (Risk Assessment, Report Generation)
- [ ] More MCP integrations (Confluence, ServiceNow)
- [ ] Advanced analytics and dashboards
- [ ] Mobile app support
- [ ] Real-time notifications
- [ ] Advanced workflow automation 