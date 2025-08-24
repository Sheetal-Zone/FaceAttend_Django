#!/usr/bin/env python3
"""
FastAPI startup script for Face Attendance System
Ensures database is running and all models are initialized
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_command(command, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or backend_dir,
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

def ensure_database():
    """Ensure database is properly set up"""
    logger.info("Setting up FastAPI database...")
    
    # Create logs directory if it doesn't exist
    logs_dir = backend_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Initialize FastAPI database
    logger.info("Initializing FastAPI database...")
    if not run_command("python scripts/init_db.py"):
        logger.error("Failed to initialize FastAPI database")
        return False
    
    logger.info("FastAPI database setup completed")
    return True

def start_fastapi_server():
    """Start the FastAPI server"""
    logger.info("Starting FastAPI server...")
    
    # Set environment variables
    os.environ.setdefault('PYTHONPATH', str(backend_dir))
    
    # Start the server
    try:
        subprocess.run([
            "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"
        ], cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        return False
    
    return True

def main():
    """Main startup function"""
    logger.info("Starting Face Attendance System FastAPI...")
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    # Ensure database is set up
    if not ensure_database():
        logger.error("Database setup failed")
        sys.exit(1)
    
    # Start the FastAPI server
    if not start_fastapi_server():
        logger.error("FastAPI server startup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
