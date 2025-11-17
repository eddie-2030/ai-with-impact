#!/bin/bash

# Skills Graph Case Study - Startup Script
# This script sets up and runs the Skills Graph application

set -e  # Exit on any error

echo "🚀 Starting Skills Graph Case Study..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check for API key
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "🔑 Please edit .env and add your OpenAI API key:"
    echo "   OPENAI_API_KEY=sk-proj-your-key-here"
    echo ""
    echo "Press Enter when ready to continue..."
    read
fi

# Generate synthetic data if it doesn't exist
if [ ! -f "data/samples/people.jsonl" ]; then
    echo "📊 Generating synthetic data..."
    python scripts/generate_synth_data.py
fi

# Export API key for the session
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the application
echo "🌐 Starting application..."
echo ""
echo "Backend API will run on: http://localhost:8000"
echo "Streamlit UI will run on: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop both services"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    pkill -f "uvicorn src.app:app" 2>/dev/null || true
    pkill -f "streamlit run" 2>/dev/null || true
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start backend in background
echo "🔧 Starting backend API..."
PYTHONPATH=$(pwd) python -m uvicorn src.app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start Streamlit in background
echo "🎨 Starting Streamlit UI..."
PYTHONPATH=$(pwd) streamlit run ui/streamlit_app.py &
STREAMLIT_PID=$!

# Wait for both processes
wait $BACKEND_PID $STREAMLIT_PID
