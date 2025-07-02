import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from .base import BaseRepositoryProvider, MCPResponse, Repository, PullRequest
import json

class GitHubProvider(BaseRepositoryProvider):
    """GitHub Repository MCP Provider"""
    
    def __init__(self, auth_token: str, config: Dict[str, Any] = None):
        super().__init__("https://api.github.com", auth_token, config)
        
        # Setup authentication
        self.auth_header = {
            'Authorization': f'token {auth_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated request to GitHub API"""
        url = f"{self.base_url}/{endpoint}"
        kwargs.setdefault('headers', {}).update(self.auth_header)
        
        response = requests.request(method, url, **kwargs)
        return response
    
    def test_connection(self) -> MCPResponse:
        """Test connection to GitHub"""
        try:
            response = self._make_request('GET', 'user')
            if response.status_code == 200:
                user_data = response.json()
                return MCPResponse(success=True, data={
                    "message": "Connection successful",
                    "user": user_data.get('login')
                })
            else:
                return MCPResponse(success=False, error=f"Connection failed: {response.status_code}")
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_repositories(self, org: str = None) -> MCPResponse:
        """Get list of repositories"""
        try:
            if org:
                endpoint = f'orgs/{org}/repos'
            else:
                endpoint = 'user/repos'
            
            response = self._make_request('GET', endpoint, params={'per_page': 100})
            
            if response.status_code == 200:
                repos_data = response.json()
                repositories = []
                
                for repo in repos_data:
                    repository = Repository(
                        id=str(repo['id']),
                        name=repo['name'],
                        full_name=repo['full_name'],
                        url=repo['html_url'],
                        default_branch=repo['default_branch'],
                        language=repo.get('language'),
                        stars=repo['stargazers_count'],
                        forks=repo['forks_count'],
                        issues_count=repo['open_issues_count'],
                        pull_requests_count=0  # GitHub API doesn't provide this directly
                    )
                    repositories.append(repository)
                
                return MCPResponse(success=True, data=repositories)
            else:
                return MCPResponse(success=False, error=f"Failed to get repositories: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_repository(self, repo_name: str, org: str = None) -> MCPResponse:
        """Get repository details"""
        try:
            if org:
                endpoint = f'repos/{org}/{repo_name}'
            else:
                # Get authenticated user's repo
                user_response = self._make_request('GET', 'user')
                if user_response.status_code == 200:
                    username = user_response.json()['login']
                    endpoint = f'repos/{username}/{repo_name}'
                else:
                    return MCPResponse(success=False, error="Failed to get user info")
            
            response = self._make_request('GET', endpoint)
            
            if response.status_code == 200:
                repo = response.json()
                repository = Repository(
                    id=str(repo['id']),
                    name=repo['name'],
                    full_name=repo['full_name'],
                    url=repo['html_url'],
                    default_branch=repo['default_branch'],
                    language=repo.get('language'),
                    stars=repo['stargazers_count'],
                    forks=repo['forks_count'],
                    issues_count=repo['open_issues_count'],
                    pull_requests_count=0
                )
                
                return MCPResponse(success=True, data=repository)
            else:
                return MCPResponse(success=False, error=f"Failed to get repository: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_pull_requests(self, repo_name: str, org: str = None, state: str = "open") -> MCPResponse:
        """Get pull requests"""
        try:
            if org:
                endpoint = f'repos/{org}/{repo_name}/pulls'
            else:
                user_response = self._make_request('GET', 'user')
                if user_response.status_code == 200:
                    username = user_response.json()['login']
                    endpoint = f'repos/{username}/{repo_name}/pulls'
                else:
                    return MCPResponse(success=False, error="Failed to get user info")
            
            response = self._make_request('GET', endpoint, params={'state': state, 'per_page': 100})
            
            if response.status_code == 200:
                prs_data = response.json()
                pull_requests = []
                
                for pr in prs_data:
                    pull_request = PullRequest(
                        id=str(pr['id']),
                        title=pr['title'],
                        description=pr.get('body', ''),
                        status=pr['state'],
                        source_branch=pr['head']['ref'],
                        target_branch=pr['base']['ref'],
                        author=pr['user']['login'],
                        created_date=datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00')),
                        updated_date=datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00')),
                        url=pr['html_url']
                    )
                    pull_requests.append(pull_request)
                
                return MCPResponse(success=True, data=pull_requests)
            else:
                return MCPResponse(success=False, error=f"Failed to get pull requests: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_issues(self, repo_name: str, org: str = None, state: str = "open") -> MCPResponse:
        """Get repository issues"""
        try:
            if org:
                endpoint = f'repos/{org}/{repo_name}/issues'
            else:
                user_response = self._make_request('GET', 'user')
                if user_response.status_code == 200:
                    username = user_response.json()['login']
                    endpoint = f'repos/{username}/{repo_name}/issues'
                else:
                    return MCPResponse(success=False, error="Failed to get user info")
            
            response = self._make_request('GET', endpoint, params={'state': state, 'per_page': 100})
            
            if response.status_code == 200:
                issues_data = response.json()
                issues = []
                
                for issue in issues_data:
                    # Skip pull requests (they appear as issues in GitHub API)
                    if 'pull_request' in issue:
                        continue
                    
                    issues.append({
                        'id': str(issue['id']),
                        'number': issue['number'],
                        'title': issue['title'],
                        'description': issue.get('body', ''),
                        'state': issue['state'],
                        'assignee': issue['assignee']['login'] if issue['assignee'] else None,
                        'labels': [label['name'] for label in issue['labels']],
                        'created_at': issue['created_at'],
                        'updated_at': issue['updated_at'],
                        'url': issue['html_url']
                    })
                
                return MCPResponse(success=True, data=issues)
            else:
                return MCPResponse(success=False, error=f"Failed to get issues: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_commits(self, repo_name: str, org: str = None, branch: str = None) -> MCPResponse:
        """Get repository commits"""
        try:
            if org:
                endpoint = f'repos/{org}/{repo_name}/commits'
            else:
                user_response = self._make_request('GET', 'user')
                if user_response.status_code == 200:
                    username = user_response.json()['login']
                    endpoint = f'repos/{username}/{repo_name}/commits'
                else:
                    return MCPResponse(success=False, error="Failed to get user info")
            
            params = {'per_page': 100}
            if branch:
                params['sha'] = branch
            
            response = self._make_request('GET', endpoint, params=params)
            
            if response.status_code == 200:
                commits_data = response.json()
                commits = []
                
                for commit in commits_data:
                    commits.append({
                        'sha': commit['sha'],
                        'message': commit['commit']['message'],
                        'author': commit['commit']['author']['name'],
                        'author_email': commit['commit']['author']['email'],
                        'date': commit['commit']['author']['date'],
                        'url': commit['html_url']
                    })
                
                return MCPResponse(success=True, data=commits)
            else:
                return MCPResponse(success=False, error=f"Failed to get commits: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_branches(self, repo_name: str, org: str = None) -> MCPResponse:
        """Get repository branches"""
        try:
            if org:
                endpoint = f'repos/{org}/{repo_name}/branches'
            else:
                user_response = self._make_request('GET', 'user')
                if user_response.status_code == 200:
                    username = user_response.json()['login']
                    endpoint = f'repos/{username}/{repo_name}/branches'
                else:
                    return MCPResponse(success=False, error="Failed to get user info")
            
            response = self._make_request('GET', endpoint, params={'per_page': 100})
            
            if response.status_code == 200:
                branches_data = response.json()
                branches = []
                
                for branch in branches_data:
                    branches.append({
                        'name': branch['name'],
                        'sha': branch['commit']['sha'],
                        'protected': branch.get('protected', False),
                        'url': branch['commit']['url']
                    })
                
                return MCPResponse(success=True, data=branches)
            else:
                return MCPResponse(success=False, error=f"Failed to get branches: {response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e))
    
    def get_repository_stats(self, repo_name: str, org: str = None) -> MCPResponse:
        """Get repository statistics"""
        try:
            if org:
                repo_endpoint = f'repos/{org}/{repo_name}'
                contributors_endpoint = f'repos/{org}/{repo_name}/contributors'
            else:
                user_response = self._make_request('GET', 'user')
                if user_response.status_code == 200:
                    username = user_response.json()['login']
                    repo_endpoint = f'repos/{username}/{repo_name}'
                    contributors_endpoint = f'repos/{username}/{repo_name}/contributors'
                else:
                    return MCPResponse(success=False, error="Failed to get user info")
            
            # Get basic repo info
            repo_response = self._make_request('GET', repo_endpoint)
            contributors_response = self._make_request('GET', contributors_endpoint)
            
            if repo_response.status_code == 200:
                repo_data = repo_response.json()
                stats = {
                    'name': repo_data['name'],
                    'stars': repo_data['stargazers_count'],
                    'forks': repo_data['forks_count'],
                    'open_issues': repo_data['open_issues_count'],
                    'size': repo_data['size'],
                    'language': repo_data.get('language'),
                    'created_at': repo_data['created_at'],
                    'updated_at': repo_data['updated_at']
                }
                
                if contributors_response.status_code == 200:
                    contributors_data = contributors_response.json()
                    stats['contributors_count'] = len(contributors_data)
                    stats['top_contributors'] = [
                        {
                            'login': contributor['login'],
                            'contributions': contributor['contributions']
                        }
                        for contributor in contributors_data[:5]
                    ]
                
                return MCPResponse(success=True, data=stats)
            else:
                return MCPResponse(success=False, error=f"Failed to get repository stats: {repo_response.status_code}")
        
        except Exception as e:
            return MCPResponse(success=False, error=str(e)) 