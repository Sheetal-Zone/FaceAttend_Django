#!/usr/bin/env python3
"""
FastAPI Database Setup Script
This script initializes the database for the FastAPI Face Attendance System.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import create_tables, SessionLocal
from app.auth import init_admin_password
from app.models import Student, Attendance, DetectionLog
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_database():
    """Set up the database with tables and initial data."""
    print("🗄️  Setting up FastAPI Face Attendance System Database...")
    
    try:
        # Create tables
        print("📦 Creating database tables...")
        create_tables()
        print("✅ Database tables created successfully")
        
        # Initialize admin password
        print("🔐 Initializing admin authentication...")
        init_admin_password()
        print("✅ Admin authentication initialized")
        
        # Test database connection
        print("🔍 Testing database connection...")
        db = SessionLocal()
        try:
            # Test query
            student_count = db.query(Student).count()
            attendance_count = db.query(Attendance).count()
            log_count = db.query(DetectionLog).count()
            
            print(f"✅ Database connection successful")
            print(f"   - Students: {student_count}")
            print(f"   - Attendance records: {attendance_count}")
            print(f"   - Detection logs: {log_count}")
            
        finally:
            db.close()
        
        print("🎉 Database setup completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Start the FastAPI server: uvicorn main:app --reload")
        print("   2. Access API docs: http://localhost:8000/docs")
        print("   3. Login with: admin / admin123")
        
    except Exception as e:
        logger.error(f"❌ Error setting up database: {e}")
        print(f"❌ Error setting up database: {e}")
        sys.exit(1)

def create_sample_data():
    """Create sample data for testing."""
    print("📝 Creating sample data...")
    
    try:
        db = SessionLocal()
        
        # Check if sample data already exists
        if db.query(Student).count() > 0:
            print("ℹ️  Sample data already exists, skipping...")
            return
        
        # Create sample students
        sample_students = [
            {
                "name": "John Doe",
                "roll_number": "CS001",
                "photo_url": "https://example.com/photos/john_doe.jpg"
            },
            {
                "name": "Jane Smith",
                "roll_number": "CS002", 
                "photo_url": "https://example.com/photos/jane_smith.jpg"
            },
            {
                "name": "Mike Johnson",
                "roll_number": "CS003",
                "photo_url": "https://example.com/photos/mike_johnson.jpg"
            }
        ]
        
        for student_data in sample_students:
            student = Student(**student_data)
            db.add(student)
        
        db.commit()
        print(f"✅ Created {len(sample_students)} sample students")
        
    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        print(f"❌ Error creating sample data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_database()
    
    # Ask if user wants sample data
    response = input("\n🤔 Would you like to create sample data? (y/n): ")
    if response.lower() in ['y', 'yes']:
        create_sample_data()
    
    print("\n✨ Setup complete! Happy coding! 🚀")
