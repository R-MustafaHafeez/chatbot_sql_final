"""
Database Agent 1 - Handles simple database queries.
Translates natural language to SQL and executes with RBAC checks.
"""

from typing import Dict, Any, Optional, List
from openai import OpenAI
from ..core.models import ChatState, Command, DatabaseResult
from ..utils.rbac import rbac_manager
from ..core.database import DatabaseManager
from .sql_validator import SQLValidator
from .schema_introspector import SchemaIntrospector
import logging
import json

logger = logging.getLogger(__name__)

# Database Agent 1 Prompt
DB_AGENT_PROMPT = """
You are a SQL query assistant for Database 1.
Your task is to:
1. Translate user request into a safe, read-only SQL query.
2. Respect RBAC rules → only query allowed tables/columns.
3. Handle simple queries: SELECT, WHERE, ORDER BY, LIMIT.
4. For complex queries (JOINs, aggregations), suggest using "complex query" mode.
5. Return the result in structured JSON:

{
  "type": "table",
  "headers": ["col1", "col2", ...],
  "rows": [["val1", "val2"], ...]
}

⚠️ Never expose the raw SQL query or internal errors to the user.
⚠️ If query is too complex, suggest breaking it down or using advanced query mode.
"""


class DatabaseAgent1:
    """Database agent for simple queries with RBAC enforcement."""
    
    def __init__(self, openai_client: OpenAI, db_manager: DatabaseManager):
        self.client = openai_client
        self.db_manager = db_manager
        self.system_prompt = DB_AGENT_PROMPT
        self.sql_validator = SQLValidator(openai_client)
        self.schema_introspector = SchemaIntrospector(db_manager)
    
    def process_query(self, state: ChatState) -> Command:
        """Process database query with RBAC checks."""
        try:
            query = state.query
            role = state.role
            
            # Generate SQL query
            sql_query = self._generate_sql(query, role)
            
            # Validate SQL query for common mistakes
            validation_result = self.sql_validator.validate_query(sql_query)
            if not validation_result["validation_passed"]:
                logger.warning(f"SQL validation failed: {validation_result.get('error', 'Unknown error')}")
                sql_query = validation_result["corrected_query"]
            
            # Validate RBAC access
            is_allowed, reason = rbac_manager.validate_query_access(role, sql_query)
            if not is_allowed:
                logger.warning(f"RBAC violation for user {state.user_id}: {reason}")
                return Command(goto="unauthorized", update={
                    "response_message": "Sorry, you don't have permission to access that information.",
                    "is_complete": True
                })
            
            # Execute query
            result = self.db_manager.execute_query(sql_query, role)
            
            if result is None:
                return Command(goto="summarizer", update={
                    "response_message": "I couldn't retrieve the data you requested. Please try rephrasing your question.",
                    "is_complete": True
                })
            
            # Update state with results
            update = {
                "db_results": result.model_dump(),
                "sql_query": sql_query  # Store for debugging, not exposed to user
            }
            
            # Check if visualization is needed
            if state.context and state.context.get("needs_visualization", False):
                return Command(goto="visualizer", update=update)
            else:
                return Command(goto="summarizer", update=update)
            
        except Exception as e:
            logger.error(f"Database Agent 1 error: {e}")
            return Command(goto="summarizer", update={
                "response_message": "I encountered an error processing your request. Please try again.",
                "is_complete": True
            })
    
    def _generate_sql(self, query: str, role: str) -> str:
        """Generate SQL query from natural language with schema introspection."""
        try:
            # Get schema context for better SQL generation
            schema_context = self.schema_introspector.get_schema_context(query)
            
            # Get role-specific context for SQL generation
            role_context = self._get_role_context(role)
            
            prompt = f"""
            Generate SQL query for: {query}
            
            {schema_context}
            
            Role context: {role_context}
            
            Examples:
            - "Show me all users" → SELECT * FROM users
            - "Users from New York" → SELECT * FROM users WHERE city = 'New York'
            - "List all products" → SELECT * FROM products
            
            Return ONLY the SQL query. No explanations.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            sql = response.choices[0].message.content.strip()
            
            # Clean up the SQL
            sql = self._clean_sql(sql)
            
            logger.info(f"Generated SQL for role {role}: {sql}")
            return sql
            
        except Exception as e:
            logger.error(f"SQL generation error: {e}")
            # Fallback to pattern-based generation
            query_lower = query.lower()
            
            if "show me all users" in query_lower or "list all users" in query_lower:
                return "SELECT * FROM users"
            elif "show me all products" in query_lower or "list all products" in query_lower:
                return "SELECT * FROM products"
            elif "show me all orders" in query_lower or "list all orders" in query_lower:
                return "SELECT * FROM orders"
            elif "users from" in query_lower:
                # Extract city from query
                if "new york" in query_lower:
                    return "SELECT * FROM users WHERE city = 'New York'"
                elif "los angeles" in query_lower:
                    return "SELECT * FROM users WHERE city = 'Los Angeles'"
                elif "chicago" in query_lower:
                    return "SELECT * FROM users WHERE city = 'Chicago'"
                elif "boston" in query_lower:
                    return "SELECT * FROM users WHERE city = 'Boston'"
                elif "seattle" in query_lower:
                    return "SELECT * FROM users WHERE city = 'Seattle'"
                else:
                    return "SELECT * FROM users"
            else:
                return "SELECT * FROM users LIMIT 10"
    
    def _get_role_context(self, role: str) -> str:
        """Get role-specific context for SQL generation."""
        try:
            role_info = rbac_manager.get_role_info(role)
            if not role_info:
                return "No specific restrictions"
            
            context_parts = []
            context_parts.append(f"Permissions: {', '.join(role_info['permissions'])}")
            
            if role_info['allowed_tables'] != "all":
                context_parts.append(f"Allowed tables: {', '.join(role_info['allowed_tables'])}")
            
            if role_info['column_restrictions']:
                context_parts.append(f"Column restrictions: {role_info['column_restrictions']}")
            
            return "; ".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting role context: {e}")
            return "No specific restrictions"
    
    def _clean_sql(self, sql: str) -> str:
        """Clean and validate SQL query."""
        import re
        
        # Remove code blocks
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)
        
        # Ensure it starts with SELECT
        sql = sql.strip()
        if not sql.upper().startswith('SELECT'):
            sql = f"SELECT {sql}"
        
        return sql
    
    def get_available_tables(self, role: str) -> List[str]:
        """Get tables available to the role."""
        try:
            return self.db_manager.get_available_tables(role) or []
        except Exception as e:
            logger.error(f"Error getting available tables: {e}")
            return []
    
    def get_table_schema(self, table_name: str, role: str) -> Optional[Dict[str, Any]]:
        """Get table schema for the role."""
        try:
            return self.db_manager.get_table_schema(table_name, role)
        except Exception as e:
            logger.error(f"Error getting table schema: {e}")
            return None
