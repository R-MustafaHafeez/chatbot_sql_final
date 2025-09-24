"""
Configuration management for the Conversational SQL Chatbot.
Handles environment variables and application settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from .models import DatabaseConfig

# Load environment variables
load_dotenv()


class AppConfig:
    """Application configuration class."""
    
    def __init__(self):
        # OpenAI Configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            print("Warning: OPENAI_API_KEY not found. Using mock mode for testing.")
            self.openai_api_key = "mock_key_for_testing"
        
        # Database Configuration
        self.database_config = self._get_database_config()
        
        # Application Settings
        self.app_host = os.getenv("APP_HOST", "0.0.0.0")
        self.app_port = int(os.getenv("APP_PORT", "8000"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Security
        self.secret_key = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")
    
    def _get_database_config(self) -> Optional[DatabaseConfig]:
        """Get database configuration from environment variables."""
        # Use SQLite for easy testing with hardcoded credentials
        return DatabaseConfig(
            host="localhost",
            port=0,
            database="chatbot.db",
            username="",
            password="",
            schema=None
        )
    
    def is_database_configured(self) -> bool:
        """Check if database is properly configured."""
        return self.database_config is not None
    
    def get_database_url(self) -> Optional[str]:
        """Get database connection URL."""
        if not self.database_config:
            return None
        
        return (
            f"postgresql://{self.database_config.username}:{self.database_config.password}"
            f"@{self.database_config.host}:{self.database_config.port}/{self.database_config.database}"
        )


# Global configuration instance
config = AppConfig()
