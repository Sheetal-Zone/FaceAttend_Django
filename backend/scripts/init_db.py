#!/usr/bin/env python3
"""
Database Initialization Script for FastAPI
Creates all necessary tables and initializes the database
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import create_tables, engine
from app.models import Base, Student, LivenessDetectionSession, AttendanceLog, DetectionLog
from app.auth import create_admin_user
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with all tables"""
    try:
        logger.info("Initializing database...")
        
        # Create all tables
        create_tables()
        logger.info("Database tables created successfully")
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Available tables: {tables}")
        
        # Check if required tables exist
        required_tables = ['students', 'liveness_detection_sessions', 'attendance', 'detection_logs']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"Missing required tables: {missing_tables}")
            return False
        
        logger.info("All required tables are present")
        
        # Create admin user if it doesn't exist
        try:
            create_admin_user()
            logger.info("Admin user created/verified")
        except Exception as e:
            logger.warning(f"Admin user creation failed: {e}")
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    if success:
        print("✅ Database initialized successfully!")
        sys.exit(0)
    else:
        print("❌ Database initialization failed!")
        sys.exit(1)
