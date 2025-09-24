# Enhanced Conversational SQL Chatbot

A production-ready conversational SQL chatbot built with LangGraph, FastAPI, and OpenAI LLMs. Features modular agent architecture, enhanced RBAC, conversation history management, and intelligent routing through specialized agents.

## 🚀 Enhanced Features

- **Modular Agent Architecture**: Separate agent modules with specific prompts
- **Enhanced RBAC**: Role-based permissions with table/column-level access control
- **History Management**: In-memory conversation tracking (easily replaceable with Redis/DB)
- **Intelligent Routing**: gpt-4o-mini for lightweight intent classification
- **Data Visualization**: Automatic chart generation with multiple chart types
- **Conversational Interface**: Natural language responses with context awareness
- **System Monitoring**: Statistics and health monitoring endpoints

## 🏗️ Enhanced Architecture

### Modular Agent System

```
[User Input] → [History Manager] → [Router Agent (gpt-4o-mini)]
                                        │
                                        ├──> [Chit-Chat Agent] ──┐
                                        │                        │
                                        ├──> [Database Agent 1] ─┤
                                        │                        │
                                        ├──> [Database Agent 2] ─┤
                                        │                        │
                                        └──> [Unauthorized Handler]
                                                                    │
                                                                    ▼
                                            [Visualizer Agent?] → [Summarizer Agent (gpt-4o)]
                                                                    │
                                                                    ▼
                                                              [Final Output]
```

### Agent Modules

1. **Router Agent** (`agents/router_agent.py`): Lightweight intent classification
2. **Chit-Chat Agent** (`agents/chitchat_agent.py`): Casual conversation handling
3. **Database Agent 1** (`agents/db_agent1.py`): Simple SQL queries with RBAC
4. **Database Agent 2** (`agents/db_agent2.py`): Complex queries with joins/aggregations
5. **Visualizer Agent** (`agents/visualizer_agent.py`): Chart specification generation
6. **Summarizer Agent** (`agents/summarizer_agent.py`): Final conversational responses
7. **Unauthorized Agent** (`agents/unauthorized_agent.py`): RBAC violation handling

### Utility Modules

- **History Manager** (`utils/history.py`): Conversation tracking and retrieval
- **RBAC Manager** (`utils/rbac.py`): Role-based access control enforcement

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd chatbotfinal
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

## Configuration

### Required Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key for LLM functionality

### Optional Environment Variables

- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)
- `DB_NAME`: Database name (default: chatbot_db)
- `DB_USER`: Database username (default: postgres)
- `DB_PASSWORD`: Database password
- `APP_HOST`: Server host (default: 0.0.0.0)
- `APP_PORT`: Server port (default: 8000)

## Usage

### Starting the Server

```bash
python main.py
```

The server will start on `http://localhost:8000` by default.

### Enhanced API Endpoints

#### POST /chat

Main endpoint for conversational queries with enhanced routing.

**Request Body**:
```json
{
  "user_id": "12345",
  "role": "analyst",
  "query": "Show me a bar chart of sales by region",
  "context": {
    "session_id": "abcd-efgh",
    "timestamp": "2025-01-24T22:50:00Z"
  }
}
```

**Response**:
```json
{
  "message": "Here's a bar chart showing sales by region...",
  "data": {
    "table": {
      "type": "table",
      "headers": ["region", "sales"],
      "rows": [["North", 50000], ["South", 30000]],
      "row_count": 2
    },
    "chart": {
      "type": "chart",
      "chart_type": "bar",
      "x": ["North", "South"],
      "y": [50000, 30000],
      "label": "Sales by Region"
    }
  },
  "history": [...]
}
```

#### GET /health

Health check endpoint with system status.

#### GET /roles

Get available user roles and their permissions (enhanced RBAC info).

#### GET /tables?role=analyst

Get available tables for a specific role.

#### GET /schema/{table_name}?role=analyst

Get schema information for a specific table.

#### GET /history/{user_id}?limit=10

Get conversation history for a specific user.

#### DELETE /history/{user_id}

Clear conversation history for a specific user.

#### GET /stats

Get system statistics (total conversations, active users, etc.).

### User Roles

- **analyst**: Can query data and create visualizations
- **admin**: Full database access (SELECT, INSERT, UPDATE, DELETE)
- **readonly**: Read-only access to data
- **viewer**: Limited read access

## Example Queries

### Data Queries
- "How many users do we have?"
- "Show me the top 10 customers by revenue"
- "What's the average order value this month?"

### Visualization Requests
- "Create a bar chart of sales by region"
- "Show me a line graph of user growth over time"
- "Plot the distribution of order amounts"

### Casual Conversation
- "Hello, how are you?"
- "What can you help me with?"
- "Thanks for your help!"

## Development

### Project Structure

```
chatbotfinal/
├── agents.py          # LangGraph agent implementations
├── app.py             # FastAPI application
├── config.py          # Configuration management
├── database.py         # Database connection and RBAC
├── main.py            # Application entry point
├── models.py          # Pydantic models
├── state.py           # LangGraph state management
├── workflow.py        # LangGraph workflow definition
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

### Adding New Agents

1. Create a new agent class inheriting from `BaseAgent`
2. Implement the required methods
3. Add the agent to the workflow in `workflow.py`
4. Define routing logic in the router agent

### Customizing RBAC

Modify the `RBACConfig` class in `models.py` to add new roles or permissions.

## Database Setup

### Using PostgreSQL (Recommended)

1. Install PostgreSQL
2. Create a database:
   ```sql
   CREATE DATABASE chatbot_db;
   ```
3. Configure environment variables in `.env`

### Using Mock Database (Development)

If no database is configured, the system will use a mock database with sample data for development and testing.

## Security Considerations

- All SQL queries are validated for safety
- Only SELECT statements are allowed for non-admin users
- SQL injection protection through parameterized queries
- Role-based access control enforced at the database level

## Troubleshooting

### Common Issues

1. **OpenAI API Key Error**: Ensure `OPENAI_API_KEY` is set in your environment
2. **Database Connection Error**: Check database configuration and connectivity
3. **Import Errors**: Ensure all dependencies are installed with `pip install -r requirements.txt`

### Logs

The application logs are configured via the `LOG_LEVEL` environment variable. Set to `DEBUG` for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
