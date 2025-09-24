"""
Pydantic models for the Conversational SQL Chatbot API.
Defines request/response contracts and internal data structures.
"""

from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    """Input contract for the /chat endpoint."""
    user_id: str = Field(..., description="User identifier for history and RBAC")
    role: str = Field(..., description="User role for RBAC enforcement")
    query: str = Field(..., description="User's natural language query")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")


class ChatResponse(BaseModel):
    """Output contract for the /chat endpoint."""
    message: str = Field(..., description="Conversational response to user")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Structured data if any")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")


class ChatState(BaseModel):
    """Shared state for LangGraph workflow."""
    user_id: str
    role: str
    query: str
    context: Optional[Dict[str, Any]] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Agent-specific data
    sql_query: Optional[str] = None
    db_results: Optional[Dict[str, Any]] = None
    chart_spec: Optional[Dict[str, Any]] = None
    response_message: Optional[str] = None
    
    # Control flow
    next_agent: Optional[str] = None
    is_complete: bool = False


class Command(BaseModel):
    """Command for LangGraph node transitions."""
    goto: str = Field(..., description="Next agent to route to")
    update: Optional[Dict[str, Any]] = Field(default=None, description="State updates")


class DatabaseResult(BaseModel):
    """Structured database query result."""
    type: Literal["table"] = "table"
    headers: List[str] = Field(..., description="Column headers")
    rows: List[List[Any]] = Field(..., description="Data rows")
    row_count: int = Field(..., description="Number of rows returned")


class ChartSpec(BaseModel):
    """Chart specification for visualization."""
    type: Literal["chart"] = "chart"
    chart_type: Literal["bar", "line", "pie", "scatter"] = Field(..., description="Chart type")
    x: List[Any] = Field(..., description="X-axis data")
    y: List[Any] = Field(..., description="Y-axis data")
    label: str = Field(..., description="Chart title/label")
    x_label: Optional[str] = None
    y_label: Optional[str] = None


class ConversationTurn(BaseModel):
    """Single conversation turn in history."""
    timestamp: datetime = Field(default_factory=datetime.now)
    user_query: str
    assistant_response: str
    data: Optional[Dict[str, Any]] = None


class RBACConfig(BaseModel):
    """RBAC configuration for different roles."""
    analyst: List[str] = Field(default_factory=lambda: ["SELECT"])
    admin: List[str] = Field(default_factory=lambda: ["SELECT", "INSERT", "UPDATE", "DELETE"])
    readonly: List[str] = Field(default_factory=lambda: ["SELECT"])
    viewer: List[str] = Field(default_factory=lambda: ["SELECT"])


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    schema: Optional[str] = None
