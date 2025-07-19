#!/bin/bash
# Startup script for Streamlit Cloud deployment

echo "🌱 Starting ESG Engine - भारत Edition..."

# Install dependencies
pip install -r requirements.txt

# Create data directory if it doesn't exist
mkdir -p data

# Start the backend server in the background
echo "Starting FastAPI backend..."
uvicorn backend.app:app --host 0.0.0.0 --port 8000 &

# Wait a moment for backend to start
sleep 5

# Start the Streamlit frontend
echo "Starting Streamlit frontend..."
streamlit run frontend/streamlit_app.py --server.port 8501 --server.address 0.0.0.0
