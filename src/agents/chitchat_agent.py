"""
Chit-Chat Agent - Handles casual conversation and small talk.
Provides friendly, conversational responses without database access.
"""

from typing import Dict, Any, Optional
from openai import OpenAI
from ..core.models import ChatState, Command
import logging

logger = logging.getLogger(__name__)

# Chit-Chat Agent Prompt
CHITCHAT_PROMPT = """
You are a friendly assistant for casual conversation.
Keep responses short, natural, and conversational.
Never mention databases, SQL, or system internals.
"""


class ChitChatAgent:
    """Agent for handling casual conversation and small talk."""
    
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self.system_prompt = CHITCHAT_PROMPT
    
    def handle_conversation(self, state: ChatState) -> Command:
        """Handle casual conversation and return response."""
        try:
            query = state.query
            
            # Generate conversational response
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            message = response.choices[0].message.content.strip()
            
            # Update state with response
            update = {
                "response_message": message,
                "is_complete": True
            }
            
            logger.info(f"ChitChat: Generated response for casual conversation")
            
            return Command(goto="END", update=update)
            
        except Exception as e:
            logger.error(f"ChitChat error: {e}")
            # Fallback response
            fallback_message = "Hello! I'm here to help. How can I assist you today?"
            return Command(goto="END", update={
                "response_message": fallback_message,
                "is_complete": True
            })
    
    def get_conversation_context(self, user_id: str, history: list) -> str:
        """Get conversation context from history for better responses."""
        try:
            if not history:
                return ""
            
            # Get recent conversation context
            recent_turns = history[-3:] if len(history) >= 3 else history
            context_parts = []
            
            for turn in recent_turns:
                context_parts.append(f"User: {turn.get('user_query', '')}")
                context_parts.append(f"Assistant: {turn.get('assistant_response', '')}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return ""
    
    def is_casual_query(self, query: str) -> bool:
        """Check if query is casual conversation."""
        casual_patterns = [
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "thanks", "thank you", "bye", "goodbye",
            "nice to meet you", "how's it going", "what's new", "help", "joke",
            "tell me a story", "what's the weather", "how's your day"
        ]
        
        query_lower = query.lower()
        return any(pattern in query_lower for pattern in casual_patterns)
