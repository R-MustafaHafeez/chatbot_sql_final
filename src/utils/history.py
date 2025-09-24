"""
History Manager for conversation tracking.
Stores and retrieves conversation history by user_id.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from ..core.models import ConversationTurn
import json
import logging

logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages conversation history in memory (easily replaceable with Redis/DB)."""
    
    def __init__(self):
        # In-memory storage: {user_id: [conversation_turns]}
        self.conversations: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_per_user = 50  # Limit history size
    
    def add_turn(self, user_id: str, user_query: str, assistant_response: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Add a conversation turn to user's history."""
        try:
            turn = ConversationTurn(
                user_query=user_query,
                assistant_response=assistant_response,
                data=data
            )
            
            if user_id not in self.conversations:
                self.conversations[user_id] = []
            
            # Add new turn
            self.conversations[user_id].append(turn.model_dump())
            
            # Smart history management: Summarize when reaching 100+ conversations
            if len(self.conversations[user_id]) >= 100:
                self._summarize_history(user_id)
            
            logger.info(f"Added conversation turn for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding conversation turn: {e}")
    
    def _summarize_history(self, user_id: str) -> None:
        """Summarize conversation history when it gets too long."""
        try:
            if user_id not in self.conversations or len(self.conversations[user_id]) < 100:
                return
            
            # Get the first 80 conversations for summarization
            old_conversations = self.conversations[user_id][:80]
            recent_conversations = self.conversations[user_id][80:]
            
            # Create a summary of old conversations
            summary = self._create_conversation_summary(old_conversations)
            
            # Replace old conversations with summary + recent conversations
            self.conversations[user_id] = [summary] + recent_conversations
            
            logger.info(f"Summarized history for user {user_id}: {len(old_conversations)} conversations summarized")
            
        except Exception as e:
            logger.error(f"Error summarizing history for user {user_id}: {e}")
    
    def _create_conversation_summary(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of conversation history."""
        try:
            # Extract key information from conversations
            user_queries = [conv.get("user_query", "") for conv in conversations]
            assistant_responses = [conv.get("assistant_response", "") for conv in conversations]
            
            # Create a summary entry
            summary_entry = {
                "timestamp": conversations[0].get("timestamp", ""),
                "user_query": f"[CONVERSATION SUMMARY] {len(conversations)} previous conversations",
                "assistant_response": f"Previous conversation summary: User discussed topics including {self._extract_key_topics(user_queries)}. Key interactions involved database queries, data analysis, and general conversation.",
                "data": {
                    "type": "summary",
                    "original_count": len(conversations),
                    "summary_type": "conversation_consolidation",
                    "key_topics": self._extract_key_topics(user_queries),
                    "interaction_types": self._categorize_interactions(user_queries)
                }
            }
            
            return summary_entry
            
        except Exception as e:
            logger.error(f"Error creating conversation summary: {e}")
            return {
                "timestamp": conversations[0].get("timestamp", ""),
                "user_query": "[CONVERSATION SUMMARY] Previous conversations",
                "assistant_response": "Previous conversation summary available.",
                "data": {"type": "summary", "original_count": len(conversations)}
            }
    
    def _extract_key_topics(self, queries: List[str]) -> List[str]:
        """Extract key topics from user queries."""
        try:
            topics = set()
            for query in queries:
                query_lower = query.lower()
                if any(word in query_lower for word in ["user", "customer", "order", "product"]):
                    topics.add("database queries")
                if any(word in query_lower for word in ["chart", "graph", "visual", "plot"]):
                    topics.add("data visualization")
                if any(word in query_lower for word in ["name", "hello", "how are you"]):
                    topics.add("personal interaction")
                if any(word in query_lower for word in ["revenue", "sales", "total", "amount"]):
                    topics.add("financial analysis")
                if any(word in query_lower for word in ["city", "location", "address"]):
                    topics.add("geographic data")
            
            return list(topics)[:5]  # Return top 5 topics
            
        except Exception as e:
            logger.error(f"Error extracting key topics: {e}")
            return ["general conversation"]
    
    def _categorize_interactions(self, queries: List[str]) -> List[str]:
        """Categorize types of interactions."""
        try:
            categories = set()
            for query in queries:
                query_lower = query.lower()
                if any(word in query_lower for word in ["show", "list", "get", "find"]):
                    categories.add("data retrieval")
                if any(word in query_lower for word in ["chart", "graph", "plot", "visual"]):
                    categories.add("visualization")
                if any(word in query_lower for word in ["total", "sum", "count", "average"]):
                    categories.add("aggregation")
                if any(word in query_lower for word in ["hello", "hi", "how are you", "name"]):
                    categories.add("chit-chat")
            
            return list(categories)
            
        except Exception as e:
            logger.error(f"Error categorizing interactions: {e}")
            return ["general interaction"]
    
    def get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a user."""
        try:
            return self.conversations.get(user_id, [])
        except Exception as e:
            logger.error(f"Error retrieving history for user {user_id}: {e}")
            return []
    
    def get_recent_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history for context."""
        try:
            history = self.conversations.get(user_id, [])
            return history[-limit:] if history else []
        except Exception as e:
            logger.error(f"Error retrieving recent history for user {user_id}: {e}")
            return []
    
    def clear_history(self, user_id: str) -> None:
        """Clear conversation history for a user."""
        try:
            if user_id in self.conversations:
                del self.conversations[user_id]
                logger.info(f"Cleared history for user {user_id}")
        except Exception as e:
            logger.error(f"Error clearing history for user {user_id}: {e}")
    
    def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of user's conversation history."""
        try:
            history = self.conversations.get(user_id, [])
            return {
                "user_id": user_id,
                "total_turns": len(history),
                "last_activity": history[-1]["timestamp"] if history else None,
                "recent_queries": [turn["user_query"] for turn in history[-5:]] if history else []
            }
        except Exception as e:
            logger.error(f"Error getting conversation summary for user {user_id}: {e}")
            return {"user_id": user_id, "total_turns": 0, "last_activity": None, "recent_queries": []}
    
    def export_history(self, user_id: str) -> Optional[str]:
        """Export user's conversation history as JSON."""
        try:
            history = self.conversations.get(user_id, [])
            if not history:
                return None
            
            export_data = {
                "user_id": user_id,
                "exported_at": datetime.now().isoformat(),
                "conversation_count": len(history),
                "history": history
            }
            
            return json.dumps(export_data, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error exporting history for user {user_id}: {e}")
            return None
    
    def get_all_users(self) -> List[str]:
        """Get list of all users with conversation history."""
        return list(self.conversations.keys())
    
    def get_total_conversations(self) -> int:
        """Get total number of conversations across all users."""
        return sum(len(history) for history in self.conversations.values())
    
    def get_conversation_context(self, user_id: str, limit: int = 10) -> str:
        """Get conversation context for agents to use in their prompts."""
        try:
            history = self.get_recent_history(user_id, limit)
            if not history:
                return "No previous conversation context."
            
            context_parts = []
            for turn in history:
                user_query = turn.get("user_query", "")
                assistant_response = turn.get("assistant_response", "")
                
                # Skip summary entries in context
                if "[CONVERSATION SUMMARY]" in user_query:
                    context_parts.append(f"Previous conversations: {assistant_response}")
                else:
                    context_parts.append(f"User: {user_query}")
                    context_parts.append(f"Assistant: {assistant_response}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error getting conversation context for user {user_id}: {e}")
            return "No previous conversation context."


# Global history manager instance
history_manager = HistoryManager()
