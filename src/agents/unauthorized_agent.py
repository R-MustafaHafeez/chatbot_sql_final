"""
Unauthorized Agent - Handles RBAC violations.
Provides polite denial messages when users lack permissions.
"""

from typing import Dict, Any, Optional
from ..core.models import ChatState, Command
import logging

logger = logging.getLogger(__name__)


class UnauthorizedAgent:
    """Agent for handling unauthorized access attempts."""
    
    def __init__(self):
        self.denial_messages = [
            "I don't have permission to access that information for you.",
            "Sorry, you don't have the necessary permissions to view that data.",
            "I'm unable to retrieve that information due to access restrictions.",
            "That data isn't available with your current access level.",
            "I can't access that information on your behalf."
        ]
    
    def handle_unauthorized(self, state: ChatState) -> Command:
        """Handle unauthorized access with polite denial."""
        try:
            # Get user role for context
            role = state.role
            query = state.query
            
            # Generate appropriate denial message
            message = self._generate_denial_message(role, query)
            
            # Log the unauthorized attempt
            logger.warning(f"Unauthorized access attempt by user {state.user_id} (role: {role}) for query: {query}")
            
            # Update state with denial response
            update = {
                "response_message": message,
                "is_complete": True
            }
            
            return Command(goto="END", update=update)
            
        except Exception as e:
            logger.error(f"Unauthorized agent error: {e}")
            return Command(goto="END", update={
                "response_message": "I don't have permission to access that information.",
                "is_complete": True
            })
    
    def _generate_denial_message(self, role: str, query: str) -> str:
        """Generate appropriate denial message based on context."""
        try:
            # Base denial message
            base_message = "I don't have permission to access that information for you."
            
            # Add role-specific context
            if role == "viewer":
                base_message += " As a viewer, you have limited access to data."
            elif role == "readonly":
                base_message += " Your read-only access doesn't include this information."
            elif role == "analyst":
                base_message += " This data may require admin-level access."
            
            # Add helpful suggestion
            base_message += " Please contact your administrator if you need access to this data."
            
            return base_message
            
        except Exception as e:
            logger.error(f"Error generating denial message: {e}")
            return "I don't have permission to access that information."
    
    def get_role_permissions_info(self, role: str) -> str:
        """Get information about role permissions for user education."""
        try:
            permission_info = {
                "viewer": "Viewers can access basic user and order information.",
                "readonly": "Read-only users can access most data but cannot modify anything.",
                "analyst": "Analysts can access all data and create visualizations.",
                "admin": "Admins have full access to all data and operations."
            }
            
            return permission_info.get(role, "Unknown role permissions.")
            
        except Exception as e:
            logger.error(f"Error getting role permissions info: {e}")
            return "Please contact your administrator for permission details."
    
    def suggest_alternative_query(self, query: str, role: str) -> str:
        """Suggest alternative queries that the user might have access to."""
        try:
            suggestions = {
                "viewer": [
                    "Try asking about basic user information",
                    "You can query order data",
                    "Ask for simple counts or totals"
                ],
                "readonly": [
                    "You can access most data tables",
                    "Try asking for user or product information",
                    "You can create visualizations of accessible data"
                ],
                "analyst": [
                    "You have access to most data",
                    "Try asking for analytics or trends",
                    "You can create complex visualizations"
                ],
                "admin": [
                    "You should have access to all data",
                    "Contact support if you're getting this error"
                ]
            }
            
            role_suggestions = suggestions.get(role, ["Please contact your administrator"])
            return f"Alternative suggestions: {'; '.join(role_suggestions[:2])}"
            
        except Exception as e:
            logger.error(f"Error suggesting alternative query: {e}")
            return "Please try a different query or contact your administrator."
