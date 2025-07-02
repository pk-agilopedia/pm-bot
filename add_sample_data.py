#!/usr/bin/env python3
"""
Add sample project data for testing the PM Bot API
"""
import os
import sys
from datetime import datetime, timedelta

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Project, WorkItem, Sprint, TeamMember

def add_sample_data():
    """Add sample data to the database"""
    app = create_app()
    
    with app.app_context():
        print("Adding sample project data...")
        
        # Get the existing Sample Project
        project = Project.query.filter_by(name="Sample Project").first()
        if not project:
            print("Sample Project not found. Please run init_db.py first.")
            return
        
        # Add team members
        team_members = [
            TeamMember(
                project_id=project.id,
                name="John Doe",
                email="john@demo.com",
                role="Developer",
                is_active=True
            ),
            TeamMember(
                project_id=project.id,
                name="Jane Smith",
                email="jane@demo.com",
                role="Product Owner",
                is_active=True
            ),
            TeamMember(
                project_id=project.id,
                name="Mike Johnson",
                email="mike@demo.com",
                role="Scrum Master",
                is_active=True
            ),
            TeamMember(
                project_id=project.id,
                name="Sarah Wilson",
                email="sarah@demo.com",
                role="QA Engineer",
                is_active=True
            )
        ]
        
        for member in team_members:
            existing = TeamMember.query.filter_by(
                project_id=project.id, 
                email=member.email
            ).first()
            if not existing:
                db.session.add(member)
                print(f"Added team member: {member.name}")
        
        # Add sprints
        today = datetime.utcnow()
        
        # Previous sprint (completed)
        prev_sprint = Sprint(
            project_id=project.id,
            name="Sprint 1",
            goal="Setup project foundation and basic features",
            start_date=today - timedelta(days=21),
            end_date=today - timedelta(days=7),
            status="completed",
            is_active=False
        )
        
        # Current sprint (active)
        current_sprint = Sprint(
            project_id=project.id,
            name="Sprint 2",
            goal="Implement core functionality and user management",
            start_date=today - timedelta(days=7),
            end_date=today + timedelta(days=7),
            status="active",
            is_active=True
        )
        
        # Future sprint (planned)
        future_sprint = Sprint(
            project_id=project.id,
            name="Sprint 3",
            goal="Add reporting and analytics features",
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=21),
            status="planned",
            is_active=False
        )
        
        sprints = [prev_sprint, current_sprint, future_sprint]
        for sprint in sprints:
            existing = Sprint.query.filter_by(
                project_id=project.id,
                name=sprint.name
            ).first()
            if not existing:
                db.session.add(sprint)
                print(f"Added sprint: {sprint.name}")
        
        db.session.commit()
        
        # Get sprint IDs for work items
        sprint1 = Sprint.query.filter_by(project_id=project.id, name="Sprint 1").first()
        sprint2 = Sprint.query.filter_by(project_id=project.id, name="Sprint 2").first()
        sprint3 = Sprint.query.filter_by(project_id=project.id, name="Sprint 3").first()
        
        # Add work items
        work_items = [
            # Sprint 1 items (completed)
            WorkItem(
                project_id=project.id,
                sprint_id=sprint1.id if sprint1 else None,
                title="Setup project repository",
                description="Initialize git repository and project structure",
                status="done",
                priority="high",
                story_points=3,
                work_item_type="story",
                created_date=today - timedelta(days=20),
                updated_date=today - timedelta(days=8)
            ),
            WorkItem(
                project_id=project.id,
                sprint_id=sprint1.id if sprint1 else None,
                title="Configure development environment",
                description="Setup Docker, dependencies, and development tools",
                status="done",
                priority="high",
                story_points=5,
                work_item_type="story",
                created_date=today - timedelta(days=19),
                updated_date=today - timedelta(days=8)
            ),
            WorkItem(
                project_id=project.id,
                sprint_id=sprint1.id if sprint1 else None,
                title="Create basic API structure",
                description="Setup Flask app with basic routes and authentication",
                status="done",
                priority="medium",
                story_points=8,
                work_item_type="story",
                created_date=today - timedelta(days=18),
                updated_date=today - timedelta(days=9)
            ),
            
            # Sprint 2 items (current)
            WorkItem(
                project_id=project.id,
                sprint_id=sprint2.id if sprint2 else None,
                title="Implement user management",
                description="Create user registration, login, and profile management",
                status="in_progress",
                priority="high",
                story_points=13,
                work_item_type="story",
                created_date=today - timedelta(days=10),
                updated_date=today - timedelta(days=1)
            ),
            WorkItem(
                project_id=project.id,
                sprint_id=sprint2.id if sprint2 else None,
                title="Add project management features",
                description="Create project CRUD operations and team management",
                status="in_progress",
                priority="medium",
                story_points=8,
                work_item_type="story",
                created_date=today - timedelta(days=9),
                updated_date=today
            ),
            WorkItem(
                project_id=project.id,
                sprint_id=sprint2.id if sprint2 else None,
                title="Fix authentication bug",
                description="Token expiration not working correctly",
                status="to_do",
                priority="high",
                story_points=2,
                work_item_type="bug",
                created_date=today - timedelta(days=3),
                updated_date=today - timedelta(days=3)
            ),
            WorkItem(
                project_id=project.id,
                sprint_id=sprint2.id if sprint2 else None,
                title="Write API documentation",
                description="Document all API endpoints with examples",
                status="to_do",
                priority="low",
                story_points=5,
                work_item_type="task",
                created_date=today - timedelta(days=2),
                updated_date=today - timedelta(days=2)
            ),
            
            # Sprint 3 items (planned)
            WorkItem(
                project_id=project.id,
                sprint_id=sprint3.id if sprint3 else None,
                title="Create analytics dashboard",
                description="Build reporting interface for project metrics",
                status="to_do",
                priority="medium",
                story_points=13,
                work_item_type="story",
                created_date=today - timedelta(days=1),
                updated_date=today - timedelta(days=1)
            ),
            WorkItem(
                project_id=project.id,
                sprint_id=sprint3.id if sprint3 else None,
                title="Add email notifications",
                description="Send notifications for important events",
                status="to_do",
                priority="low",
                story_points=8,
                work_item_type="story",
                created_date=today,
                updated_date=today
            ),
            
            # Backlog items (no sprint assigned)
            WorkItem(
                project_id=project.id,
                sprint_id=None,
                title="Implement mobile app",
                description="Create mobile application for iOS and Android",
                status="to_do",
                priority="low",
                story_points=21,
                work_item_type="epic",
                created_date=today,
                updated_date=today
            )
        ]
        
        for item in work_items:
            existing = WorkItem.query.filter_by(
                project_id=project.id,
                title=item.title
            ).first()
            if not existing:
                db.session.add(item)
                print(f"Added work item: {item.title}")
        
        db.session.commit()
        print("\n✅ Sample data added successfully!")
        
        # Print summary
        total_items = WorkItem.query.filter_by(project_id=project.id).count()
        total_sprints = Sprint.query.filter_by(project_id=project.id).count()
        total_members = TeamMember.query.filter_by(project_id=project.id).count()
        
        print(f"\n📊 Summary:")
        print(f"   • Team Members: {total_members}")
        print(f"   • Sprints: {total_sprints}")
        print(f"   • Work Items: {total_items}")
        print(f"\n🚀 Now try the messages endpoint again!")

if __name__ == "__main__":
    add_sample_data() 