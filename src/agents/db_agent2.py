"""
Database Agent 2 - Handles complex database queries with joins and aggregations.
Advanced SQL generation with RBAC enforcement.
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

# Database Agent 2 Prompt
DB_AGENT_2_PROMPT = """
You are an advanced SQL query assistant for Database 2.
Your task is to:
1. Translate complex user requests into safe, read-only SQL queries with JOINs, aggregations, subqueries.
2. Respect RBAC rules → only query allowed tables/columns.
3. Handle complex business logic and multi-table operations.
4. Optimize queries for performance and readability.
5. Use proper SQL best practices: appropriate JOINs, indexing hints, query optimization.
6. Return the result in structured JSON:

{
  "type": "table",
  "headers": ["col1", "col2", ...],
  "rows": [["val1", "val2"], ...]
}

⚠️ Never expose the raw SQL query or internal errors to the user.
⚠️ Use descriptive column aliases for better readability.
⚠️ Handle NULL values appropriately in aggregations.
"""


class DatabaseAgent2:
    """Database agent for complex queries with advanced RBAC enforcement."""
    
    def __init__(self, openai_client: OpenAI, db_manager: DatabaseManager):
        self.client = openai_client
        self.db_manager = db_manager
        self.system_prompt = DB_AGENT_2_PROMPT
        self.sql_validator = SQLValidator(openai_client)
        self.schema_introspector = SchemaIntrospector(db_manager)
    
    def process_query(self, state: ChatState) -> Command:
        """Process complex database query with RBAC checks."""
        try:
            query = state.query
            role = state.role
            
            # Check if this is a visualization request
            is_visualization_request = self._is_visualization_request(query)
            
            # Generate complex SQL query
            sql_query = self._generate_complex_sql(query, role)
            
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
                    "response_message": "I couldn't retrieve the complex data you requested. Please try rephrasing your question.",
                    "is_complete": True
                })
            
            # Update state with results
            update = {
                "db_results": result.model_dump(),
                "sql_query": sql_query  # Store for debugging, not exposed to user
            }
            
            # Check if visualization is needed
            if (state.context and state.context.get("needs_visualization", False)) or is_visualization_request:
                logger.info("Database Agent 2: Routing to visualizer for chart generation")
                return Command(goto="visualizer", update=update)
            else:
                logger.info("Database Agent 2: Routing to summarizer")
                return Command(goto="summarizer", update=update)
            
        except Exception as e:
            logger.error(f"Database Agent 2 error: {e}")
            return Command(goto="summarizer", update={
                "response_message": "I encountered an error processing your complex request. Please try again.",
                "is_complete": True
            })
    
    def _generate_complex_sql(self, query: str, role: str) -> str:
        """Generate complex SQL query from natural language."""
        try:
            # Get role-specific context for SQL generation
            role_context = self._get_role_context(role)
            
            prompt = f"""
            You are a SQL query generator. Generate ONLY the SQL query for: {query}
            
            Tables:
            - users (id, name, email, age, city, created_at)
            - products (id, name, price, category, stock_quantity)  
            - orders (id, user_id, product_id, quantity, total_amount, order_date, status)
            
            For "orders with user names": SELECT u.id, u.name, u.email, o.id as order_id, o.user_id, o.product_id, o.quantity, o.total_amount, o.order_date, o.status FROM users u JOIN orders o ON u.id = o.user_id
            
            For "top customers by spending": SELECT u.id, u.name, u.email, SUM(o.total_amount) as total_spent FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name, u.email ORDER BY total_spent DESC
            
            Return ONLY the SQL query. No explanations.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            sql = response.choices[0].message.content.strip()
            
            # Clean up the SQL
            sql = self._clean_sql(sql)
            
            logger.info(f"Generated complex SQL for role {role}: {sql}")
            return sql
            
        except Exception as e:
            logger.error(f"Complex SQL generation error: {e}")
            # Fallback to pattern-based generation
            query_lower = query.lower()
            
            if "orders with user names" in query_lower:
                return "SELECT u.id, u.name, u.email, o.id as order_id, o.user_id, o.product_id, o.quantity, o.total_amount, o.order_date, o.status FROM users u JOIN orders o ON u.id = o.user_id"
            elif "total revenue by city" in query_lower:
                return "SELECT u.city, SUM(o.total_amount) as total_revenue FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.city"
            elif "top" in query_lower and "customers" in query_lower:
                return "SELECT u.id, u.name, u.email, SUM(o.total_amount) as total_spent FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name, u.email ORDER BY total_spent DESC"
            elif "sales by product category" in query_lower:
                return "SELECT p.category, SUM(o.total_amount) as total_sales FROM products p JOIN orders o ON p.id = o.product_id GROUP BY p.category"
            else:
                return "SELECT u.id, u.name, u.email, o.id as order_id, o.user_id, o.product_id, o.quantity, o.total_amount, o.order_date, o.status FROM users u JOIN orders o ON u.id = o.user_id"
    
    def _get_role_context(self, role: str) -> str:
        """Get role-specific context for complex SQL generation."""
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
        """Clean and validate complex SQL query."""
        import re
        
        # Remove code blocks
        sql = re.sub(r'```sql\n?', '', sql)
        sql = re.sub(r'```\n?', '', sql)
        
        # Ensure it starts with SELECT
        sql = sql.strip()
        if not sql.upper().startswith('SELECT'):
            sql = f"SELECT {sql}"
        
        return sql
    
    def is_complex_query(self, query: str) -> bool:
        """Check if query requires complex SQL processing."""
        complex_patterns = [
            "join", "aggregate", "group by", "having", "subquery", "union",
            "multiple tables", "complex", "advanced", "detailed analysis",
            "compare", "correlation", "trend", "pattern", "relationship"
        ]
        
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in complex_patterns)
    
    def get_query_complexity_score(self, query: str) -> float:
        """Get complexity score for query (0.0 to 1.0)."""
        try:
            complexity_indicators = [
                "join", "aggregate", "group by", "having", "subquery", "union",
                "multiple", "complex", "advanced", "detailed", "compare",
                "correlation", "trend", "pattern", "relationship", "analysis"
            ]
            
            query_lower = query.lower()
            matches = sum(1 for indicator in complexity_indicators if indicator in query_lower)
            
            # Normalize to 0.0-1.0 scale
            max_indicators = len(complexity_indicators)
            return min(matches / max_indicators, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating complexity score: {e}")
            return 0.5  # Default medium complexity
    
    def _is_visualization_request(self, query: str) -> bool:
        """Check if query is a visualization request."""
        visualization_keywords = [
            "chart", "graph", "plot", "visualize", "show me a", "display",
            "bar chart", "pie chart", "line chart", "scatter plot",
            "create a chart", "generate a graph", "draw a plot"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in visualization_keywords)
