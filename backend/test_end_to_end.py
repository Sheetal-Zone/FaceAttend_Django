#!/usr/bin/env python3
"""
End-to-End Test Script for Face Attendance System
"""

import requests
import json
import time
import base64
import numpy as np
import cv2
from datetime import datetime

# Configuration
FASTAPI_BASE_URL = "http://localhost:8001"
AUTH_TOKEN = "admin_token_placeholder"

def test_health_endpoints():
    """Test health and readiness endpoints"""
    print("🔍 Testing health endpoints...")
    
    # Test /health
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print("✅ /health endpoint working")
    except Exception as e:
        print(f"❌ /health endpoint failed: {e}")
        return False
    
    # Test /ready
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/ready", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] == True
        print("✅ /ready endpoint working")
    except Exception as e:
        print(f"❌ /ready endpoint failed: {e}")
        return False
    
    return True

def test_models_endpoint():
    """Test models endpoint"""
    print("🔍 Testing models endpoint...")
    
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/api/v1/models", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "face_detection" in data
        assert "face_recognition" in data
        assert "liveness_detection" in data
        print("✅ /api/v1/models endpoint working")
        return True
    except Exception as e:
        print(f"❌ /api/v1/models endpoint failed: {e}")
        return False

def create_test_student():
    """Create a test student"""
    print("🔍 Creating test student...")
    
    try:
        student_data = {
            "name": "Test Student",
            "roll_no": "TEST001",
            "branch": "CSE",
            "year": 3
        }
        
        response = requests.post(
            f"{FASTAPI_BASE_URL}/api/v1/students/",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}"
            },
            json=student_data,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        student_id = data["data"]["student_id"]
        print(f"✅ Test student created with ID: {student_id}")
        return student_id
    except Exception as e:
        print(f"❌ Failed to create test student: {e}")
        return None

def create_test_image():
    """Create a test image with a simple pattern"""
    # Create a simple test image
    img = np.ones((480, 640, 3), dtype=np.uint8) * 128  # Gray background
    cv2.rectangle(img, (200, 150), (400, 350), (0, 255, 0), 2)  # Green rectangle
    cv2.putText(img, "TEST FACE", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Encode as base64
    _, buffer = cv2.imencode('.jpg', img)
    img_base64 = base64.b64encode(buffer).decode('utf-8')
    return img_base64

def test_liveness_flow(student_id):
    """Test liveness detection flow"""
    print("🔍 Testing liveness detection flow...")
    
    try:
        # 1. Create liveness session
        response = requests.post(
            f"{FASTAPI_BASE_URL}/api/v1/liveness/session",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}"
            },
            json={},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        session_id = data["data"]["session_id"]
        print(f"✅ Liveness session created: {session_id}")
        
        # 2. Process frames for each position
        positions = ["center", "left", "right"]
        test_image = create_test_image()
        
        for position in positions:
            print(f"  Processing {position} position...")
            
            response = requests.post(
                f"{FASTAPI_BASE_URL}/api/v1/liveness/frames",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {AUTH_TOKEN}"
                },
                json={
                    "session_id": session_id,
                    "position": position,
                    "frame_data": test_image
                },
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            print(f"    Response: {data['message']}")
        
        # 3. Complete liveness detection
        response = requests.post(
            f"{FASTAPI_BASE_URL}/api/v1/liveness/complete",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}"
            },
            json={
                "session_id": session_id,
                "student_id": student_id
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✅ Liveness detection completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Liveness detection failed: {e}")
        return False

def test_detection_flow():
    """Test live detection flow"""
    print("🔍 Testing live detection flow...")
    
    try:
        # 1. Start detection session
        response = requests.post(
            f"{FASTAPI_BASE_URL}/api/v1/detection/start",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}"
            },
            json={"camera_source": "test"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        session_id = data["session_id"]
        print(f"✅ Detection session started: {session_id}")
        
        # 2. Process test frame
        test_image = create_test_image()
        
        response = requests.post(
            f"{FASTAPI_BASE_URL}/api/v1/detection/frame",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}"
            },
            json={
                "image_data": test_image,
                "session_id": session_id
            },
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✅ Frame processed: {data['message']}")
        
        # 3. Stop detection session
        response = requests.post(
            f"{FASTAPI_BASE_URL}/api/v1/detection/stop",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AUTH_TOKEN}"
            },
            json={"session_id": session_id},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✅ Detection session stopped successfully")
        return True
        
    except Exception as e:
        print(f"❌ Detection flow failed: {e}")
        return False

def test_metrics():
    """Test metrics endpoint"""
    print("🔍 Testing metrics endpoint...")
    
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/metrics", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "embeddings_count" in data
        assert "students_count" in data
        assert "attendance_logs_count" in data
        print("✅ Metrics endpoint working")
        print(f"  Students: {data['students_count']}")
        print(f"  Embeddings: {data['embeddings_count']}")
        print(f"  Attendance logs: {data['attendance_logs_count']}")
        return True
    except Exception as e:
        print(f"❌ Metrics endpoint failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting End-to-End Tests for Face Attendance System")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 6
    
    # Test 1: Health endpoints
    if test_health_endpoints():
        tests_passed += 1
    
    # Test 2: Models endpoint
    if test_models_endpoint():
        tests_passed += 1
    
    # Test 3: Create test student
    student_id = create_test_student()
    if student_id:
        tests_passed += 1
        
        # Test 4: Liveness flow
        if test_liveness_flow(student_id):
            tests_passed += 1
    
    # Test 5: Detection flow
    if test_detection_flow():
        tests_passed += 1
    
    # Test 6: Metrics
    if test_metrics():
        tests_passed += 1
    
    print("=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! System is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the system.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
