#!/usr/bin/env python3
"""
Standalone script to start the face detection system.
This script can be run independently of Django for testing or development.
"""

import os
import sys
import time
import signal
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'face_attendance.settings')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / 'logs' / 'detection.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to start the detection system."""
    try:
        # Import Django and initialize
        import django
        django.setup()
        
        logger.info("Django initialized successfully")
        
        # Import our detection modules
        from attendance.camera_processor import camera_manager
        from attendance.models import CameraStream
        
        logger.info("Starting face detection system...")
        
        # Check for active camera streams
        active_cameras = CameraStream.objects.filter(is_active=True)
        if not active_cameras:
            logger.warning("No active camera streams found. Please add cameras via Django admin.")
            return
        
        logger.info(f"Found {active_cameras.count()} active camera streams")
        
        # Start camera processing
        camera_manager.start_all_cameras()
        
        logger.info("Face detection system started successfully")
        logger.info("Press Ctrl+C to stop...")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(1)
                
                # Log status every 30 seconds
                if int(time.time()) % 30 == 0:
                    status = camera_manager.get_camera_status()
                    active_count = len([c for c in status.values() if c['is_running']])
                    logger.info(f"Status: {active_count}/{len(status)} cameras active")
                    
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure all dependencies are installed and Django is properly configured")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        try:
            # Stop all cameras
            camera_manager.stop_all_cameras()
            logger.info("Face detection system stopped")
        except:
            pass

def signal_handler(signum, frame):
    """Handle system signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

if __name__ == "__main__":
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create logs directory if it doesn't exist
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Run main function
    main()
