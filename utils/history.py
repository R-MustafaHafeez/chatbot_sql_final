"""
History Manager for conversation tracking.
Stores and retrieves conversation history by user_id.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from models import ConversationTurn
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
            
            # Trim history if too long
            if len(self.conversations[user_id]) > self.max_history_per_user:
                self.conversations[user_id] = self.conversations[user_id][-self.max_history_per_user:]
            
            logger.info(f"Added conversation turn for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error adding conversation turn: {e}")
    
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


# Global history manager instance
history_manager = HistoryManager()
