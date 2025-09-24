"""
Main entry point for the Conversational SQL Chatbot.
Starts the FastAPI server with the LangGraph workflow.
"""

import uvicorn
import logging
from src.core.config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Start the FastAPI server."""
    try:
        logger.info("Starting Conversational SQL Chatbot API")
        logger.info(f"Server will run on {config.app_host}:{config.app_port}")
        logger.info(f"Database configured: {config.is_database_configured()}")
        
        # Start the server
        uvicorn.run(
            "src.core.app:app",
            host=config.app_host,
            port=config.app_port,
            reload=True,  # Enable auto-reload for development
            log_level=config.log_level.lower()
        )
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    main()
