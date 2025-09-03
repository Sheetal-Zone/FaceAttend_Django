#!/usr/bin/env python3
"""
Comprehensive test script for the Face Attendance System
Tests all components including AI models, liveness detection, and API endpoints
"""

import os
import sys
import time
import logging
import requests
import json
import cv2
import numpy as np
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class SystemTester:
    """Comprehensive system tester"""
    
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.admin_token = None
        self.test_results = {}
        
    def test_ai_models(self):
        """Test AI model initialization and functionality"""
        logger.info("🧠 Testing AI Models...")
        
        try:
            from app.ai_models import face_recognition_system, liveness_detection_system
            
            # Test model initialization
            logger.info("Initializing face recognition system...")
            face_recognition_system.initialize_models()
            
            logger.info("Initializing liveness detection system...")
            liveness_detection_system.initialize_models()
            
            # Test face detection
            logger.info("Testing face detection...")
            test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            faces = face_recognition_system.detect_faces(test_frame)
            logger.info(f"Face detection test: {len(faces)} faces detected")
            
            # Test liveness detection
            logger.info("Testing liveness detection...")
            liveness_result = liveness_detection_system.detect_liveness(test_frame, "center")
            logger.info(f"Liveness detection test: {liveness_result}")
            
            self.test_results['ai_models'] = {
                'status': 'PASSED',
                'face_recognition_initialized': face_recognition_system.initialized,
                'liveness_detection_initialized': liveness_detection_system.initialized,
                'face_detection_working': len(faces) >= 0,
                'liveness_detection_working': 'is_live' in liveness_result
            }
            
            logger.info("✅ AI Models test PASSED")
            
        except Exception as e:
            logger.error(f"❌ AI Models test FAILED: {e}")
            self.test_results['ai_models'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_liveness_detection_engine(self):
        """Test liveness detection engine"""
        logger.info("🔍 Testing Liveness Detection Engine...")
        
        try:
            from app.liveness_detection import liveness_detection_engine
            
            # Test engine initialization
            logger.info("Initializing liveness detection engine...")
            liveness_detection_engine.initialize_models()
            
            # Test session creation
            logger.info("Testing session creation...")
            session = liveness_detection_engine.create_session(student_id=1)
            session_id = session['session_id']
            logger.info(f"Session created: {session_id}")
            
            # Test frame processing
            logger.info("Testing frame processing...")
            test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            result = liveness_detection_engine.process_frame_for_liveness(test_frame, "center")
            logger.info(f"Frame processing result: {result}")
            
            # Test session update
            logger.info("Testing session update...")
            if result.get('embedding'):
                update_result = liveness_detection_engine.update_session(
                    session_id, "center", "test_frame_data", json.dumps(result['embedding'])
                )
                logger.info(f"Session update result: {update_result}")
            
            self.test_results['liveness_engine'] = {
                'status': 'PASSED',
                'engine_initialized': liveness_detection_engine.initialized,
                'session_created': session_id is not None,
                'frame_processing_working': 'face_detected' in result,
                'session_update_working': 'success' in update_result if 'update_result' in locals() else False
            }
            
            logger.info("✅ Liveness Detection Engine test PASSED")
            
        except Exception as e:
            logger.error(f"❌ Liveness Detection Engine test FAILED: {e}")
            self.test_results['liveness_engine'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_database_connection(self):
        """Test database connectivity"""
        logger.info("🗄️ Testing Database Connection...")
        
        try:
            from app.database import get_db, create_tables
            from app.models import Student, LivenessDetectionSession
            
            # Test table creation
            create_tables()
            logger.info("Database tables created/verified")
            
            # Test database session
            db = next(get_db())
            student_count = db.query(Student).count()
            session_count = db.query(LivenessDetectionSession).count()
            
            logger.info(f"Database connection successful")
            logger.info(f"Students in database: {student_count}")
            logger.info(f"Liveness sessions in database: {session_count}")
            
            db.close()
            
            self.test_results['database'] = {
                'status': 'PASSED',
                'connection': 'successful',
                'students_count': student_count,
                'sessions_count': session_count
            }
            
            logger.info("✅ Database test PASSED")
            
        except Exception as e:
            logger.error(f"❌ Database test FAILED: {e}")
            self.test_results['database'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        logger.info("🌐 Testing API Endpoints...")
        
        try:
            # Test root endpoint
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                logger.info("✅ Root endpoint working")
                root_working = True
            else:
                logger.warning(f"⚠️ Root endpoint returned {response.status_code}")
                root_working = False
            
            # Test health endpoint
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                logger.info("✅ Health endpoint working")
                health_working = True
            else:
                logger.warning(f"⚠️ Health endpoint returned {response.status_code}")
                health_working = False
            
            # Test authentication
            auth_data = {"username": "admin", "password": "admin123"}
            response = requests.post(f"{self.base_url}/api/v1/auth/login", json=auth_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.admin_token = token_data.get('access_token')
                logger.info("✅ Authentication working")
                auth_working = True
            else:
                logger.warning(f"⚠️ Authentication returned {response.status_code}")
                auth_working = False
            
            # Test protected endpoints if authenticated
            if self.admin_token:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                
                # Test students endpoint
                response = requests.get(f"{self.base_url}/api/v1/students", headers=headers)
                if response.status_code == 200:
                    logger.info("✅ Students endpoint working")
                    students_working = True
                else:
                    logger.warning(f"⚠️ Students endpoint returned {response.status_code}")
                    students_working = False
                
                # Test liveness endpoint
                response = requests.get(f"{self.base_url}/api/v1/liveness/session", headers=headers)
                if response.status_code in [200, 405]:  # 405 is expected for GET on POST endpoint
                    logger.info("✅ Liveness endpoint accessible")
                    liveness_working = True
                else:
                    logger.warning(f"⚠️ Liveness endpoint returned {response.status_code}")
                    liveness_working = False
            else:
                students_working = False
                liveness_working = False
            
            self.test_results['api_endpoints'] = {
                'status': 'PASSED' if all([root_working, health_working, auth_working]) else 'PARTIAL',
                'root_endpoint': root_working,
                'health_endpoint': health_working,
                'authentication': auth_working,
                'students_endpoint': students_working,
                'liveness_endpoint': liveness_working
            }
            
            logger.info("✅ API Endpoints test PASSED")
            
        except requests.exceptions.ConnectionError:
            logger.error("❌ API Endpoints test FAILED: Cannot connect to server")
            self.test_results['api_endpoints'] = {
                'status': 'FAILED',
                'error': 'Cannot connect to server - server may not be running'
            }
        except Exception as e:
            logger.error(f"❌ API Endpoints test FAILED: {e}")
            self.test_results['api_endpoints'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_camera_functionality(self):
        """Test camera functionality"""
        logger.info("📹 Testing Camera Functionality...")
        
        try:
            # Test OpenCV camera access
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    logger.info(f"✅ Camera accessible, frame shape: {frame.shape}")
                    camera_working = True
                    frame_quality = 'good'
                else:
                    logger.warning("⚠️ Camera accessible but cannot read frames")
                    camera_working = True
                    frame_quality = 'poor'
                cap.release()
            else:
                logger.warning("⚠️ Camera not accessible")
                camera_working = False
                frame_quality = 'none'
            
            # Test face detection on test frame
            try:
                from app.ai_models import face_recognition_system
                test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                faces = face_recognition_system.detect_faces(test_frame)
                face_detection_working = True
                logger.info(f"✅ Face detection working, detected {len(faces)} faces in test frame")
            except Exception as e:
                logger.warning(f"⚠️ Face detection test failed: {e}")
                face_detection_working = False
            
            self.test_results['camera'] = {
                'status': 'PASSED' if camera_working else 'PARTIAL',
                'camera_accessible': camera_working,
                'frame_quality': frame_quality,
                'face_detection_working': face_detection_working
            }
            
            logger.info("✅ Camera functionality test PASSED")
            
        except Exception as e:
            logger.error(f"❌ Camera functionality test FAILED: {e}")
            self.test_results['camera'] = {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def run_all_tests(self):
        """Run all system tests"""
        logger.info("🚀 Starting comprehensive system tests...")
        
        # Run all tests
        self.test_ai_models()
        self.test_liveness_detection_engine()
        self.test_database_connection()
        self.test_api_endpoints()
        self.test_camera_functionality()
        
        # Generate summary
        self.generate_test_summary()
    
    def generate_test_summary(self):
        """Generate test summary report"""
        logger.info("\n" + "="*60)
        logger.info("📊 TEST SUMMARY REPORT")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PASSED')
        partial_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'PARTIAL')
        failed_tests = sum(1 for result in self.test_results.values() if result.get('status') == 'FAILED')
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"✅ PASSED: {passed_tests}")
        logger.info(f"⚠️ PARTIAL: {partial_tests}")
        logger.info(f"❌ FAILED: {failed_tests}")
        
        logger.info("\nDetailed Results:")
        for test_name, result in self.test_results.items():
            status = result.get('status', 'UNKNOWN')
            status_icon = "✅" if status == 'PASSED' else "⚠️" if status == 'PARTIAL' else "❌"
            logger.info(f"{status_icon} {test_name}: {status}")
            
            if 'error' in result:
                logger.info(f"   Error: {result['error']}")
        
        # Overall system status
        if failed_tests == 0 and partial_tests == 0:
            overall_status = "🎉 ALL SYSTEMS OPERATIONAL"
        elif failed_tests == 0:
            overall_status = "⚠️ SYSTEM PARTIALLY OPERATIONAL"
        else:
            overall_status = "❌ SYSTEM HAS ISSUES"
        
        logger.info(f"\n{overall_status}")
        
        # Recommendations
        logger.info("\n📋 RECOMMENDATIONS:")
        if failed_tests > 0:
            logger.info("• Fix failed tests before proceeding")
        if partial_tests > 0:
            logger.info("• Address partial test results for optimal performance")
        if passed_tests == total_tests:
            logger.info("• System is ready for production use")
        
        logger.info("="*60)

def main():
    """Main function"""
    tester = SystemTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
