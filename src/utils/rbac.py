"""
Role-Based Access Control (RBAC) utilities.
Handles permission checks and role validation.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Available permissions in the system."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


class Role(Enum):
    """Available user roles."""
    VIEWER = "viewer"
    READONLY = "readonly"
    ANALYST = "analyst"
    ADMIN = "admin"


class RBACManager:
    """Manages role-based access control."""
    
    def __init__(self):
        # Define role-permission mappings
        self.role_permissions: Dict[Role, Set[Permission]] = {
            Role.VIEWER: {Permission.READ},
            Role.READONLY: {Permission.READ},
            Role.ANALYST: {Permission.READ},
            Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN}
        }
        
        # Define table access by role
        self.table_permissions: Dict[Role, Set[str]] = {
            Role.VIEWER: {"users", "orders"},  # Limited tables
            Role.READONLY: {"users", "orders", "products", "categories"},
            Role.ANALYST: {"users", "orders", "products", "categories", "sales", "analytics"},
            Role.ADMIN: set()  # All tables (empty set means all)
        }
        
        # Define column restrictions by role
        self.column_restrictions: Dict[Role, Dict[str, Set[str]]] = {
            Role.VIEWER: {
                "users": {"id", "name", "email"},  # No sensitive data
                "orders": {"id", "amount", "date"}
            },
            Role.READONLY: {},  # No restrictions
            Role.ANALYST: {},  # No restrictions
            Role.ADMIN: {}  # No restrictions
        }
    
    def has_permission(self, role: str, permission: Permission) -> bool:
        """Check if role has specific permission."""
        try:
            role_enum = Role(role.lower())
            return permission in self.role_permissions.get(role_enum, set())
        except ValueError:
            logger.warning(f"Invalid role: {role}")
            return False
    
    def can_access_table(self, role: str, table_name: str) -> bool:
        """Check if role can access specific table."""
        try:
            role_enum = Role(role.lower())
            allowed_tables = self.table_permissions.get(role_enum, set())
            
            # Admin can access all tables
            if role_enum == Role.ADMIN:
                return True
            
            # Check if table is in allowed list
            return table_name.lower() in allowed_tables
            
        except ValueError:
            logger.warning(f"Invalid role: {role}")
            return False
    
    def can_access_column(self, role: str, table_name: str, column_name: str) -> bool:
        """Check if role can access specific column."""
        try:
            role_enum = Role(role.lower())
            restrictions = self.column_restrictions.get(role_enum, {})
            
            # If no restrictions for this role, allow all columns
            if not restrictions:
                return True
            
            # Check table-specific restrictions
            table_restrictions = restrictions.get(table_name.lower(), set())
            if not table_restrictions:
                return True
            
            # Check if column is allowed
            return column_name.lower() in table_restrictions
            
        except ValueError:
            logger.warning(f"Invalid role: {role}")
            return False
    
    def validate_query_access(self, role: str, sql_query: str) -> Tuple[bool, str]:
        """
        Validate if role can execute SQL query.
        Returns (is_allowed, reason).
        """
        try:
            role_enum = Role(role.lower())
            sql_upper = sql_query.upper().strip()
            
            # Extract table names from SQL (basic parsing)
            tables = self._extract_tables_from_sql(sql_query)
            
            # Check table access
            for table in tables:
                if not self.can_access_table(role, table):
                    return False, f"Access denied to table '{table}' for role '{role}'"
            
            # Check for dangerous operations
            if not self._is_safe_query(sql_query, role_enum):
                return False, "Query contains unauthorized operations"
            
            return True, "Access granted"
            
        except ValueError:
            return False, f"Invalid role: {role}"
        except Exception as e:
            logger.error(f"Error validating query access: {e}")
            return False, "Error validating access"
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query (basic implementation)."""
        import re
        
        # Simple regex to find table names after FROM and JOIN
        from_pattern = r'FROM\s+(\w+)'
        join_pattern = r'JOIN\s+(\w+)'
        
        tables = []
        tables.extend(re.findall(from_pattern, sql, re.IGNORECASE))
        tables.extend(re.findall(join_pattern, sql, re.IGNORECASE))
        
        return [table.lower() for table in tables]
    
    def _is_safe_query(self, sql: str, role: Role) -> bool:
        """Check if SQL query is safe for the role."""
        sql_upper = sql.upper().strip()
        
        # Only allow SELECT for non-admin roles
        if role != Role.ADMIN and not sql_upper.startswith("SELECT"):
            return False
        
        # Block dangerous operations for non-admin
        if role != Role.ADMIN:
            dangerous_keywords = [
                "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
                "TRUNCATE", "EXEC", "EXECUTE", "UNION", "INFORMATION_SCHEMA"
            ]
            
            for keyword in dangerous_keywords:
                if keyword in sql_upper:
                    return False
        
        return True
    
    def get_role_info(self, role: str) -> Optional[Dict[str, Any]]:
        """Get information about a role."""
        try:
            role_enum = Role(role.lower())
            permissions = self.role_permissions.get(role_enum, set())
            tables = self.table_permissions.get(role_enum, set())
            
            return {
                "role": role_enum.value,
                "permissions": [p.value for p in permissions],
                "allowed_tables": list(tables) if tables else "all",
                "column_restrictions": self.column_restrictions.get(role_enum, {})
            }
        except ValueError:
            return None
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """Get information about all available roles."""
        return [self.get_role_info(role.value) for role in Role if self.get_role_info(role.value)]


# Global RBAC manager instance
rbac_manager = RBACManager()
