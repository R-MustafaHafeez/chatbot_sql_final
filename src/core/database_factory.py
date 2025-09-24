#!/usr/bin/env python3
"""
Database Factory Pattern for multiple database support.
"""

import os
from enum import Enum
from typing import Optional
from .config import DatabaseConfig

class DatabaseType(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"

class DatabaseFactory:
    """Factory class for creating database configurations."""
    
    @staticmethod
    def create_config(db_type: DatabaseType, **kwargs) -> DatabaseConfig:
        """Create database configuration based on type."""
        
        if db_type == DatabaseType.SQLITE:
            return DatabaseConfig(
                host="localhost",
                port=0,
                database=kwargs.get("database", "chatbot.db"),
                username="",
                password="",
                schema=None
            )
        
        elif db_type == DatabaseType.POSTGRESQL:
            return DatabaseConfig(
                host=kwargs.get("host", os.getenv("DB_HOST", "localhost")),
                port=int(kwargs.get("port", os.getenv("DB_PORT", "5432"))),
                database=kwargs.get("database", os.getenv("DB_NAME", "chatbot_db")),
                username=kwargs.get("username", os.getenv("DB_USER", "postgres")),
                password=kwargs.get("password", os.getenv("DB_PASSWORD", "")),
                schema=kwargs.get("schema", os.getenv("DB_SCHEMA"))
            )
        
        elif db_type == DatabaseType.MYSQL:
            return DatabaseConfig(
                host=kwargs.get("host", os.getenv("DB_HOST", "localhost")),
                port=int(kwargs.get("port", os.getenv("DB_PORT", "3306"))),
                database=kwargs.get("database", os.getenv("DB_NAME", "chatbot_db")),
                username=kwargs.get("username", os.getenv("DB_USER", "root")),
                password=kwargs.get("password", os.getenv("DB_PASSWORD", "")),
                schema=kwargs.get("schema", os.getenv("DB_SCHEMA"))
            )
        
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

class DatabaseConnectionFactory:
    """Factory for creating database connection strings."""
    
    @staticmethod
    def create_connection_string(config: DatabaseConfig, db_type: DatabaseType) -> str:
        """Create connection string based on database type."""
        
        if db_type == DatabaseType.SQLITE:
            return f"sqlite:///{config.database}"
        
        elif db_type == DatabaseType.POSTGRESQL:
            if config.password:
                return f"postgresql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
            else:
                return f"postgresql://{config.username}@{config.host}:{config.port}/{config.database}"
        
        elif db_type == DatabaseType.MYSQL:
            if config.password:
                return f"mysql+pymysql://{config.username}:{config.password}@{config.host}:{config.port}/{config.database}"
            else:
                return f"mysql+pymysql://{config.username}@{config.host}:{config.port}/{config.database}"
        
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

# Default configuration for easy testing
def get_default_sqlite_config() -> DatabaseConfig:
    """Get default SQLite configuration for testing."""
    return DatabaseFactory.create_config(
        DatabaseType.SQLITE,
        database="chatbot.db"
    )

def get_default_postgresql_config() -> DatabaseConfig:
    """Get default PostgreSQL configuration."""
    return DatabaseFactory.create_config(
        DatabaseType.POSTGRESQL,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "chatbot_db"),
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        schema=os.getenv("DB_SCHEMA")
    )

def get_default_mysql_config() -> DatabaseConfig:
    """Get default MySQL configuration."""
    return DatabaseFactory.create_config(
        DatabaseType.MYSQL,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "chatbot_db"),
        username=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        schema=os.getenv("DB_SCHEMA")
    )
