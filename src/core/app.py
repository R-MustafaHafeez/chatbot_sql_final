"""
FastAPI application for the Conversational SQL Chatbot.
Implements the /chat endpoint with LangGraph workflow integration.
"""

import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv

from .models import ChatRequest, ChatResponse, DatabaseConfig
from .workflow import ChatbotWorkflow
from .database import create_database_manager, DatabaseManager
from ..utils.history import history_manager
from ..utils.rbac import rbac_manager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Conversational SQL Chatbot",
    description="A LangGraph-based chatbot for natural language database queries",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for workflow and database
workflow: Optional[ChatbotWorkflow] = None
db_manager: Optional[DatabaseManager] = None


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global workflow, db_manager
    
    try:
        # Initialize OpenAI client
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize database manager using factory pattern
        from config import AppConfig
        config = AppConfig()
        db_manager = DatabaseManager(config.database_config)
        
        # Initialize workflow
        workflow = ChatbotWorkflow(openai_client, db_manager)
        
        logger.info("Application started successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise


@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {
        "message": "Conversational SQL Chatbot API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "workflow_initialized": workflow is not None,
        "database_connected": db_manager is not None
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint that processes user queries through the LangGraph workflow.
    
    This endpoint:
    1. Validates the request
    2. Routes through the LangGraph workflow
    3. Returns a conversational response with optional structured data
    """
    try:
        if not workflow:
            raise HTTPException(status_code=500, detail="Workflow not initialized")
        
        # Validate required fields
        if not request.user_id or not request.role or not request.query:
            raise HTTPException(
                status_code=400, 
                detail="Missing required fields: user_id, role, or query"
            )
        
        # Validate role
        valid_roles = ["analyst", "admin", "readonly", "viewer"]
        if request.role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        logger.info(f"Processing query from user {request.user_id} with role {request.role}")
        
        # Process query through workflow
        response_data = await workflow.process_query(
            user_id=request.user_id,
            role=request.role,
            query=request.query,
            context=request.context
        )
        
        # Create response
        response = ChatResponse(
            message=response_data["message"],
            data=response_data["data"],
            history=response_data["history"]
        )
        
        logger.info(f"Query processed successfully for user {request.user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error processing your request"
        )


@app.get("/tables")
async def get_available_tables(role: str = "viewer"):
    """Get available tables for the specified role."""
    try:
        if not db_manager:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        tables = db_manager.get_available_tables(role)
        if tables is None:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return {"tables": tables}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving tables")


@app.get("/schema/{table_name}")
async def get_table_schema(table_name: str, role: str = "viewer"):
    """Get schema information for a specific table."""
    try:
        if not db_manager:
            raise HTTPException(status_code=500, detail="Database not initialized")
        
        schema = db_manager.get_table_schema(table_name, role)
        if schema is None:
            raise HTTPException(status_code=403, detail="Insufficient permissions or table not found")
        
        return schema
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema for {table_name}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving table schema")


@app.get("/roles")
async def get_available_roles():
    """Get available user roles and their permissions."""
    try:
        roles_info = rbac_manager.get_all_roles()
        return {"roles": roles_info}
    except Exception as e:
        logger.error(f"Error getting roles: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving role information")


@app.get("/history/{user_id}")
async def get_user_history(user_id: str, limit: int = 10):
    """Get conversation history for a specific user."""
    try:
        history = history_manager.get_recent_history(user_id, limit)
        return {"user_id": user_id, "history": history}
    except Exception as e:
        logger.error(f"Error getting history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving conversation history")


@app.delete("/history/{user_id}")
async def clear_user_history(user_id: str):
    """Clear conversation history for a specific user."""
    try:
        history_manager.clear_history(user_id)
        return {"message": f"History cleared for user {user_id}"}
    except Exception as e:
        logger.error(f"Error clearing history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error clearing conversation history")


@app.get("/stats")
async def get_system_stats():
    """Get system statistics."""
    try:
        total_conversations = history_manager.get_total_conversations()
        all_users = history_manager.get_all_users()
        
        return {
            "total_conversations": total_conversations,
            "active_users": len(all_users),
            "users": all_users[:10]  # Show first 10 users
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving system statistics")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
