"""
Database connection and RBAC enforcement for the Conversational SQL Chatbot.
Handles database connections, query execution, and role-based access control.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from .models import DatabaseResult, DatabaseConfig, RBACConfig
from .database_factory import DatabaseConnectionFactory, DatabaseType
import pandas as pd

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and query execution with RBAC."""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.session_factory = None
        self.rbac_config = RBACConfig()
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            # Use SQLite for easy testing with hardcoded credentials
            connection_string = f"sqlite:///{self.config.database}"
            
            self.engine = create_engine(connection_string, echo=False)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info(f"Database connection established successfully: {connection_string}")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def is_authorized(self, role: str, operation: str) -> bool:
        """Check if user role is authorized for the operation."""
        role_permissions = {
            "analyst": ["SELECT"],
            "admin": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            "readonly": ["SELECT"],
            "viewer": ["SELECT"]
        }
        
        user_permissions = role_permissions.get(role, ["SELECT"])
        return operation.upper() in user_permissions
    
    def execute_query(self, sql: str, role: str) -> Optional[DatabaseResult]:
        """Execute SQL query with RBAC enforcement."""
        try:
            # Check authorization
            if not self.is_authorized(role, "SELECT"):
                logger.warning(f"Unauthorized access attempt by role: {role}")
                return None
            
            # Validate SQL (basic safety checks)
            if not self._is_safe_query(sql):
                logger.warning(f"Unsafe query detected: {sql}")
                return None
            
            # Execute query
            with self.engine.connect() as connection:
                result = connection.execute(text(sql))
                
                # Convert to structured format
                if result.returns_rows:
                    rows = result.fetchall()
                    headers = list(result.keys()) if rows else []
                    
                    # Convert rows to list of lists
                    row_data = [list(row) for row in rows]
                    
                    return DatabaseResult(
                        headers=headers,
                        rows=row_data,
                        row_count=len(row_data)
                    )
                else:
                    # For non-SELECT queries (though we only allow SELECT)
                    return DatabaseResult(
                        headers=["result"],
                        rows=[["Query executed successfully"]],
                        row_count=1
                    )
                    
        except SQLAlchemyError as e:
            logger.error(f"Database query error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            return None
    
    def _is_safe_query(self, sql: str) -> bool:
        """Basic SQL safety validation."""
        sql_upper = sql.upper().strip()
        
        # Only allow SELECT statements
        if not sql_upper.startswith("SELECT"):
            return False
        
        # Block dangerous operations
        dangerous_keywords = [
            "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", 
            "TRUNCATE", "EXEC", "EXECUTE", "UNION", "INFORMATION_SCHEMA"
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        
        return True
    
    def get_table_schema(self, table_name: str, role: str) -> Optional[Dict[str, Any]]:
        """Get table schema information (if authorized)."""
        try:
            if not self.is_authorized(role, "SELECT"):
                return None
            
            # Query to get column information
            schema_query = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
            """
            
            result = self.execute_query(schema_query, role)
            if result:
                return {
                    "table_name": table_name,
                    "columns": [
                        {
                            "name": row[0],
                            "type": row[1], 
                            "nullable": row[2] == "YES"
                        }
                        for row in result.rows
                    ]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Schema query error: {e}")
            return None
    
    def get_available_tables(self, role: str) -> Optional[List[str]]:
        """Get list of available tables (if authorized)."""
        try:
            if not self.is_authorized(role, "SELECT"):
                return None
            
            tables_query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
            
            result = self.execute_query(tables_query, role)
            if result:
                return [row[0] for row in result.rows]
            
            return None
            
        except Exception as e:
            logger.error(f"Tables query error: {e}")
            return None


class MockDatabaseManager:
    """Mock database manager for development and testing."""
    
    def __init__(self):
        self.rbac_config = RBACConfig()
        logger.info("Using mock database manager")
    
    def is_authorized(self, role: str, operation: str) -> bool:
        """Mock authorization check."""
        role_permissions = {
            "analyst": ["SELECT"],
            "admin": ["SELECT", "INSERT", "UPDATE", "DELETE"],
            "readonly": ["SELECT"],
            "viewer": ["SELECT"]
        }
        
        user_permissions = role_permissions.get(role, ["SELECT"])
        return operation.upper() in user_permissions
    
    def execute_query(self, sql: str, role: str) -> Optional[DatabaseResult]:
        """Mock query execution with sample data."""
        try:
            if not self.is_authorized(role, "SELECT"):
                logger.warning(f"Unauthorized access attempt by role: {role}")
                return None
            
            # Return mock data based on query content
            sql_lower = sql.lower()
            
            if "user" in sql_lower:
                return DatabaseResult(
                    headers=["id", "name", "email", "created_at"],
                    rows=[
                        [1, "John Doe", "john@example.com", "2024-01-15"],
                        [2, "Jane Smith", "jane@example.com", "2024-01-16"],
                        [3, "Bob Johnson", "bob@example.com", "2024-01-17"]
                    ],
                    row_count=3
                )
            elif "order" in sql_lower or "sale" in sql_lower:
                return DatabaseResult(
                    headers=["order_id", "customer_id", "amount", "date"],
                    rows=[
                        [1001, 1, 150.00, "2024-01-15"],
                        [1002, 2, 75.50, "2024-01-16"],
                        [1003, 1, 200.00, "2024-01-17"]
                    ],
                    row_count=3
                )
            elif "count" in sql_lower:
                return DatabaseResult(
                    headers=["count"],
                    rows=[[42]],
                    row_count=1
                )
            else:
                return DatabaseResult(
                    headers=["id", "value"],
                    rows=[[1, "Sample Data"], [2, "Test Data"]],
                    row_count=2
                )
                
        except Exception as e:
            logger.error(f"Mock query execution error: {e}")
            return None
    
    def get_table_schema(self, table_name: str, role: str) -> Optional[Dict[str, Any]]:
        """Mock schema information."""
        if not self.is_authorized(role, "SELECT"):
            return None
        
        mock_schemas = {
            "users": {
                "table_name": "users",
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False},
                    {"name": "name", "type": "varchar", "nullable": False},
                    {"name": "email", "type": "varchar", "nullable": False},
                    {"name": "created_at", "type": "timestamp", "nullable": True}
                ]
            },
            "orders": {
                "table_name": "orders", 
                "columns": [
                    {"name": "order_id", "type": "integer", "nullable": False},
                    {"name": "customer_id", "type": "integer", "nullable": False},
                    {"name": "amount", "type": "decimal", "nullable": False},
                    {"name": "date", "type": "timestamp", "nullable": False}
                ]
            }
        }
        
        return mock_schemas.get(table_name)
    
    def get_available_tables(self, role: str) -> Optional[List[str]]:
        """Mock available tables."""
        if not self.is_authorized(role, "SELECT"):
            return None
        
        return ["users", "orders", "products", "categories"]


def create_database_manager(config: Optional[DatabaseConfig] = None) -> DatabaseManager:
    """Create database manager instance."""
    if config:
        return DatabaseManager(config)
    else:
        # Return mock manager for development
        return MockDatabaseManager()
