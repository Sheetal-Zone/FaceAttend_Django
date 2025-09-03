#!/usr/bin/env python3
"""
Start Face Attendance System with comprehensive verification
Ensures all components are working before starting servers
"""

import os
import sys
import time
import logging
import subprocess
import threading
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SystemVerifier:
    """System verification and startup manager"""
    
    def __init__(self):
        self.verification_passed = False
        self.models_downloaded = False
        
    def verify_dependencies(self):
        """Verify all required dependencies are installed"""
        logger.info("🔍 Verifying dependencies...")
        
        required_packages = [
            'ultralytics',
            'insightface',
            'opencv-python',
            'numpy',
            'torch',
            'fastapi',
            'uvicorn',
            'sqlalchemy'
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                if package == 'opencv-python':
                    import cv2
                elif package == 'torch':
                    import torch
                else:
                    __import__(package)
                logger.info(f"✅ {package}")
            except ImportError:
                missing_packages.append(package)
                logger.error(f"❌ {package} - MISSING")
        
        if missing_packages:
            logger.error(f"Missing packages: {missing_packages}")
            logger.info("Installing missing packages...")
            
            try:
                for package in missing_packages:
                    logger.info(f"Installing {package}...")
                    subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
                    logger.info(f"✅ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install {package}: {e}")
                return False
        
        logger.info("✅ All dependencies verified")
        return True
    
    def download_ai_models(self):
        """Download required AI models"""
        logger.info("🤖 Downloading AI models...")
        
        try:
            # Check if models already exist
            models_dir = Path("models")
            yolo_model = models_dir / "yolov11n.pt"
            
            if yolo_model.exists():
                logger.info("✅ YOLO model already exists")
                self.models_downloaded = True
                return True
            
            # Run model download script
            logger.info("Running model download script...")
            result = subprocess.run([sys.executable, "download_models.py"], 
                                 capture_output=True, text=True, check=True)
            
            logger.info("✅ AI models downloaded successfully")
            self.models_downloaded = True
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download AI models: {e}")
            logger.error(f"Error output: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error downloading AI models: {e}")
            return False
    
    def verify_ai_models(self):
        """Verify AI models are working"""
        logger.info("🧠 Verifying AI models...")
        
        try:
            # Test model initialization
            from app.ai_models import face_recognition_system, liveness_detection_system
            
            logger.info("Initializing face recognition system...")
            face_recognition_system.initialize_models()
            
            logger.info("Initializing liveness detection system...")
            liveness_detection_system.initialize_models()
            
            if not face_recognition_system.initialized:
                logger.error("❌ Face recognition system failed to initialize")
                return False
            
            if not liveness_detection_system.initialized:
                logger.error("❌ Liveness detection system failed to initialize")
                return False
            
            logger.info("✅ AI models verified and working")
            return True
            
        except Exception as e:
            logger.error(f"❌ AI model verification failed: {e}")
            return False
    
    def verify_database(self):
        """Verify database connectivity and tables"""
        logger.info("🗄️ Verifying database...")
        
        try:
            from app.database import create_tables, get_db
            from app.models import Student, LivenessDetectionSession
            
            # Create tables
            create_tables()
            logger.info("Database tables created/verified")
            
            # Test database connection
            db = next(get_db())
            student_count = db.query(Student).count()
            session_count = db.query(LivenessDetectionSession).count()
            
            logger.info(f"Database connection successful")
            logger.info(f"Students: {student_count}, Sessions: {session_count}")
            
            db.close()
            
            logger.info("✅ Database verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database verification failed: {e}")
            return False
    
    def verify_liveness_detection(self):
        """Verify liveness detection engine"""
        logger.info("🔍 Verifying liveness detection engine...")
        
        try:
            from app.liveness_detection import liveness_detection_engine
            
            # Initialize engine
            liveness_detection_engine.initialize_models()
            
            if not liveness_detection_engine.initialized:
                logger.error("❌ Liveness detection engine failed to initialize")
                return False
            
            # Test session creation
            session = liveness_detection_engine.create_session()
            if not session or 'session_id' not in session:
                logger.error("❌ Liveness detection session creation failed")
                return False
            
            logger.info("✅ Liveness detection engine verified")
            return True
            
        except Exception as e:
            logger.error(f"❌ Liveness detection verification failed: {e}")
            return False
    
    def run_comprehensive_verification(self):
        """Run all verification steps"""
        logger.info("🚀 Starting comprehensive system verification...")
        
        # Step 1: Verify dependencies
        if not self.verify_dependencies():
            logger.error("❌ Dependency verification failed")
            return False
        
        # Step 2: Download AI models
        if not self.download_ai_models():
            logger.error("❌ AI model download failed")
            return False
        
        # Step 3: Verify AI models
        if not self.verify_ai_models():
            logger.error("❌ AI model verification failed")
            return False
        
        # Step 4: Verify database
        if not self.verify_database():
            logger.error("❌ Database verification failed")
            return False
        
        # Step 5: Verify liveness detection
        if not self.verify_liveness_detection():
            logger.error("❌ Liveness detection verification failed")
            return False
        
        logger.info("🎉 All verifications passed! System is ready to start.")
        self.verification_passed = True
        return True
    
    def start_servers(self):
        """Start Django and FastAPI servers"""
        if not self.verification_passed:
            logger.error("❌ Cannot start servers - verification failed")
            return False
        
        logger.info("🚀 Starting servers...")
        
        try:
            # Start Django server in background
            logger.info("Starting Django server...")
            django_process = subprocess.Popen(
                [sys.executable, "start_backend.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for Django to start
            time.sleep(5)
            
            # Start FastAPI server in background
            logger.info("Starting FastAPI server...")
            fastapi_process = subprocess.Popen(
                ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            logger.info("🎉 Both servers started successfully!")
            logger.info("📱 Django Web Interface: http://localhost:8000")
            logger.info("🔌 FastAPI API: http://localhost:8001")
            logger.info("📚 FastAPI Docs: http://localhost:8001/docs")
            logger.info("🔑 Admin Login: admin / admin123")
            
            # Keep the script running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down servers...")
                django_process.terminate()
                fastapi_process.terminate()
                logger.info("Servers stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start servers: {e}")
            return False

def main():
    """Main function"""
    verifier = SystemVerifier()
    
    # Run verification
    if verifier.run_comprehensive_verification():
        # Start servers
        verifier.start_servers()
    else:
        logger.error("❌ System verification failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
