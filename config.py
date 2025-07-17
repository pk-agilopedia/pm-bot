import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-for-dev'   
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-string'
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    
    # AI LLM Providers
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY')
    AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    
    # Default LLM Provider
    DEFAULT_LLM_PROVIDER = os.environ.get('DEFAULT_LLM_PROVIDER', 'openai')
    
    # Third-party integrations
    AZURE_DEVOPS_PAT = os.environ.get('AZURE_DEVOPS_PAT')
    
    # JIRA Configuration
    JIRA_API_TOKEN = os.environ.get('JIRA_API_TOKEN')
    JIRA_SERVER_URL = os.environ.get('JIRA_SERVER_URL')
    JIRA_EMAIL = os.environ.get('JIRA_EMAIL')
    JIRA_PROJECT_KEY = os.environ.get('JIRA_PROJECT_KEY')
    
    # GitHub Configuration
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
    GITHUB_REPO_NAME = os.environ.get('GITHUB_REPO_NAME')
    GITHUB_REPO_OWNER = os.environ.get('GITHUB_REPO_OWNER')
    GITHUB_BASE_URL = os.environ.get('GITHUB_BASE_URL', 'https://api.github.com')
    
    # Slack and Teams
    SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
    TEAMS_WEBHOOK_URL = os.environ.get('TEAMS_WEBHOOK_URL')


    
    # Application settings
    ENVIRONMENT = os.environ.get('ENVIRONMENT', 'development')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # Cost tracking
    COST_TRACKING_ENABLED = os.environ.get('COST_TRACKING_ENABLED', 'True').lower() == 'true'

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        f"mysql+pymysql://{os.environ.get('DB_USER', 'root')}:" \
        f"{os.environ.get('DB_PASSWORD', 'password')}@" \
        f"{os.environ.get('DB_HOST', 'localhost')}:" \
        f"{os.environ.get('DB_PORT', '3306')}/" \
        f"{os.environ.get('DB_NAME', 'pmbot_dev')}"

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    BOT_APP_ID = os.environ.get('BOT_APP_ID')
    BOT_APP_PASSWORD = os.environ.get('BOT_APP_PASSWORD')
    

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 