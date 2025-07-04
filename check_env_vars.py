#!/usr/bin/env python3
"""
Check if environment variables are properly loaded
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_vars():
    """Check if all required environment variables are present"""
    required_vars = [
        'JIRA_SERVER_URL',
        'JIRA_EMAIL', 
        'JIRA_API_TOKEN',
        'JIRA_PROJECT_KEY',
        'GITHUB_TOKEN',
        'GITHUB_REPO_OWNER',
        'GITHUB_REPO_NAME',
        'GITHUB_BASE_URL'
    ]
    
    print("🔍 Checking environment variables...")
    
    missing = []
    present = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            present.append(f"✅ {var}: {value[:10]}{'...' if len(value) > 10 else ''}")
        else:
            missing.append(f"❌ {var}: Not found")
    
    print("\n📋 Environment Variables Status:")
    for item in present:
        print(item)
    
    if missing:
        print("\n⚠️  Missing Variables:")
        for item in missing:
            print(item)
        return False
    else:
        print("\n🎉 All environment variables are present!")
        return True

if __name__ == "__main__":
    check_env_vars() 