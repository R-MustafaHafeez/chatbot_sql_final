"""
Summarizer Agent - Final response generator.
Takes raw DB/visualization output and creates conversational responses.
Always runs before output (except chit-chat).
"""

from typing import Dict, Any, Optional, List
from openai import OpenAI
from ..core.models import ChatState, Command
from ..utils.history import history_manager
import logging
import json

logger = logging.getLogger(__name__)

# Summarizer Agent Prompt
SUMMARIZER_PROMPT = """
You are the final response generator.
Your task is to:
1. Take raw DB/visualization output.
2. Turn it into a short, conversational answer for the user.
3. Always be concise, natural, and professional.
4. Provide more detail ONLY if explicitly requested.

Format your response as a natural, conversational message that a human would say.
Never mention SQL, databases, or technical internals.
Focus on the insights and answers the user is looking for.
"""


class SummarizerAgent:
    """Agent that creates final conversational responses from data."""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.system_prompt = SUMMARIZER_PROMPT
    
    def summarize(self, state: ChatState) -> Command:
        """Create final conversational response from all data."""
        try:
            # Build context for summarization
            context_parts = []
            
            if state.db_results:
                context_parts.append(f"Database results: {json.dumps(state.db_results, default=str)}")
            
            if state.chart_spec:
                context_parts.append(f"Chart specification: {json.dumps(state.chart_spec, default=str)}")
            
            context = "\n".join(context_parts) if context_parts else "No data available"
            
            # Get conversation history for context
            history = history_manager.get_recent_history(state.user_id, limit=3)
            history_context = self._build_history_context(history)
            
            # Generate conversational response
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use more powerful model for summarization
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"""
                    User query: {state.query}
                    
                    Data context: {context}
                    
                    Recent conversation: {history_context}
                    
                    Provide a natural, conversational response.
                    """}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            message = response.choices[0].message.content.strip()
            
            # Prepare response data
            response_data = {}
            if state.db_results:
                response_data["table"] = state.db_results
            if state.chart_spec:
                response_data["chart"] = state.chart_spec
            
            # Add to conversation history
            history_manager.add_turn(
                user_id=state.user_id,
                user_query=state.query,
                assistant_response=message,
                data=response_data if response_data else None
            )
            
            # Get updated history
            updated_history = history_manager.get_history(state.user_id)
            
            # Update state with final response
            update = {
                "response_message": message,
                "is_complete": True
            }
            
            logger.info(f"Summarizer: Generated final response for user {state.user_id}")
            
            return Command(goto="END", update=update)
            
        except Exception as e:
            logger.error(f"Summarizer error: {e}")
            return Command(goto="END", update={
                "response_message": "I apologize, but I encountered an error processing your request. Please try again.",
                "is_complete": True
            })
    
    def _build_history_context(self, history: List[Dict[str, Any]]) -> str:
        """Build conversation history context for better responses."""
        try:
            if not history:
                return "No previous conversation"
            
            context_parts = []
            for turn in history[-3:]:  # Last 3 turns
                user_query = turn.get("user_query", "")
                assistant_response = turn.get("assistant_response", "")
                context_parts.append(f"User: {user_query}")
                context_parts.append(f"Assistant: {assistant_response}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building history context: {e}")
            return "No previous conversation"
    
    def create_data_summary(self, db_results: Dict[str, Any]) -> str:
        """Create a summary of database results."""
        try:
            if not db_results:
                return "No data available"
            
            headers = db_results.get("headers", [])
            rows = db_results.get("rows", [])
            row_count = db_results.get("row_count", 0)
            
            if not headers or not rows:
                return "No data available"
            
            # Create summary based on data
            summary_parts = []
            
            if row_count == 1:
                summary_parts.append("Found 1 record")
            else:
                summary_parts.append(f"Found {row_count} records")
            
            # Add column information
            if headers:
                summary_parts.append(f"with columns: {', '.join(headers)}")
            
            return ". ".join(summary_parts) + "."
            
        except Exception as e:
            logger.error(f"Error creating data summary: {e}")
            return "Data retrieved successfully"
    
    def create_visualization_summary(self, chart_spec: Dict[str, Any]) -> str:
        """Create a summary of visualization."""
        try:
            if not chart_spec:
                return ""
            
            chart_type = chart_spec.get("chart_type", "chart")
            label = chart_spec.get("label", "Data Visualization")
            
            return f"Created a {chart_type} chart: {label}"
            
        except Exception as e:
            logger.error(f"Error creating visualization summary: {e}")
            return "Created a data visualization"
    
    def should_provide_details(self, query: str) -> bool:
        """Check if user is asking for detailed information."""
        detail_indicators = [
            "detailed", "more information", "explain", "tell me more",
            "breakdown", "analysis", "insights", "why", "how"
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in detail_indicators)
    
    def get_response_tone(self, query: str) -> str:
        """Determine the appropriate tone for the response."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["urgent", "asap", "quickly", "fast"]):
            return "concise and direct"
        elif any(word in query_lower for word in ["please", "thank you", "help"]):
            return "polite and helpful"
        elif any(word in query_lower for word in ["explain", "understand", "learn"]):
            return "educational and detailed"
        else:
            return "professional and friendly"
