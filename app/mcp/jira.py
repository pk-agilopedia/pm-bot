import requests
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from .base import BaseMCPProvider, MCPResponse, WorkItem, Sprint
import json

class JiraProvider(BaseMCPProvider):
    """JIRA MCP Provider"""
    
    def __init__(self, server_url: str, username: str, api_token: str, config: Dict[str, Any] = None):
        super().__init__(server_url, api_token, config)
        self.username = username
        
        # Setup authentication
        auth_string = f"{username}:{api_token}"
        auth_bytes = base64.b64encode(auth_string.encode()).decode()
        
        self.auth_header = {
            'Authorization': f'Basic {auth_bytes}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Check if this is a mock instance
        self.is_mock = config.get('is_mock', False) if config else False
    
    def _get_mock_work_items(self, project_id: str) -> List[WorkItem]:
        """Generate mock work items for testing"""
        today = datetime.utcnow()
        
        mock_items = [
            # Sprint 1 items (completed)
            WorkItem(
                id="SAMPLE-1",
                title="Setup project repository",
                description="Initialize git repository and project structure",
                status="Done",
                assignee="John Doe",
                labels=["infrastructure", "setup"],
                created_date=today - timedelta(days=20),
                updated_date=today - timedelta(days=8),
                priority="High",
                story_points=3,
                metadata={
                    'issue_type': 'Story',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-1"
                }
            ),
            WorkItem(
                id="SAMPLE-2",
                title="Configure development environment",
                description="Setup Docker, dependencies, and development tools",
                status="Done",
                assignee="Jane Smith",
                labels=["infrastructure", "docker"],
                created_date=today - timedelta(days=19),
                updated_date=today - timedelta(days=8),
                priority="High",
                story_points=5,
                metadata={
                    'issue_type': 'Story',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-2"
                }
            ),
            WorkItem(
                id="SAMPLE-3",
                title="Create basic API structure",
                description="Setup Flask app with basic routes and authentication",
                status="Done",
                assignee="Mike Johnson",
                labels=["backend", "api"],
                created_date=today - timedelta(days=18),
                updated_date=today - timedelta(days=9),
                priority="Medium",
                story_points=8,
                metadata={
                    'issue_type': 'Story',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-3"
                }
            ),
            
            # Sprint 2 items (current)
            WorkItem(
                id="SAMPLE-4",
                title="Implement user management",
                description="Create user registration, login, and profile management",
                status="In Progress",
                assignee="John Doe",
                labels=["backend", "authentication"],
                created_date=today - timedelta(days=10),
                updated_date=today - timedelta(days=1),
                priority="High",
                story_points=13,
                metadata={
                    'issue_type': 'Story',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-4"
                }
            ),
            WorkItem(
                id="SAMPLE-5",
                title="Add project management features",
                description="Create project CRUD operations and team management",
                status="In Progress",
                assignee="Sarah Wilson",
                labels=["backend", "project-management"],
                created_date=today - timedelta(days=9),
                updated_date=today,
                priority="Medium",
                story_points=8,
                metadata={
                    'issue_type': 'Story',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-5"
                }
            ),
            WorkItem(
                id="SAMPLE-6",
                title="Fix authentication bug",
                description="Token expiration not working correctly",
                status="To Do",
                assignee="Mike Johnson",
                labels=["bug", "authentication"],
                created_date=today - timedelta(days=3),
                updated_date=today - timedelta(days=3),
                priority="High",
                story_points=2,
                metadata={
                    'issue_type': 'Bug',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-6"
                }
            ),
            WorkItem(
                id="SAMPLE-7",
                title="Write API documentation",
                description="Document all API endpoints with examples",
                status="To Do",
                assignee="Jane Smith",
                labels=["documentation"],
                created_date=today - timedelta(days=2),
                updated_date=today - timedelta(days=2),
                priority="Low",
                story_points=5,
                metadata={
                    'issue_type': 'Task',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-7"
                }
            ),
            
            # Sprint 3 items (planned)
            WorkItem(
                id="SAMPLE-8",
                title="Create analytics dashboard",
                description="Build reporting interface for project metrics",
                status="To Do",
                assignee=None,
                labels=["frontend", "analytics"],
                created_date=today - timedelta(days=1),
                updated_date=today - timedelta(days=1),
                priority="Medium",
                story_points=13,
                metadata={
                    'issue_type': 'Story',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-8"
                }
            ),
            WorkItem(
                id="SAMPLE-9",
                title="Add email notifications",
                description="Send notifications for important events",
                status="To Do",
                assignee=None,
                labels=["backend", "notifications"],
                created_date=today,
                updated_date=today,
                priority="Low",
                story_points=8,
                metadata={
                    'issue_type': 'Story',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-9"
                }
            ),
            
            # Backlog items
            WorkItem(
                id="SAMPLE-10",
                title="Implement mobile app",
                description="Create mobile application for iOS and Android",
                status="Backlog",
                assignee=None,
                labels=["mobile", "epic"],
                created_date=today,
                updated_date=today,
                priority="Low",
                story_points=21,
                metadata={
                    'issue_type': 'Epic',
                    'project_key': project_id,
                    'url': f"{self.base_url}/browse/SAMPLE-10"
                }
            )
        ]
        
        return mock_items
    
    def _get_mock_sprints(self, project_id: str) -> List[Sprint]:
        """Generate mock sprints for testing"""
        today = datetime.utcnow()
        
        mock_sprints = [
            Sprint(
                id="1",
                name="Sprint 1",
                state="closed",
                start_date=today - timedelta(days=21),
                end_date=today - timedelta(days=7),
                goal="Setup project foundation and basic features"
            ),
            Sprint(
                id="2",
                name="Sprint 2",
                state="active",
                start_date=today - timedelta(days=7),
                end_date=today + timedelta(days=7),
                goal="Implement core functionality and user management"
            ),
            Sprint(
                id="3",
                name="Sprint 3",
                state="future",
                start_date=today + timedelta(days=7),
                end_date=today + timedelta(days=21),
                goal="Add reporting and analytics features"
            )
        ]
        
        return mock_sprints

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to JIRA API"""
        url = f"{self.base_url}/rest/api/3/{endpoint}"
        kwargs.setdefault('headers', {}).update(self.auth_header)
        
        response = requests.request(method, url, **kwargs)
        return response
    
    def test_connection(self) -> MCPResponse:
        """Test connection to JIRA"""
        if self.is_mock:
            return MCPResponse(success=True, data={
                "message": "Mock connection successful",
                "user": "Mock User"
            })
            
        try:
            response = self._make_request('GET', 'myself')
            if response.status_code == 200:
                user_data = response.json()
                return MCPResponse(success=True, data={
                    "message": "Connection successful",
                    "user": user_data.get('displayName')
                })
            else:
                return MCPResponse(success=False, error=f"Connection failed: {response.status_code}")
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_projects(self) -> MCPResponse:
        """Get list of JIRA projects"""
        if self.is_mock:
            return MCPResponse(success=True, data=[{
                'id': '1',
                'key': 'SAMPLE',
                'name': 'Sample Project',
                'description': 'A sample project for testing PM Bot',
                'lead': 'Project Manager',
                'projectTypeKey': 'software',
                'url': f"{self.base_url}/projects/SAMPLE"
            }])
            
        try:
            response = self._make_request('GET', 'project')
            
            if response.status_code == 200:
                projects_data = response.json()
                projects = []
                
                for project in projects_data:
                    projects.append({
                        'id': project['id'],
                        'key': project['key'],
                        'name': project['name'],
                        'description': project.get('description', ''),
                        'lead': project.get('lead', {}).get('displayName'),
                        'projectTypeKey': project.get('projectTypeKey'),
                        'url': project.get('self')
                    })
                
                return MCPResponse(success=True, data=projects)
            else:
                return MCPResponse(success=False, error=f"Failed to get projects: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_work_items(self, project_id: str, **filters) -> MCPResponse:
        """Get issues from JIRA project"""
        if self.is_mock:
            return MCPResponse(success=True, data=self._get_mock_work_items(project_id))
            
        try:
            # Build JQL query based on filters
            jql_parts = [f'project = "{project_id}"']
            
            if filters.get('status'):
                jql_parts.append(f'status = "{filters["status"]}"')
            
            if filters.get('assignee'):
                jql_parts.append(f'assignee = "{filters["assignee"]}"')
            
            if filters.get('issue_type'):
                jql_parts.append(f'issuetype = "{filters["issue_type"]}"')
            
            if filters.get('sprint'):
                jql_parts.append(f'sprint = "{filters["sprint"]}"')
            
            jql = ' AND '.join(jql_parts)
            
            params = {
                'jql': jql,
                'fields': 'summary,description,status,assignee,labels,created,updated,priority,customfield_10016',  # customfield_10016 is usually story points
                'maxResults': filters.get('max_results', 100)
            }
            
            response = self._make_request('GET', 'search', params=params)
            
            if response.status_code == 200:
                data = response.json()
                work_items = []
                
                for issue in data.get('issues', []):
                    fields = issue.get('fields', {})
                    
                    work_item = WorkItem(
                        id=issue['key'],
                        title=fields.get('summary', ''),
                        description=fields.get('description', {}).get('content', [{}])[0].get('content', [{}])[0].get('text', '') if fields.get('description') else '',
                        status=fields.get('status', {}).get('name', ''),
                        assignee=fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
                        labels=fields.get('labels', []),
                        created_date=datetime.fromisoformat(fields.get('created', '').replace('Z', '+00:00')) if fields.get('created') else None,
                        updated_date=datetime.fromisoformat(fields.get('updated', '').replace('Z', '+00:00')) if fields.get('updated') else None,
                        priority=fields.get('priority', {}).get('name') if fields.get('priority') else None,
                        story_points=fields.get('customfield_10016'),  # Story points custom field
                        metadata={
                            'issue_type': fields.get('issuetype', {}).get('name'),
                            'project_key': issue['key'].split('-')[0],
                            'url': f"{self.base_url}/browse/{issue['key']}"
                        }
                    )
                    work_items.append(work_item)
                
                return MCPResponse(success=True, data=work_items)
            else:
                return MCPResponse(success=False, error=f"Failed to get issues: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def create_work_item(self, project_id: str, work_item: WorkItem) -> MCPResponse:
        """Create a new issue in JIRA"""
        try:
            # Default issue type if not specified
            issue_type = work_item.metadata.get('issue_type', 'Story') if work_item.metadata else 'Story'
            
            issue_data = {
                "fields": {
                    "project": {"key": project_id},
                    "summary": work_item.title,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": work_item.description
                                    }
                                ]
                            }
                        ]
                    },
                    "issuetype": {"name": issue_type}
                }
            }
            
            if work_item.assignee:
                issue_data["fields"]["assignee"] = {"displayName": work_item.assignee}
            
            if work_item.priority:
                issue_data["fields"]["priority"] = {"name": work_item.priority}
            
            if work_item.labels:
                issue_data["fields"]["labels"] = [{"name": label} for label in work_item.labels]
            
            if work_item.story_points:
                issue_data["fields"]["customfield_10016"] = work_item.story_points
            
            response = self._make_request('POST', 'issue', json=issue_data)
            
            if response.status_code == 201:
                created_issue = response.json()
                return MCPResponse(success=True, data={
                    'key': created_issue['key'],
                    'id': created_issue['id'],
                    'url': f"{self.base_url}/browse/{created_issue['key']}"
                })
            else:
                return MCPResponse(success=False, error=f"Failed to create issue: {response.status_code} - {response.text}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def update_work_item(self, project_id: str, work_item_id: str, updates: Dict[str, Any]) -> MCPResponse:
        """Update an existing issue"""
        try:
            update_data = {"fields": {}}
            
            field_mapping = {
                'title': 'summary',
                'description': 'description',
                'assignee': 'assignee',
                'priority': 'priority',
                'labels': 'labels',
                'story_points': 'customfield_10016'
            }
            
            for key, value in updates.items():
                if key in field_mapping:
                    jira_field = field_mapping[key]
                    
                    if key == 'description':
                        update_data["fields"][jira_field] = {
                            "type": "doc",
                            "version": 1,
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": value
                                        }
                                    ]
                                }
                            ]
                        }
                    elif key == 'assignee':
                        update_data["fields"][jira_field] = {"displayName": value}
                    elif key == 'priority':
                        update_data["fields"][jira_field] = {"name": value}
                    elif key == 'labels':
                        update_data["fields"][jira_field] = [{"name": label} for label in value] if isinstance(value, list) else [{"name": value}]
                    else:
                        update_data["fields"][jira_field] = value
            
            # Handle status separately with transition
            if 'status' in updates:
                # First, get available transitions
                transitions_response = self._make_request('GET', f'issue/{work_item_id}/transitions')
                
                if transitions_response.status_code == 200:
                    transitions = transitions_response.json().get('transitions', [])
                    target_transition = None
                    
                    for transition in transitions:
                        if transition['to']['name'].lower() == updates['status'].lower():
                            target_transition = transition
                            break
                    
                    if target_transition:
                        transition_data = {
                            "transition": {"id": target_transition['id']}
                        }
                        self._make_request('POST', f'issue/{work_item_id}/transitions', json=transition_data)
            
            # Update other fields
            if update_data["fields"]:
                response = self._make_request('PUT', f'issue/{work_item_id}', json=update_data)
                
                if response.status_code == 204:
                    return MCPResponse(success=True, data={
                        'key': work_item_id,
                        'url': f"{self.base_url}/browse/{work_item_id}"
                    })
                else:
                    return MCPResponse(success=False, error=f"Failed to update issue: {response.status_code}")
            
            return MCPResponse(success=True, data={
                'key': work_item_id,
                'url': f"{self.base_url}/browse/{work_item_id}"
            })
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_work_item_comments(self, project_id: str, work_item_id: str) -> MCPResponse:
        """Get comments for an issue"""
        try:
            response = self._make_request('GET', f'issue/{work_item_id}/comment')
            
            if response.status_code == 200:
                data = response.json()
                comments = []
                
                for comment in data.get('comments', []):
                    comments.append({
                        'id': comment['id'],
                        'body': comment['body']['content'][0]['content'][0]['text'] if comment.get('body', {}).get('content') else '',
                        'author': comment.get('author', {}).get('displayName'),
                        'created': comment.get('created'),
                        'updated': comment.get('updated')
                    })
                
                return MCPResponse(success=True, data=comments)
            else:
                return MCPResponse(success=False, error=f"Failed to get comments: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_sprints(self, project_id: str) -> MCPResponse:
        """Get sprints for a project"""
        if self.is_mock:
            return MCPResponse(success=True, data=self._get_mock_sprints(project_id))
            
        try:
            # First get boards for the project
            boards_response = self._make_request('GET', f'../../rest/agile/1.0/board', 
                                                params={'projectKeyOrId': project_id})
            
            if boards_response.status_code != 200:
                return MCPResponse(success=False, error=f"Failed to get boards: {boards_response.status_code}")
            
            boards_data = boards_response.json()
            all_sprints = []
            
            # Get sprints for each board
            for board in boards_data.get('values', []):
                board_id = board['id']
                sprints_response = self._make_request('GET', f'../../rest/agile/1.0/board/{board_id}/sprint')
                
                if sprints_response.status_code == 200:
                    sprints_data = sprints_response.json()
                    
                    for sprint in sprints_data.get('values', []):
                        sprint_obj = Sprint(
                            id=str(sprint['id']),
                            name=sprint['name'],
                            state=sprint['state'],
                            start_date=datetime.fromisoformat(sprint.get('startDate', '').replace('Z', '+00:00')) if sprint.get('startDate') else None,
                            end_date=datetime.fromisoformat(sprint.get('endDate', '').replace('Z', '+00:00')) if sprint.get('endDate') else None,
                            goal=sprint.get('goal')
                        )
                        all_sprints.append(sprint_obj)
            
            return MCPResponse(success=True, data=all_sprints)
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def create_sprint(self, project_id: str, sprint: Sprint) -> MCPResponse:
        """Create a new sprint"""
        try:
            # First get boards for the project
            boards_response = self._make_request('GET', f'../../rest/agile/1.0/board', 
                                                params={'projectKeyOrId': project_id})
            
            if boards_response.status_code != 200:
                return MCPResponse(success=False, error=f"Failed to get boards: {boards_response.status_code}")
            
            boards_data = boards_response.json()
            if not boards_data.get('values'):
                return MCPResponse(success=False, error="No boards found for project")
            
            # Use the first board
            board_id = boards_data['values'][0]['id']
            
            sprint_data = {
                "name": sprint.name,
                "originBoardId": board_id
            }
            
            if sprint.start_date:
                sprint_data["startDate"] = sprint.start_date.isoformat()
            
            if sprint.end_date:
                sprint_data["endDate"] = sprint.end_date.isoformat()
            
            if sprint.goal:
                sprint_data["goal"] = sprint.goal
            
            response = self._make_request('POST', f'../../rest/agile/1.0/sprint', json=sprint_data)
            
            if response.status_code == 201:
                created_sprint = response.json()
                return MCPResponse(success=True, data={
                    'id': created_sprint['id'],
                    'name': created_sprint['name'],
                    'state': created_sprint['state']
                })
            else:
                return MCPResponse(success=False, error=f"Failed to create sprint: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e)) 