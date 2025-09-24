"""
LangGraph workflow implementation for the Conversational SQL Chatbot.
Defines the graph structure, nodes, and edges for the agent routing system.
"""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from models import ChatState, Command
from agents.router_agent import RouterAgent
from agents.chitchat_agent import ChitChatAgent
from agents.db_agent1 import DatabaseAgent1
from agents.db_agent2 import DatabaseAgent2
from agents.visualizer_agent import VisualizerAgent
from agents.summarizer_agent import SummarizerAgent
from agents.unauthorized_agent import UnauthorizedAgent
from utils.history import history_manager
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class ChatbotWorkflow:
    """Main workflow class that orchestrates the LangGraph-based chatbot."""
    
    def __init__(self, openai_client: OpenAI, db_manager=None):
        self.client = openai_client
        self.db_manager = db_manager
        
        # Initialize agents
        self.router = RouterAgent(openai_client)
        self.chitchat = ChitChatAgent(openai_client)
        self.db_agent_1 = DatabaseAgent1(openai_client, db_manager)
        self.db_agent_2 = DatabaseAgent2(openai_client, db_manager)
        self.visualizer = VisualizerAgent(openai_client)
        self.summarizer = SummarizerAgent(openai_client)
        self.unauthorized = UnauthorizedAgent()
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with proper routing logic."""
        
        # Create the state graph
        workflow = StateGraph(ChatState)
        
        # Add nodes (agents)
        workflow.add_node("router", self._router_node)
        workflow.add_node("chitchat", self._chitchat_node)
        workflow.add_node("db_agent_1", self._db_agent_1_node)
        workflow.add_node("db_agent_2", self._db_agent_2_node)
        workflow.add_node("visualizer", self._visualizer_node)
        workflow.add_node("summarizer", self._summarizer_node)
        workflow.add_node("unauthorized", self._unauthorized_node)
        
        # Define edges and routing logic
        workflow.add_edge(START, "router")
        
        # Router can route to any agent based on intent classification
        workflow.add_conditional_edges(
            "router",
            self._route_after_router,
            {
                "chitchat": "chitchat",
                "db_agent_1": "db_agent_1",
                "db_agent_2": "db_agent_2",
                "unauthorized": "unauthorized"
            }
        )
        
        # Database agents route to visualizer or summarizer
        workflow.add_conditional_edges(
            "db_agent_1",
            self._route_after_db,
            {
                "visualizer": "visualizer",
                "summarizer": "summarizer"
            }
        )
        
        workflow.add_conditional_edges(
            "db_agent_2", 
            self._route_after_db,
            {
                "visualizer": "visualizer",
                "summarizer": "summarizer"
            }
        )
        
        # Visualizer always routes to summarizer
        workflow.add_edge("visualizer", "summarizer")
        
        # All agents end the workflow
        workflow.add_edge("summarizer", END)
        workflow.add_edge("chitchat", END)
        workflow.add_edge("unauthorized", END)
        
        # Compile the graph with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def _router_node(self, state: ChatState) -> ChatState:
        """Router node that analyzes intent and routes to appropriate agent."""
        try:
            command = self.router.classify_intent(state)
            
            # Update state with routing decision
            if command.update:
                state_dict = state.model_dump()
                state_dict.update(command.update)
                state = ChatState(**state_dict)
            
            # Set next agent for conditional routing
            state.next_agent = command.goto
            return state
            
        except Exception as e:
            logger.error(f"Router node error: {e}")
            state.next_agent = "chitchat"
            return state
    
    def _chitchat_node(self, state: ChatState) -> ChatState:
        """ChitChat node for casual conversation."""
        try:
            command = self.chitchat.handle_conversation(state)
            
            # Update state with response
            if command.update:
                state_dict = state.model_dump()
                state_dict.update(command.update)
                state = ChatState(**state_dict)
            
            # Mark as complete
            state.is_complete = True
            state.next_agent = None
            return state
            
        except Exception as e:
            logger.error(f"ChitChat node error: {e}")
            state.is_complete = True
            state.response_message = "Hello! I'm here to help. How can I assist you today?"
            return state
    
    def _db_agent_1_node(self, state: ChatState) -> ChatState:
        """Database Agent 1 node for simple queries."""
        try:
            command = self.db_agent_1.process_query(state)
            
            # Update state with results
            if command.update:
                state_dict = state.model_dump()
                state_dict.update(command.update)
                state = ChatState(**state_dict)
            
            # Set next agent
            state.next_agent = command.goto
            return state
            
        except Exception as e:
            logger.error(f"Database Agent 1 node error: {e}")
            state.next_agent = "summarizer"
            state.response_message = "I encountered an error processing your request."
            return state
    
    def _db_agent_2_node(self, state: ChatState) -> ChatState:
        """Database Agent 2 node for complex queries."""
        try:
            command = self.db_agent_2.process_query(state)
            
            # Update state with results
            if command.update:
                state_dict = state.model_dump()
                state_dict.update(command.update)
                state = ChatState(**state_dict)
            
            # Set next agent
            state.next_agent = command.goto
            return state
            
        except Exception as e:
            logger.error(f"Database Agent 2 node error: {e}")
            state.next_agent = "summarizer"
            state.response_message = "I encountered an error processing your complex request."
            return state
    
    def _visualizer_node(self, state: ChatState) -> ChatState:
        """Visualizer node for creating charts and graphs."""
        try:
            command = self.visualizer.create_visualization(state)
            
            # Update state with chart spec
            if command.update:
                state_dict = state.model_dump()
                state_dict.update(command.update)
                state = ChatState(**state_dict)
            
            # Set next agent
            state.next_agent = command.goto
            return state
            
        except Exception as e:
            logger.error(f"Visualizer node error: {e}")
            state.next_agent = "summarizer"
            state.response_message = "I couldn't create a visualization. Let me provide the data in a different format."
            return state
    
    def _unauthorized_node(self, state: ChatState) -> ChatState:
        """Unauthorized node for handling RBAC violations."""
        try:
            command = self.unauthorized.handle_unauthorized(state)
            
            # Update state with denial response
            if command.update:
                state_dict = state.model_dump()
                state_dict.update(command.update)
                state = ChatState(**state_dict)
            
            # Mark as complete
            state.is_complete = True
            state.next_agent = None
            return state
            
        except Exception as e:
            logger.error(f"Unauthorized node error: {e}")
            state.is_complete = True
            state.response_message = "I don't have permission to access that information."
            return state
    
    def _summarizer_node(self, state: ChatState) -> ChatState:
        """Summarizer node that creates final conversational response."""
        try:
            command = self.summarizer.summarize(state)
            
            # Update state with final response
            if command.update:
                state_dict = state.model_dump()
                state_dict.update(command.update)
                state = ChatState(**state_dict)
            
            # Mark as complete
            state.is_complete = True
            state.next_agent = None
            return state
            
        except Exception as e:
            logger.error(f"Summarizer node error: {e}")
            state.is_complete = True
            state.response_message = "I apologize, but I encountered an error. Please try again."
            return state
    
    def _route_after_router(self, state: ChatState) -> str:
        """Route after router based on intent classification."""
        return state.next_agent or "chitchat"
    
    def _route_after_db(self, state: ChatState) -> str:
        """Route after database agents based on visualization needs."""
        # Check if visualization was requested
        if state.context and state.context.get("needs_visualization", False):
            return "visualizer"
        
        # Also check if the query itself is a visualization request
        visualization_keywords = [
            "chart", "graph", "plot", "visualize", "show me a", "display",
            "bar chart", "pie chart", "line chart", "scatter plot",
            "create a chart", "generate a graph", "draw a plot"
        ]
        query_lower = state.query.lower()
        if any(keyword in query_lower for keyword in visualization_keywords):
            return "visualizer"
        
        return "summarizer"
    
    async def process_query(self, user_id: str, role: str, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a user query through the workflow."""
        try:
            # Create initial state
            initial_state = ChatState(
                user_id=user_id,
                role=role,
                query=query,
                context=context or {}
            )
            
            # Run the workflow
            config = {"configurable": {"thread_id": f"{user_id}_{hash(query)}"}}
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            # Extract response data
            response_data = {}
            if final_state.get("db_results"):
                response_data["table"] = final_state["db_results"]
            if final_state.get("chart_spec"):
                response_data["chart"] = final_state["chart_spec"]
            
            # Get conversation history from history manager
            history = history_manager.get_history(user_id)
            
            return {
                "message": final_state.get("response_message") or "I'm sorry, I couldn't process your request.",
                "data": response_data if response_data else None,
                "history": history
            }
            
        except Exception as e:
            logger.error(f"Workflow processing error: {e}")
            return {
                "message": "I apologize, but I encountered an error processing your request. Please try again.",
                "data": None,
                "history": []
            }
