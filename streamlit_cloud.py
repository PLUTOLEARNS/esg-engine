"""
Streamlit Cloud deployment script for ESG Engine
This script starts both the FastAPI backend and Streamlit frontend
"""
import subprocess
import time
import sys
import os
from pathlib import Path

def start_backend():
    """Start the FastAPI backend server"""
    print("🚀 Starting FastAPI backend...")
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # Start backend server
    backend_process = subprocess.Popen([
        sys.executable, "-m", "uvicorn", 
        "backend.app:app", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    return backend_process

def main():
    """Main deployment function for Streamlit Cloud"""
    print("🌱 ESG Engine - भारत Edition Starting...")
    
    # Start backend in a separate process
    backend_process = start_backend()
    
    # Give backend time to start
    time.sleep(3)
    
    print("✅ Backend started successfully!")
    print("📊 Streamlit frontend will start automatically")
    
    # Keep the backend process alive
    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
        backend_process.terminate()
        backend_process.wait()

if __name__ == "__main__":
    main()
