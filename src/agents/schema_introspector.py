#!/usr/bin/env python3
"""
Database Schema Introspector based on LangGraph tutorial.
"""

import logging
from typing import Dict, Any, List, Optional
from ..core.database import DatabaseManager

logger = logging.getLogger(__name__)

class SchemaIntrospector:
    """Introspects database schema for better SQL generation."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def get_available_tables(self) -> List[str]:
        """Get list of available tables in the database."""
        try:
            # Query to get table names
            result = self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
                "admin"
            )
            
            if result and result.rows:
                tables = [row[0] for row in result.rows]
                logger.info(f"Available tables: {tables}")
                return tables
            else:
                logger.warning("No tables found in database")
                return []
                
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get detailed schema information for a table."""
        try:
            # Get column information
            schema_query = f"PRAGMA table_info({table_name})"
            result = self.db_manager.execute_query(schema_query, "admin")
            
            if not result or not result.rows:
                return {"table": table_name, "columns": [], "sample_data": []}
            
            columns = []
            for row in result.rows:
                columns.append({
                    "name": row[1],
                    "type": row[2],
                    "not_null": bool(row[3]),
                    "default_value": row[4],
                    "primary_key": bool(row[5])
                })
            
            # Get sample data
            sample_result = self.db_manager.execute_query(
                f"SELECT * FROM {table_name} LIMIT 3",
                "admin"
            )
            
            sample_data = []
            if sample_result and sample_result.rows:
                sample_data = sample_result.rows
            
            schema_info = {
                "table": table_name,
                "columns": columns,
                "sample_data": sample_data,
                "row_count": len(sample_data)
            }
            
            logger.info(f"Schema for {table_name}: {len(columns)} columns")
            return schema_info
            
        except Exception as e:
            logger.error(f"Error getting schema for {table_name}: {e}")
            return {"table": table_name, "columns": [], "sample_data": [], "error": str(e)}
    
    def get_relevant_tables(self, query: str) -> List[str]:
        """Determine which tables are relevant for a given query."""
        query_lower = query.lower()
        all_tables = self.get_available_tables()
        
        # Simple keyword matching for table relevance
        relevant_tables = []
        
        for table in all_tables:
            table_lower = table.lower()
            
            # Check if table name appears in query
            if table_lower in query_lower:
                relevant_tables.append(table)
                continue
            
            # Check for common patterns
            if table_lower == "users" and any(word in query_lower for word in ["user", "customer", "person", "people"]):
                relevant_tables.append(table)
            elif table_lower == "products" and any(word in query_lower for word in ["product", "item", "goods"]):
                relevant_tables.append(table)
            elif table_lower == "orders" and any(word in query_lower for word in ["order", "purchase", "sale", "transaction"]):
                relevant_tables.append(table)
        
        # If no specific tables found, return all tables for safety
        if not relevant_tables:
            relevant_tables = all_tables[:3]  # Limit to first 3 tables
        
        logger.info(f"Relevant tables for '{query}': {relevant_tables}")
        return relevant_tables
    
    def get_schema_context(self, query: str) -> str:
        """Get comprehensive schema context for SQL generation."""
        try:
            relevant_tables = self.get_relevant_tables(query)
            schema_context = "Available database schema:\n\n"
            
            for table in relevant_tables:
                schema_info = self.get_table_schema(table)
                
                schema_context += f"Table: {table}\n"
                schema_context += "Columns:\n"
                
                for col in schema_info.get("columns", []):
                    schema_context += f"  - {col['name']} ({col['type']})"
                    if col.get("primary_key"):
                        schema_context += " [PRIMARY KEY]"
                    if col.get("not_null"):
                        schema_context += " [NOT NULL]"
                    schema_context += "\n"
                
                # Add sample data
                sample_data = schema_info.get("sample_data", [])
                if sample_data:
                    schema_context += f"Sample data ({len(sample_data)} rows):\n"
                    for i, row in enumerate(sample_data[:2]):  # Show first 2 rows
                        schema_context += f"  Row {i+1}: {row}\n"
                
                schema_context += "\n"
            
            return schema_context
            
        except Exception as e:
            logger.error(f"Error generating schema context: {e}")
            return "Database schema information not available."
