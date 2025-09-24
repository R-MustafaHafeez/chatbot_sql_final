"""
Visualizer Agent - Creates JSON chart specifications from database results.
Generates visualization specs that frontend can render.
"""

from typing import Dict, Any, Optional, List
from openai import OpenAI
from ..core.models import ChatState, Command, ChartSpec
import logging
import json

logger = logging.getLogger(__name__)

# Visualizer Agent Prompt
VISUALIZER_PROMPT = """
You are a visualization generator.
Input: structured table data.
Output: chart specification JSON that frontend can render.

Analyze the data and choose the most appropriate chart type:
- bar: categorical data, comparisons
- line: time series, trends
- pie: proportions, percentages
- scatter: correlations, relationships
- area: cumulative data over time
- histogram: distribution analysis

Example:
{
  "type": "chart",
  "chart_type": "bar",
  "title": "Monthly Sales",
  "x": ["Jan", "Feb", "Mar"],
  "y": [100, 200, 300],
  "x_label": "Month",
  "y_label": "Sales ($)",
  "colors": ["#3498db", "#e74c3c", "#2ecc71"]
}

Supported chart types: bar, line, pie, scatter, area, histogram.
Do NOT generate explanations—only the JSON.
"""


class VisualizerAgent:
    """Agent for creating data visualizations from database results."""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.system_prompt = VISUALIZER_PROMPT
    
    def create_visualization(self, state: ChatState) -> Command:
        """Create visualization from database results."""
        try:
            # Check if we have data from database
            if not state.db_results:
                return Command(goto="summarizer", update={
                    "response_message": "I need data from the database to create a visualization. Please ask a data question first to fetch the information.",
                    "is_complete": True
                })
            
            # Generate chart specification
            chart_spec = self._generate_chart_spec(state.db_results, state.query)
            
            if not chart_spec:
                return Command(goto="summarizer", update={
                    "response_message": "I couldn't create a visualization from the data. Let me provide the information in a different format.",
                    "is_complete": True
                })
            
            # Update state with chart spec
            update = {"chart_spec": chart_spec.model_dump()}
            
            logger.info(f"Visualizer: Created {chart_spec.chart_type} chart")
            
            return Command(goto="summarizer", update=update)
            
        except Exception as e:
            logger.error(f"Visualizer error: {e}")
            return Command(goto="summarizer", update={
                "response_message": "I couldn't create a visualization. Let me provide the data in a different format.",
                "is_complete": True
            })
    
    def _generate_sample_chart(self, query: str) -> Dict[str, Any]:
        """Generate a sample chart structure based on the query."""
        query_lower = query.lower()
        
        # Determine chart type based on query
        if "pie" in query_lower or "distribution" in query_lower:
            chart_type = "pie"
            sample_data = {
                "type": "chart",
                "chart_type": "pie",
                "title": "Sample Distribution",
                "labels": ["Category A", "Category B", "Category C"],
                "values": [30, 45, 25],
                "colors": ["#3498db", "#e74c3c", "#2ecc71"]
            }
        elif "line" in query_lower or "trend" in query_lower or "time" in query_lower:
            chart_type = "line"
            sample_data = {
                "type": "chart",
                "chart_type": "line",
                "title": "Sample Trend",
                "x": ["Jan", "Feb", "Mar", "Apr", "May"],
                "y": [100, 120, 90, 150, 180],
                "x_label": "Time Period",
                "y_label": "Value"
            }
        elif "scatter" in query_lower or "correlation" in query_lower:
            chart_type = "scatter"
            sample_data = {
                "type": "chart",
                "chart_type": "scatter",
                "title": "Sample Correlation",
                "x": [1, 2, 3, 4, 5],
                "y": [2, 4, 6, 8, 10],
                "x_label": "Variable X",
                "y_label": "Variable Y"
            }
        else:  # Default to bar chart
            chart_type = "bar"
            sample_data = {
                "type": "chart",
                "chart_type": "bar",
                "title": "Sample Data",
                "x": ["Category 1", "Category 2", "Category 3"],
                "y": [100, 150, 120],
                "x_label": "Categories",
                "y_label": "Values",
                "colors": ["#3498db", "#e74c3c", "#2ecc71"]
            }
        
        return sample_data
    
    def _generate_chart_spec(self, db_results: Dict[str, Any], query: str) -> Optional[ChartSpec]:
        """Generate chart specification from database results."""
        try:
            headers = db_results.get("headers", [])
            rows = db_results.get("rows", [])
            
            if not headers or not rows:
                return None
            
            # Determine chart type based on data and query
            chart_type = self._determine_chart_type(headers, rows, query)
            
            # Extract x and y data
            x_data, y_data = self._extract_chart_data(headers, rows, chart_type)
            
            if not x_data or not y_data:
                return None
            
            # Generate chart label
            label = self._generate_chart_label(query, headers)
            
            # Create chart specification
            chart_spec = ChartSpec(
                chart_type=chart_type,
                x=x_data,
                y=y_data,
                label=label,
                x_label=headers[0] if headers else "X",
                y_label=headers[1] if len(headers) > 1 else "Y"
            )
            
            return chart_spec
            
        except Exception as e:
            logger.error(f"Chart spec generation error: {e}")
            return None
    
    def _determine_chart_type(self, headers: List[str], rows: List[List], query: str) -> str:
        """Determine the best chart type for the data."""
        try:
            query_lower = query.lower()
            
            # Check for explicit chart type requests
            if "bar chart" in query_lower or "bar" in query_lower:
                return "bar"
            elif "line chart" in query_lower or "line" in query_lower:
                return "line"
            elif "pie chart" in query_lower or "pie" in query_lower:
                return "pie"
            elif "scatter" in query_lower:
                return "scatter"
            
            # Analyze data to determine best chart type
            num_rows = len(rows)
            num_cols = len(headers)
            
            # For time series data
            if any("date" in h.lower() or "time" in h.lower() for h in headers):
                return "line"
            
            # For categorical data with few categories
            if num_rows <= 10 and num_cols >= 2:
                return "bar"
            
            # For many data points
            if num_rows > 20:
                return "line"
            
            # Default to bar chart
            return "bar"
            
        except Exception as e:
            logger.error(f"Error determining chart type: {e}")
            return "bar"
    
    def _extract_chart_data(self, headers: List[str], rows: List[List], chart_type: str) -> tuple:
        """Extract x and y data for the chart."""
        try:
            if not rows or len(rows[0]) < 2:
                return [], []
            
            # For most chart types, use first column as x, second as y
            x_data = [row[0] for row in rows]
            y_data = [row[1] for row in rows]
            
            # Handle different data types
            if chart_type == "pie":
                # For pie charts, use labels and values
                x_data = [str(row[0]) for row in rows]
                y_data = [float(row[1]) if isinstance(row[1], (int, float)) else 1 for row in rows]
            else:
                # For other charts, ensure y_data is numeric
                try:
                    y_data = [float(row[1]) if isinstance(row[1], (int, float)) else 0 for row in rows]
                except (ValueError, TypeError):
                    y_data = [0] * len(rows)
            
            return x_data, y_data
            
        except Exception as e:
            logger.error(f"Error extracting chart data: {e}")
            return [], []
    
    def _generate_chart_label(self, query: str, headers: List[str]) -> str:
        """Generate a descriptive label for the chart."""
        try:
            # Extract key terms from query
            query_words = query.split()
            key_terms = [word for word in query_words if len(word) > 3]
            
            # Create label from key terms
            if key_terms:
                label = " ".join(key_terms[:3]).title()
            else:
                label = "Data Visualization"
            
            # Add context from headers if available
            if headers:
                label += f" - {headers[0]} vs {headers[1] if len(headers) > 1 else 'Values'}"
            
            return label
            
        except Exception as e:
            logger.error(f"Error generating chart label: {e}")
            return "Data Visualization"
    
    def get_supported_chart_types(self) -> List[str]:
        """Get list of supported chart types."""
        return ["bar", "line", "pie", "scatter"]
    
    def validate_chart_data(self, data: Dict[str, Any]) -> bool:
        """Validate if data is suitable for visualization."""
        try:
            headers = data.get("headers", [])
            rows = data.get("rows", [])
            
            # Need at least 2 columns and some rows
            if len(headers) < 2 or len(rows) < 1:
                return False
            
            # Check if we have numeric data in the second column
            if rows:
                try:
                    float(rows[0][1])
                    return True
                except (ValueError, TypeError, IndexError):
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating chart data: {e}")
            return False
