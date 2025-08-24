#!/usr/bin/env python3
"""
Complete Face Attendance System Startup Script
Initializes both Django and FastAPI with liveness detection
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(command, cwd=None, shell=True):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Command successful: {command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {command}")
        logger.error(f"Error: {e.stderr}")
        return None

def setup_django():
    """Setup Django system"""
    logger.info("Setting up Django system...")
    
    # Change to backend directory
    backend_dir = Path("backend")
    os.chdir(backend_dir)
    
    # Run Django migrations
    logger.info("Running Django migrations...")
    if not run_command("python manage.py makemigrations attendance"):
        logger.error("Django makemigrations failed")
        return False
    
    if not run_command("python manage.py migrate"):
        logger.error("Django migrate failed")
        return False
    
    logger.info("Django setup completed successfully")
    return True

def setup_fastapi():
    """Setup FastAPI system"""
    logger.info("Setting up FastAPI system...")
    
    # Change to backend directory
    backend_dir = Path("backend")
    os.chdir(backend_dir)
    
    # Test FastAPI setup
    logger.info("Testing FastAPI setup...")
    if not run_command("python test_fastapi.py"):
        logger.error("FastAPI setup test failed")
        return False
    
    logger.info("FastAPI setup completed successfully")
    return True

def start_servers():
    """Start both Django and FastAPI servers"""
    logger.info("Starting servers...")
    
    # Start Django server in background
    logger.info("Starting Django server...")
    django_process = subprocess.Popen(
        ["python", "start_backend.py"],
        cwd="backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait a bit for Django to start
    time.sleep(3)
    
    # Start FastAPI server in background
    logger.info("Starting FastAPI server...")
    fastapi_process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        cwd="backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    logger.info("🎉 Both servers started successfully!")
    logger.info("📱 Django Web Interface: http://localhost:8000")
    logger.info("🔌 FastAPI API: http://localhost:8001")
    logger.info("📚 FastAPI Docs: http://localhost:8001/docs")
    logger.info("🔑 Admin Login: admin / admin123")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
        django_process.terminate()
        fastapi_process.terminate()
        logger.info("Servers stopped")

def main():
    """Main startup function"""
    logger.info("🚀 Starting Complete Face Attendance System with Liveness Detection...")
    
    # Check if we're in the right directory
    if not Path("backend").exists():
        logger.error("Please run this script from the project root directory")
        sys.exit(1)
    
    # Setup Django
    if not setup_django():
        logger.error("Django setup failed")
        sys.exit(1)
    
    # Setup FastAPI
    if not setup_fastapi():
        logger.error("FastAPI setup failed")
        sys.exit(1)
    
    # Start servers
    start_servers()

if __name__ == "__main__":
    main()
