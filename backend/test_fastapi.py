#!/usr/bin/env python3
"""
FastAPI Setup Test Script
Tests all components of the FastAPI application
"""

import sys
import os
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing module imports...")
    
    try:
        from app.config import settings
        print("✅ Config module imported")
        
        from app.database import engine, create_tables
        print("✅ Database module imported")
        
        from app.models import Base, Student, LivenessDetectionSession, Attendance, DetectionLog, AdminUser
        print("✅ Models module imported")
        
        from app.auth import authenticate_admin, create_access_token, verify_token
        print("✅ Auth module imported")
        
        from app.ai_models import face_recognition_system, liveness_detection_system
        print("✅ AI models module imported")
        
        from app.liveness_detection import liveness_detection_engine
        print("✅ Liveness detection module imported")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during import: {e}")
        return False

def test_database():
    """Test database connection and table creation"""
    print("\n🗄️  Testing database...")
    
    try:
        from app.database import engine, create_tables
        
        # Test database connection
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
        
        # Create tables
        create_tables()
        print("✅ Database tables created")
        
        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Available tables: {tables}")
        
        required_tables = ['admin_users', 'students', 'liveness_detection_sessions', 'attendance', 'detection_logs']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        
        print("✅ All required tables present")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_ai_models():
    """Test AI model initialization"""
    print("\n🤖 Testing AI models...")
    
    try:
        from app.ai_models import face_recognition_system, liveness_detection_system
        
        # Test face recognition system
        if face_recognition_system.initialize_models():
            print("✅ Face recognition system initialized")
        else:
            print("⚠️  Face recognition system initialization failed (using fallback)")
        
        # Test liveness detection system
        if liveness_detection_system.initialize_models():
            print("✅ Liveness detection system initialized")
        else:
            print("⚠️  Liveness detection system initialization failed (using fallback)")
        
        return True
        
    except Exception as e:
        print(f"❌ AI models test failed: {e}")
        return False

def test_liveness_engine():
    """Test liveness detection engine"""
    print("\n🔄 Testing liveness detection engine...")
    
    try:
        from app.liveness_detection import liveness_detection_engine
        
        if liveness_detection_engine.initialize_models():
            print("✅ Liveness detection engine initialized")
        else:
            print("⚠️  Liveness detection engine initialization failed (using fallback)")
        
        return True
        
    except Exception as e:
        print(f"❌ Liveness engine test failed: {e}")
        return False

def test_auth():
    """Test authentication system"""
    print("\n🔐 Testing authentication...")
    
    try:
        from app.auth import authenticate_admin, create_access_token, verify_token
        from app.config import settings
        
        # Test admin authentication
        if authenticate_admin(settings.admin_username, settings.admin_password):
            print("✅ Admin authentication working")
        else:
            print("❌ Admin authentication failed")
            return False
        
        # Test token creation and verification
        token = create_access_token({"sub": settings.admin_username})
        username = verify_token(token)
        
        if username == settings.admin_username:
            print("✅ Token creation and verification working")
        else:
            print("❌ Token verification failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 FastAPI Setup Test Suite")
    print("=" * 50)
    
    tests = [
        ("Module Imports", test_imports),
        ("Database", test_database),
        ("AI Models", test_ai_models),
        ("Liveness Engine", test_liveness_engine),
        ("Authentication", test_auth)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! FastAPI is ready to run.")
        print("\n📋 Next steps:")
        print("   1. Start FastAPI: uvicorn main:app --host 0.0.0.0 --port 8001 --reload")
        print("   2. Access API docs: http://localhost:8001/docs")
        print("   3. Login with: admin / admin123")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
