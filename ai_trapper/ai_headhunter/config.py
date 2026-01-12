"""
Configuration settings for the AI Headhunter system
"""

import os
from typing import Dict, List


class Config:
    """
    Base configuration class with default settings
    """
    
    # Application settings
    APP_NAME = "AI Headhunter"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Data source settings
    DEFAULT_DATA_SOURCE = "local_file"
    SUPPORTED_DATA_SOURCES = ["local_file", "api", "database"]
    
    # Matching algorithm settings
    REQUIRED_SKILLS_WEIGHT = 0.5
    PREFERRED_SKILLS_WEIGHT = 0.3
    EXPERIENCE_WEIGHT = 0.2
    LOCATION_BONUS = 0.1
    
    # API settings
    API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
    API_RETRY_COUNT = int(os.getenv('API_RETRY_COUNT', '3'))
    
    # Database settings
    DB_PATH = os.getenv('DB_PATH', './data/candidates.db')
    DB_CONNECTION_POOL_SIZE = int(os.getenv('DB_CONNECTION_POOL_SIZE', '10'))
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/ai_headhunter.log')
    
    # External service settings
    LINKEDIN_API_KEY = os.getenv('LINKEDIN_API_KEY', '')
    GITHUB_API_KEY = os.getenv('GITHUB_API_KEY', '')
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY', '')
    
    # NLP processing settings
    NLP_MODEL_NAME = os.getenv('NLP_MODEL_NAME', 'en_core_web_sm')
    SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.7'))
    
    # Job search settings
    MAX_CANDIDATES_PER_JOB = int(os.getenv('MAX_CANDIDATES_PER_JOB', '100'))
    DEFAULT_SEARCH_RADIUS = int(os.getenv('DEFAULT_SEARCH_RADIUS', '50'))  # in miles
    
    # Notification settings
    EMAIL_NOTIFICATIONS_ENABLED = os.getenv('EMAIL_NOTIFICATIONS_ENABLED', 'True').lower() == 'true'
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    EMAIL_FROM = os.getenv('EMAIL_FROM', 'noreply@aiheadhunter.com')
    
    # Rate limiting
    API_RATE_LIMIT = int(os.getenv('API_RATE_LIMIT', '100'))  # requests per minute
    CONCURRENT_REQUESTS_LIMIT = int(os.getenv('CONCURRENT_REQUESTS_LIMIT', '5'))
    
    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate the configuration and return a list of errors if any
        """
        errors = []
        
        if not cls.LINKEDIN_API_KEY and not cls.GITHUB_API_KEY:
            errors.append("At least one social media API key should be configured")
        
        if cls.SIMILARITY_THRESHOLD < 0 or cls.SIMILARITY_THRESHOLD > 1:
            errors.append("SIMILARITY_THRESHOLD must be between 0 and 1")
        
        if cls.API_TIMEOUT <= 0:
            errors.append("API_TIMEOUT must be greater than 0")
        
        if cls.API_RETRY_COUNT <= 0:
            errors.append("API_RETRY_COUNT must be greater than 0")
        
        return errors


class DevelopmentConfig(Config):
    """
    Development environment configuration
    """
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """
    Production environment configuration
    """
    DEBUG = False
    LOG_LEVEL = 'WARNING'


class TestingConfig(Config):
    """
    Testing environment configuration
    """
    DEBUG = True
    TESTING = True
    LOG_LEVEL = 'ERROR'


# Configuration dictionary
config: Dict[str, Config] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}