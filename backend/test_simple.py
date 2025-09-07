#!/usr/bin/env python3
"""
Simple Test Script
Tests basic functionality without starting servers
"""

import sys
import os
from pathlib import Path

def test_basic_functionality():
    """Test basic functionality"""
    print("🧪 Testing Basic Functionality")
    print("=" * 40)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from app.database import create_tables, engine
        from app.models import Student, LivenessDetectionSession, AttendanceLog
        from app.auth import authenticate_admin, create_access_token
        from app.config import settings
        print("✅ All imports successful")
        
        # Test database
        print("2. Testing database...")
        create_tables()
        print("✅ Database tables created")
        
        # Test authentication
        print("3. Testing authentication...")
        if authenticate_admin(settings.admin_username, settings.admin_password):
            print("✅ Admin authentication working")
        else:
            print("❌ Admin authentication failed")
            return False
        
        # Test token creation
        token = create_access_token({"sub": settings.admin_username})
        print(f"✅ Token created: {token[:20]}...")
        
        print("\n🎉 Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
