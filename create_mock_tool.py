#!/usr/bin/env python3
"""
Create a mock tool for testing project analysis
"""
import os
import sys

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Project, Tool, ProjectTool, ToolType

def create_mock_tool():
    """Create a mock tool for testing"""
    app = create_app()
    
    with app.app_context():
        print("Creating mock tool for testing...")
        
        # Get the existing Sample Project
        project = Project.query.filter_by(name="Sample Project").first()
        if not project:
            print("Sample Project not found. Please run init_db.py first.")
            return
        
        # Check if mock tool already exists
        existing_tool = Tool.query.filter_by(
            tenant_id=project.tenant_id,
            name="Mock JIRA (Testing)"
        ).first()
        
        if existing_tool:
            print("Mock tool already exists!")
            return
        
        # Create a mock tool
        mock_tool = Tool(
            tenant_id=project.tenant_id,
            name="Mock JIRA (Testing)",
            tool_type=ToolType.JIRA,
            base_url="https://mock-jira.example.com",
            api_token="mock_token_123",
            configuration={
                "is_mock": True,
                "project_key": "SAMPLE"
            },
            is_active=True
        )
        
        db.session.add(mock_tool)
        db.session.commit()
        
        # Link the tool to the project
        project_tool = ProjectTool(
            project_id=project.id,
            tool_id=mock_tool.id,
            configuration={
                "project_key": "SAMPLE",
                "is_mock": True
            },
            is_active=True
        )
        
        db.session.add(project_tool)
        db.session.commit()
        
        print("✅ Mock tool created successfully!")
        print(f"   • Tool: {mock_tool.name}")
        print(f"   • Type: {mock_tool.tool_type.value}")
        print(f"   • Linked to project: {project.name}")
        print("\n🚀 Now create the mock MCP provider and try the analysis again!")

if __name__ == "__main__":
    create_mock_tool() 