import requests
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional
from .base import BaseMCPProvider, MCPResponse, WorkItem, Sprint
import json

class AzureDevOpsProvider(BaseMCPProvider):
    """Azure DevOps MCP Provider"""
    
    def __init__(self, organization: str, auth_token: str, config: Dict[str, Any] = None):
        self.organization = organization
        base_url = f"https://dev.azure.com/{organization}"
        super().__init__(base_url, auth_token, config)
        
        # Setup authentication
        self.auth_header = {
            'Authorization': f'Basic {base64.b64encode(f":{auth_token}".encode()).decode()}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to Azure DevOps API"""
        url = f"{self.base_url}/_apis/{endpoint}"
        kwargs.setdefault('headers', {}).update(self.auth_header)
        
        if 'api-version' not in kwargs.get('params', {}):
            kwargs.setdefault('params', {})['api-version'] = '7.0'
        
        response = requests.request(method, url, **kwargs)
        return response
    
    def test_connection(self) -> MCPResponse:
        """Test connection to Azure DevOps"""
        try:
            response = self._make_request('GET', 'projects')
            if response.status_code == 200:
                return MCPResponse(success=True, data={"message": "Connection successful"})
            else:
                return MCPResponse(success=False, error=f"Connection failed: {response.status_code}")
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_projects(self) -> MCPResponse:
        """Get list of Azure DevOps projects"""
        try:
            response = self._make_request('GET', 'projects')
            
            if response.status_code == 200:
                data = response.json()
                projects = []
                
                for project in data.get('value', []):
                    projects.append({
                        'id': project['id'],
                        'name': project['name'],
                        'description': project.get('description', ''),
                        'state': project['state'],
                        'url': project['url']
                    })
                
                return MCPResponse(success=True, data=projects)
            else:
                return MCPResponse(success=False, error=f"Failed to get projects: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_work_items(self, project_id: str, **filters) -> MCPResponse:
        """Get work items from Azure DevOps project"""
        try:
            # Build WIQL query based on filters
            wiql_query = f"SELECT [System.Id], [System.Title], [System.Description], [System.State], [System.AssignedTo], [System.Tags], [System.CreatedDate], [System.ChangedDate], [Microsoft.VSTS.Common.Priority], [Microsoft.VSTS.Scheduling.StoryPoints] FROM WorkItems WHERE [System.TeamProject] = '{project_id}'"
            
            if filters.get('state'):
                wiql_query += f" AND [System.State] = '{filters['state']}'"
            
            if filters.get('assigned_to'):
                wiql_query += f" AND [System.AssignedTo] = '{filters['assigned_to']}'"
            
            if filters.get('work_item_type'):
                wiql_query += f" AND [System.WorkItemType] = '{filters['work_item_type']}'"
            
            # Execute WIQL query
            wiql_response = self._make_request('POST', f'wit/wiql', 
                                             json={'query': wiql_query})
            
            if wiql_response.status_code != 200:
                return MCPResponse(success=False, error=f"WIQL query failed: {wiql_response.status_code}")
            
            wiql_data = wiql_response.json()
            work_item_ids = [item['id'] for item in wiql_data.get('workItems', [])]
            
            if not work_item_ids:
                return MCPResponse(success=True, data=[])
            
            # Get work item details
            ids_param = ','.join(map(str, work_item_ids))
            details_response = self._make_request('GET', f'wit/workitems', 
                                                params={'ids': ids_param, '$expand': 'fields'})
            
            if details_response.status_code != 200:
                return MCPResponse(success=False, error=f"Failed to get work item details: {details_response.status_code}")
            
            details_data = details_response.json()
            work_items = []
            
            for item in details_data.get('value', []):
                fields = item.get('fields', {})
                
                work_item = WorkItem(
                    id=str(item['id']),
                    title=fields.get('System.Title', ''),
                    description=fields.get('System.Description', ''),
                    status=fields.get('System.State', ''),
                    assignee=fields.get('System.AssignedTo', {}).get('displayName') if fields.get('System.AssignedTo') else None,
                    labels=fields.get('System.Tags', '').split(';') if fields.get('System.Tags') else [],
                    created_date=datetime.fromisoformat(fields.get('System.CreatedDate', '').replace('Z', '+00:00')) if fields.get('System.CreatedDate') else None,
                    updated_date=datetime.fromisoformat(fields.get('System.ChangedDate', '').replace('Z', '+00:00')) if fields.get('System.ChangedDate') else None,
                    priority=fields.get('Microsoft.VSTS.Common.Priority'),
                    story_points=fields.get('Microsoft.VSTS.Scheduling.StoryPoints'),
                    metadata={
                        'work_item_type': fields.get('System.WorkItemType'),
                        'url': item.get('url'),
                        'project': fields.get('System.TeamProject')
                    }
                )
                work_items.append(work_item)
            
            return MCPResponse(success=True, data=work_items)
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def create_work_item(self, project_id: str, work_item: WorkItem) -> MCPResponse:
        """Create a new work item in Azure DevOps"""
        try:
            # Default work item type if not specified
            work_item_type = work_item.metadata.get('work_item_type', 'User Story') if work_item.metadata else 'User Story'
            
            # Build the document for the PATCH request
            document = [
                {
                    "op": "add",
                    "path": "/fields/System.Title",
                    "value": work_item.title
                },
                {
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": work_item.description
                }
            ]
            
            if work_item.assignee:
                document.append({
                    "op": "add",
                    "path": "/fields/System.AssignedTo",
                    "value": work_item.assignee
                })
            
            if work_item.priority:
                document.append({
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Common.Priority",
                    "value": work_item.priority
                })
            
            if work_item.story_points:
                document.append({
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Scheduling.StoryPoints",
                    "value": work_item.story_points
                })
            
            if work_item.labels:
                document.append({
                    "op": "add",
                    "path": "/fields/System.Tags",
                    "value": ';'.join(work_item.labels)
                })
            
            headers = self.auth_header.copy()
            headers['Content-Type'] = 'application/json-patch+json'
            
            response = self._make_request('POST', f'wit/workitems/${work_item_type}',
                                        json=document, headers=headers)
            
            if response.status_code == 200:
                created_item = response.json()
                return MCPResponse(success=True, data={
                    'id': created_item['id'],
                    'url': created_item['url']
                })
            else:
                return MCPResponse(success=False, error=f"Failed to create work item: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def update_work_item(self, project_id: str, work_item_id: str, updates: Dict[str, Any]) -> MCPResponse:
        """Update an existing work item"""
        try:
            document = []
            
            field_mapping = {
                'title': '/fields/System.Title',
                'description': '/fields/System.Description',
                'status': '/fields/System.State',
                'assignee': '/fields/System.AssignedTo',
                'priority': '/fields/Microsoft.VSTS.Common.Priority',
                'story_points': '/fields/Microsoft.VSTS.Scheduling.StoryPoints',
                'labels': '/fields/System.Tags'
            }
            
            for key, value in updates.items():
                if key in field_mapping:
                    if key == 'labels' and isinstance(value, list):
                        value = ';'.join(value)
                    
                    document.append({
                        "op": "replace",
                        "path": field_mapping[key],
                        "value": value
                    })
            
            headers = self.auth_header.copy()
            headers['Content-Type'] = 'application/json-patch+json'
            
            response = self._make_request('PATCH', f'wit/workitems/{work_item_id}',
                                        json=document, headers=headers)
            
            if response.status_code == 200:
                updated_item = response.json()
                return MCPResponse(success=True, data={
                    'id': updated_item['id'],
                    'url': updated_item['url']
                })
            else:
                return MCPResponse(success=False, error=f"Failed to update work item: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_work_item_comments(self, project_id: str, work_item_id: str) -> MCPResponse:
        """Get comments for a work item"""
        try:
            response = self._make_request('GET', f'wit/workItems/{work_item_id}/comments')
            
            if response.status_code == 200:
                data = response.json()
                comments = []
                
                for comment in data.get('comments', []):
                    comments.append({
                        'id': comment['id'],
                        'text': comment['text'],
                        'createdBy': comment.get('createdBy', {}).get('displayName'),
                        'createdDate': comment.get('createdDate'),
                        'modifiedDate': comment.get('modifiedDate')
                    })
                
                return MCPResponse(success=True, data=comments)
            else:
                return MCPResponse(success=False, error=f"Failed to get comments: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_sprints(self, project_id: str) -> MCPResponse:
        """Get sprints for a project"""
        try:
            # First get teams for the project
            teams_response = self._make_request('GET', f'projects/{project_id}/teams')
            
            if teams_response.status_code != 200:
                return MCPResponse(success=False, error=f"Failed to get teams: {teams_response.status_code}")
            
            teams_data = teams_response.json()
            all_sprints = []
            
            # Get iterations for each team
            for team in teams_data.get('value', []):
                team_id = team['id']
                iterations_response = self._make_request('GET', f'work/teamsettings/iterations',
                                                       params={'$timeframe': 'current'})
                
                if iterations_response.status_code == 200:
                    iterations_data = iterations_response.json()
                    
                    for iteration in iterations_data.get('value', []):
                        sprint = Sprint(
                            id=iteration['id'],
                            name=iteration['name'],
                            state=iteration.get('attributes', {}).get('timeFrame', 'unknown'),
                            start_date=datetime.fromisoformat(iteration.get('attributes', {}).get('startDate', '').replace('Z', '+00:00')) if iteration.get('attributes', {}).get('startDate') else None,
                            end_date=datetime.fromisoformat(iteration.get('attributes', {}).get('finishDate', '').replace('Z', '+00:00')) if iteration.get('attributes', {}).get('finishDate') else None
                        )
                        all_sprints.append(sprint)
            
            return MCPResponse(success=True, data=all_sprints)
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_team_members(self, project_id: str) -> MCPResponse:
        """Get team members for a project"""
        try:
            response = self._make_request('GET', f'projects/{project_id}/teams')
            
            if response.status_code == 200:
                teams_data = response.json()
                all_members = []
                
                for team in teams_data.get('value', []):
                    team_id = team['id']
                    members_response = self._make_request('GET', f'projects/{project_id}/teams/{team_id}/members')
                    
                    if members_response.status_code == 200:
                        members_data = members_response.json()
                        
                        for member in members_data.get('value', []):
                            all_members.append({
                                'id': member['identity']['id'],
                                'displayName': member['identity']['displayName'],
                                'uniqueName': member['identity']['uniqueName'],
                                'team': team['name']
                            })
                
                return MCPResponse(success=True, data=all_members)
            else:
                return MCPResponse(success=False, error=f"Failed to get team members: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e)) 