#!/usr/bin/env python3
"""
Test script for FastAPI setup
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    from app.database import create_tables, SessionLocal
    from app.models import Student, Attendance, DetectionLog, LivenessDetectionSession
    from app.auth import init_admin_password
    print("✅ Successfully imported FastAPI modules")
    
    # Test database creation
    print("📦 Creating database tables...")
    create_tables()
    print("✅ Database tables created successfully")
    
    # Test database connection
    print("🔍 Testing database connection...")
    db = SessionLocal()
    try:
        # Test query
        student_count = db.query(Student).count()
        attendance_count = db.query(Attendance).count()
        log_count = db.query(DetectionLog).count()
        liveness_session_count = db.query(LivenessDetectionSession).count()
        
        print(f"✅ Database connection successful")
        print(f"   - Students: {student_count}")
        print(f"   - Attendance records: {attendance_count}")
        print(f"   - Detection logs: {log_count}")
        print(f"   - Liveness detection sessions: {liveness_session_count}")
        
    finally:
        db.close()
    
    # Test admin password initialization
    print("🔐 Initializing admin authentication...")
    init_admin_password()
    print("✅ Admin authentication initialized")
    
    print("🎉 FastAPI setup test completed successfully!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
