#!/usr/bin/env python3
"""
Auto Schema Discovery - Automatically discovers database schema and generates dynamic queries.
"""

import logging
from typing import Dict, Any, List, Optional
from ..core.database import DatabaseManager

logger = logging.getLogger(__name__)

class AutoSchemaDiscovery:
    """Automatically discovers database schema and generates dynamic SQL queries."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._schema_cache = {}
        self._table_relationships = {}
    
    def discover_full_schema(self) -> Dict[str, Any]:
        """Discover complete database schema automatically."""
        try:
            logger.info("🔍 Auto-discovering database schema...")
            
            # Get all tables
            tables = self._get_all_tables()
            logger.info(f"📊 Found {len(tables)} tables: {tables}")
            
            schema_info = {
                "tables": {},
                "relationships": {},
                "summary": {}
            }
            
            # Analyze each table
            for table in tables:
                table_schema = self._analyze_table(table)
                schema_info["tables"][table] = table_schema
                
                # Find relationships
                relationships = self._find_relationships(table, tables)
                if relationships:
                    schema_info["relationships"][table] = relationships
            
            # Generate schema summary
            schema_info["summary"] = self._generate_schema_summary(schema_info)
            
            # Cache the schema
            self._schema_cache = schema_info
            
            logger.info("✅ Schema discovery completed successfully")
            return schema_info
            
        except Exception as e:
            logger.error(f"❌ Schema discovery failed: {e}")
            return {"error": str(e)}
    
    def _get_all_tables(self) -> List[str]:
        """Get all user tables from database."""
        try:
            result = self.db_manager.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
                "admin"
            )
            
            if result and result.rows:
                return [row[0] for row in result.rows]
            return []
            
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
    
    def _analyze_table(self, table_name: str) -> Dict[str, Any]:
        """Analyze a single table for schema information."""
        try:
            # Get column information
            columns_result = self.db_manager.execute_query(
                f"PRAGMA table_info({table_name})",
                "admin"
            )
            
            columns = []
            if columns_result and columns_result.rows:
                for row in columns_result.rows:
                    columns.append({
                        "name": row[1],
                        "type": row[2],
                        "not_null": bool(row[3]),
                        "default_value": row[4],
                        "primary_key": bool(row[5])
                    })
            
            # Get sample data
            sample_result = self.db_manager.execute_query(
                f"SELECT * FROM {table_name} LIMIT 5",
                "admin"
            )
            
            sample_data = []
            if sample_result and sample_result.rows:
                sample_data = sample_result.rows
            
            # Get row count
            count_result = self.db_manager.execute_query(
                f"SELECT COUNT(*) as count FROM {table_name}",
                "admin"
            )
            
            row_count = 0
            if count_result and count_result.rows:
                row_count = count_result.rows[0][0]
            
            # Analyze data types and patterns
            data_analysis = self._analyze_data_patterns(table_name, sample_data)
            
            return {
                "columns": columns,
                "sample_data": sample_data,
                "row_count": row_count,
                "data_analysis": data_analysis,
                "primary_keys": [col["name"] for col in columns if col["primary_key"]],
                "foreign_keys": self._detect_foreign_keys(table_name, columns)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing table {table_name}: {e}")
            return {"error": str(e)}
    
    def _analyze_data_patterns(self, table_name: str, sample_data: List) -> Dict[str, Any]:
        """Analyze data patterns in the table."""
        if not sample_data:
            return {"patterns": [], "suggestions": []}
        
        patterns = []
        suggestions = []
        
        # Analyze column patterns
        for i, row in enumerate(sample_data[:3]):  # Analyze first 3 rows
            for j, value in enumerate(row):
                if value is not None:
                    # Detect common patterns
                    if isinstance(value, str):
                        if "@" in str(value):
                            patterns.append(f"Column {j} contains email addresses")
                        elif len(str(value)) > 50:
                            patterns.append(f"Column {j} contains long text")
                        elif str(value).replace("-", "").replace(" ", "").isdigit():
                            patterns.append(f"Column {j} contains formatted numbers")
        
        # Generate query suggestions based on table name and data
        if "user" in table_name.lower():
            suggestions.extend([
                f"SELECT * FROM {table_name} WHERE city = 'New York'",
                f"SELECT COUNT(*) FROM {table_name}",
                f"SELECT city, COUNT(*) FROM {table_name} GROUP BY city"
            ])
        elif "product" in table_name.lower():
            suggestions.extend([
                f"SELECT * FROM {table_name} WHERE category = 'Electronics'",
                f"SELECT category, COUNT(*) FROM {table_name} GROUP BY category",
                f"SELECT * FROM {table_name} ORDER BY price DESC"
            ])
        elif "order" in table_name.lower():
            suggestions.extend([
                f"SELECT * FROM {table_name} WHERE status = 'completed'",
                f"SELECT user_id, SUM(total_amount) FROM {table_name} GROUP BY user_id",
                f"SELECT * FROM {table_name} ORDER BY order_date DESC"
            ])
        
        return {
            "patterns": list(set(patterns)),
            "suggestions": suggestions
        }
    
    def _detect_foreign_keys(self, table_name: str, columns: List[Dict]) -> List[Dict[str, str]]:
        """Detect potential foreign key relationships."""
        foreign_keys = []
        
        for col in columns:
            col_name = col["name"]
            # Common foreign key patterns
            if col_name.endswith("_id") and not col["primary_key"]:
                # Try to find the referenced table
                potential_table = col_name.replace("_id", "")
                if potential_table != table_name:
                    foreign_keys.append({
                        "column": col_name,
                        "referenced_table": potential_table,
                        "referenced_column": "id"
                    })
        
        return foreign_keys
    
    def _find_relationships(self, table_name: str, all_tables: List[str]) -> List[Dict[str, str]]:
        """Find relationships between tables."""
        relationships = []
        
        for other_table in all_tables:
            if other_table != table_name:
                # Check if there's a foreign key relationship
                if f"{table_name}_id" in [col["name"] for col in self._schema_cache.get("tables", {}).get(other_table, {}).get("columns", [])]:
                    relationships.append({
                        "type": "one_to_many",
                        "related_table": other_table,
                        "foreign_key": f"{table_name}_id"
                    })
        
        return relationships
    
    def _generate_schema_summary(self, schema_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive schema summary."""
        tables = schema_info.get("tables", {})
        
        summary = {
            "total_tables": len(tables),
            "total_columns": sum(len(table.get("columns", [])) for table in tables.values()),
            "total_rows": sum(table.get("row_count", 0) for table in tables.values()),
            "table_summary": {},
            "common_patterns": [],
            "query_suggestions": []
        }
        
        # Generate table summaries
        for table_name, table_info in tables.items():
            summary["table_summary"][table_name] = {
                "columns": len(table_info.get("columns", [])),
                "rows": table_info.get("row_count", 0),
                "primary_keys": len(table_info.get("primary_keys", [])),
                "foreign_keys": len(table_info.get("foreign_keys", []))
            }
        
        # Generate common patterns
        all_patterns = []
        for table_info in tables.values():
            patterns = table_info.get("data_analysis", {}).get("patterns", [])
            all_patterns.extend(patterns)
        
        summary["common_patterns"] = list(set(all_patterns))
        
        # Generate query suggestions
        all_suggestions = []
        for table_info in tables.values():
            suggestions = table_info.get("data_analysis", {}).get("suggestions", [])
            all_suggestions.extend(suggestions)
        
        summary["query_suggestions"] = all_suggestions[:10]  # Top 10 suggestions
        
        return summary
    
    def get_dynamic_schema_context(self, query: str) -> str:
        """Get dynamic schema context based on query and discovered schema."""
        try:
            if not self._schema_cache:
                self.discover_full_schema()
            
            # Find relevant tables for the query
            relevant_tables = self._find_relevant_tables_for_query(query)
            
            context = "🔍 **Dynamic Database Schema Discovery**\n\n"
            context += f"**Query Analysis**: '{query}'\n"
            context += f"**Relevant Tables**: {', '.join(relevant_tables)}\n\n"
            
            # Add schema information for relevant tables
            for table in relevant_tables:
                if table in self._schema_cache.get("tables", {}):
                    table_info = self._schema_cache["tables"][table]
                    
                    context += f"**Table: {table}**\n"
                    context += f"Rows: {table_info.get('row_count', 0)}\n"
                    context += "Columns:\n"
                    
                    for col in table_info.get("columns", []):
                        context += f"  - {col['name']} ({col['type']})"
                        if col.get("primary_key"):
                            context += " [PRIMARY KEY]"
                        if col.get("not_null"):
                            context += " [NOT NULL]"
                        context += "\n"
                    
                    # Add sample data
                    sample_data = table_info.get("sample_data", [])
                    if sample_data:
                        context += f"Sample data ({len(sample_data)} rows):\n"
                        for i, row in enumerate(sample_data[:2]):
                            context += f"  Row {i+1}: {row}\n"
                    
                    context += "\n"
            
            # Add relationship information
            relationships = self._schema_cache.get("relationships", {})
            if relationships:
                context += "**Table Relationships**:\n"
                for table, rels in relationships.items():
                    if rels:
                        context += f"- {table}: {', '.join([r['related_table'] for r in rels])}\n"
                context += "\n"
            
            # Add query suggestions
            suggestions = self._schema_cache.get("summary", {}).get("query_suggestions", [])
            if suggestions:
                context += "**Suggested Queries**:\n"
                for suggestion in suggestions[:5]:
                    context += f"- {suggestion}\n"
                context += "\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Error generating dynamic schema context: {e}")
            return "Schema context not available."
    
    def _find_relevant_tables_for_query(self, query: str) -> List[str]:
        """Find tables relevant to the query using intelligent matching."""
        query_lower = query.lower()
        all_tables = list(self._schema_cache.get("tables", {}).keys())
        
        relevant_tables = []
        
        # Direct table name matching
        for table in all_tables:
            if table.lower() in query_lower:
                relevant_tables.append(table)
        
        # Keyword-based matching
        keyword_mappings = {
            "user": ["users", "customers", "people"],
            "product": ["products", "items", "goods"],
            "order": ["orders", "purchases", "transactions"],
            "sale": ["orders", "transactions"],
            "customer": ["users", "customers"],
            "revenue": ["orders", "transactions"],
            "spending": ["orders", "transactions"]
        }
        
        for keyword, table_names in keyword_mappings.items():
            if keyword in query_lower:
                for table_name in table_names:
                    if table_name in all_tables and table_name not in relevant_tables:
                        relevant_tables.append(table_name)
        
        # If no specific tables found, return all tables
        if not relevant_tables:
            relevant_tables = all_tables[:3]  # Limit to first 3 tables
        
        return relevant_tables
