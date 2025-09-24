#!/bin/bash

# Conversational SQL Chatbot Startup Script

echo "🚀 Starting Conversational SQL Chatbot"
echo "========================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check for environment file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from example..."
    cp env.example .env
    echo "📝 Please edit .env file with your OpenAI API key and other settings"
    echo "   Required: OPENAI_API_KEY=your_key_here"
fi

# Start the application
echo "🌟 Starting the chatbot server..."
echo "   Server will be available at: http://localhost:8000"
echo "   API documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
