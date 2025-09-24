"""
Router Agent - Lightweight LLM (gpt-4o-mini) for intent classification.
Analyzes user queries and routes to appropriate agents.
"""

from typing import Dict, Any, Optional
from openai import OpenAI
from models import ChatState, Command
import logging

logger = logging.getLogger(__name__)

# Router Agent Prompt
ROUTER_PROMPT = """
You are a query classifier. Analyze the user query and decide its intent.

Valid categories:
- "chitchat" → casual talk, greetings, jokes, general conversation.
- "db1" → simple data queries (SELECT, WHERE, basic filters).
- "db2" → complex queries (JOINs, aggregations, subqueries, GROUP BY, HAVING).
- "visualize" → user asks for charts, graphs, plots, visualizations, "create a chart", "show me a chart", "bar chart", "pie chart", "line chart".
- "unauthorized" → user is asking for data they may not have access to.

Complex query indicators: JOIN, aggregate, group by, having, subquery, complex filtering.
Visualization indicators: chart, graph, plot, visualize, show me, display, bar chart, pie chart, line chart, scatter plot, create a chart, generate a graph.

IMPORTANT: If the query contains visualization keywords, classify as "visualize" even if it also mentions data.

Return ONLY one label.
"""


class RouterAgent:
    """Router agent that classifies user intent and routes to appropriate agents."""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.system_prompt = ROUTER_PROMPT
    
    def classify_intent(self, state: ChatState) -> Command:
        """Classify user intent and return routing command."""
        try:
            # Get user query
            query = state.query
            
            # Use lightweight model for classification
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"User query: {query}"}
                ],
                max_tokens=20,
                temperature=0.1
            )
            
            intent = response.choices[0].message.content.strip().lower()
            
            # Validate and route
            routing_map = {
                "chitchat": "chitchat",
                "db1": "db_agent_1", 
                "db2": "db_agent_2",
                "visualize": "db_agent_2",  # First get data, then visualize
                "unauthorized": "unauthorized"
            }
            
            # Default to chitchat for unknown intents
            next_agent = routing_map.get(intent, "chitchat")
            
            # Special handling for visualization requests
            update = {}
            if intent == "visualize":
                update["needs_visualization"] = True
            
            logger.info(f"Router: Classified '{query}' as '{intent}' → routing to '{next_agent}'")
            
            return Command(goto=next_agent, update=update)
            
        except Exception as e:
            logger.error(f"Router classification error: {e}")
            # Safe fallback to chitchat
            return Command(goto="chitchat")
    
    def get_intent_confidence(self, query: str) -> Dict[str, float]:
        """Get confidence scores for different intents (for debugging)."""
        try:
            intents = ["chitchat", "db1", "db2", "visualize", "unauthorized"]
            confidence_scores = {}
            
            for intent in intents:
                prompt = f"{self.system_prompt}\n\nClassify this query as '{intent}': {query}"
                
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Rate confidence from 0.0 to 1.0"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=10,
                    temperature=0.1
                )
                
                try:
                    confidence = float(response.choices[0].message.content.strip())
                    confidence_scores[intent] = confidence
                except ValueError:
                    confidence_scores[intent] = 0.0
            
            return confidence_scores
            
        except Exception as e:
            logger.error(f"Error getting intent confidence: {e}")
            return {"chitchat": 1.0}
    
    def _is_visualization_request(self, query: str) -> bool:
        """Check if query is a visualization request."""
        visualization_keywords = [
            "chart", "graph", "plot", "visualize", "show me a", "display",
            "bar chart", "pie chart", "line chart", "scatter plot",
            "create a chart", "generate a graph", "draw a plot"
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in visualization_keywords)
