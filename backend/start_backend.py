#!/usr/bin/env python3
"""
Backend startup script for Face Attendance System
Ensures database is running and all migrations are applied
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

def run_command(command, cwd=None, return_output=False):
    """Run a command and return True for success, False for failure"""
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
        if return_output:
            return result.stdout
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {command}")
        logger.error(f"Error: {e.stderr}")
        return False

def ensure_database():
    """Ensure database is properly set up"""
    logger.info("Setting up database...")
    
    # Create logs directory if it doesn't exist
    logs_dir = backend_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Run migrations
    logger.info("Running database migrations...")
    if not run_command("python manage.py makemigrations"):
        logger.error("Failed to create migrations")
        return False
    
    if not run_command("python manage.py migrate"):
        logger.error("Failed to apply migrations")
        return False
    
    # Create superuser if it doesn't exist
    logger.info("Checking for superuser...")
    result = run_command("python manage.py shell -c \"from django.contrib.auth.models import User; print('Superuser exists' if User.objects.filter(is_superuser=True).exists() else 'No superuser')\"", return_output=True)
    
    if result and "No superuser" in result:
        logger.info("Creating superuser...")
        # Create superuser with default credentials
        create_superuser_script = """
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"""
        with open("create_superuser.py", "w") as f:
            f.write(create_superuser_script)
        
        run_command("python manage.py shell < create_superuser.py")
        os.remove("create_superuser.py")
    
    logger.info("Database setup completed")
    return True

def collect_static():
    """Collect static files"""
    logger.info("Collecting static files...")
    if not run_command("python manage.py collectstatic --noinput"):
        logger.error("Failed to collect static files")
        return False
    logger.info("Static files collected")
    return True

def start_server():
    """Start the Django development server"""
    logger.info("Starting Django development server...")
    
    # Set environment variables
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'face_attendance.settings')
    
    # Start the server
    try:
        subprocess.run([
            "python", "manage.py", "runserver", "0.0.0.0:8000"
        ], cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        return False
    
    return True

def main():
    """Main startup function"""
    logger.info("Starting Face Attendance System Backend...")
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    # Ensure models are downloaded (call root-level script)
    try:
        root_dir = backend_dir.parent
        logger.info("Verifying required AI models via root downloader...")
        subprocess.run([sys.executable, str(root_dir / "download_models.py")], check=True)
    except Exception as e:
        logger.warning(f"Model verification script failed or missing: {e}")
    
    # Ensure database is set up
    if not ensure_database():
        logger.error("Database setup failed")
        sys.exit(1)
    
    # Collect static files
    if not collect_static():
        logger.error("Static file collection failed")
        sys.exit(1)
    
    # Start the server
    if not start_server():
        logger.error("Server startup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
