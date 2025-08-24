#!/usr/bin/env python3
"""
Simple server startup script for Face Attendance System
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def start_django():
    """Start Django server"""
    print("Starting Django server on port 8000...")
    try:
        django_process = subprocess.Popen(
            ["python", "manage.py", "runserver", "0.0.0.0:8000"],
            cwd="backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("Django server started successfully!")
        return django_process
    except Exception as e:
        print(f"Failed to start Django server: {e}")
        return None

def start_fastapi():
    """Start FastAPI server"""
    print("Starting FastAPI server on port 8001...")
    try:
        fastapi_process = subprocess.Popen(
            ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
            cwd="backend",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print("FastAPI server started successfully!")
        return fastapi_process
    except Exception as e:
        print(f"Failed to start FastAPI server: {e}")
        return None

def main():
    """Main function"""
    print("🚀 Starting Face Attendance System...")
    
    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Start Django server
    django_process = start_django()
    if not django_process:
        print("❌ Failed to start Django server")
        sys.exit(1)
    
    # Wait a bit for Django to start
    time.sleep(3)
    
    # Start FastAPI server
    fastapi_process = start_fastapi()
    if not fastapi_process:
        print("❌ Failed to start FastAPI server")
        django_process.terminate()
        sys.exit(1)
    
    print("\n🎉 Both servers started successfully!")
    print("📱 Django Web Interface: http://localhost:8000")
    print("🔌 FastAPI API: http://localhost:8001")
    print("📚 FastAPI Docs: http://localhost:8001/docs")
    print("🔑 Admin Login: admin / admin123")
    print("\nPress Ctrl+C to stop both servers...")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        django_process.terminate()
        fastapi_process.terminate()
        print("✅ Servers stopped")

if __name__ == "__main__":
    main()
