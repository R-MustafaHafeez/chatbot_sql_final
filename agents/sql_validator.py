#!/usr/bin/env python3
"""
SQL Query Validator based on LangGraph tutorial best practices.
"""

import logging
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class SQLValidator:
    """Validates SQL queries for common mistakes before execution."""
    
    def __init__(self, client: OpenAI):
        self.client = client
    
    def validate_query(self, sql_query: str, dialect: str = "sqlite") -> Dict[str, Any]:
        """
        Validate SQL query for common mistakes.
        Returns validation result with corrected query if needed.
        """
        try:
            system_prompt = f"""
            You are a SQL expert with a strong attention to detail.
            Double check the {dialect} query for common mistakes, including:
            - Using NOT IN with NULL values
            - Using UNION when UNION ALL should have been used
            - Using BETWEEN for exclusive ranges
            - Data type mismatch in predicates
            - Properly quoting identifiers
            - Using the correct number of arguments for functions
            - Casting to the correct data type
            - Using the proper columns for joins
            - Missing WHERE clauses that could cause performance issues
            - Using SELECT * when specific columns are needed

            If there are any of the above mistakes, rewrite the query. If there are no mistakes,
            just reproduce the original query.

            Return ONLY the corrected SQL query, nothing else.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Validate this SQL query: {sql_query}"}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            corrected_query = response.choices[0].message.content.strip()
            
            # Clean up the query
            corrected_query = self._clean_sql(corrected_query)
            
            is_valid = corrected_query.upper().strip() == sql_query.upper().strip()
            
            logger.info(f"SQL Validation - Original: {sql_query}")
            logger.info(f"SQL Validation - Corrected: {corrected_query}")
            logger.info(f"SQL Validation - Valid: {is_valid}")
            
            return {
                "is_valid": is_valid,
                "original_query": sql_query,
                "corrected_query": corrected_query,
                "validation_passed": True
            }
            
        except Exception as e:
            logger.error(f"SQL validation error: {e}")
            return {
                "is_valid": False,
                "original_query": sql_query,
                "corrected_query": sql_query,
                "validation_passed": False,
                "error": str(e)
            }
    
    def _clean_sql(self, sql: str) -> str:
        """Clean up SQL query."""
        # Remove any markdown formatting
        sql = sql.replace("```sql", "").replace("```", "")
        # Remove extra whitespace
        sql = " ".join(sql.split())
        return sql.strip()
