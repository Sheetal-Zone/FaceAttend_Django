"""
Camera stream processor for handling RTSP/HTTP camera feeds.
"""

import cv2
import time
import threading
import logging
from typing import Optional, Callable
from django.conf import settings
from .models import CameraStream
from .face_detection import FaceDetectionService

logger = logging.getLogger(__name__)


class CameraProcessor:
    """Process camera streams for face detection."""
    
    def __init__(self, camera_stream: CameraStream, callback: Optional[Callable] = None):
        self.camera_stream = camera_stream
        self.callback = callback
        self.is_running = False
        self.cap = None
        self.face_detection_service = FaceDetectionService(camera_stream)
        self.thread = None
        
    def start(self):
        """Start processing the camera stream."""
        if self.is_running:
            logger.warning(f"Camera {self.camera_stream.name} is already running")
            return
        
        self.is_running = True
        self.thread = threading.Thread(target=self._process_stream)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Started processing camera stream: {self.camera_stream.name}")
    
    def stop(self):
        """Stop processing the camera stream."""
        self.is_running = False
        if self.cap:
            self.cap.release()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"Stopped processing camera stream: {self.camera_stream.name}")
    
    def _process_stream(self):
        """Main processing loop for the camera stream."""
        try:
            # Try to open the camera stream
            if self.camera_stream.rtsp_url:
                self.cap = cv2.VideoCapture(self.camera_stream.rtsp_url)
            elif self.camera_stream.http_url:
                self.cap = cv2.VideoCapture(self.camera_stream.http_url)
            else:
                logger.error(f"No valid URL for camera {self.camera_stream.name}")
                return
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera stream: {self.camera_stream.rtsp_url or self.camera_stream.http_url}")
                return
            
            logger.info(f"Successfully opened camera stream: {self.camera_stream.name}")
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 10)  # Limit to 10 FPS for processing
            
            frame_count = 0
            last_fps_time = time.time()
            
            while self.is_running:
                try:
                    ret, frame = self.cap.read()
                    if not ret:
                        logger.warning(f"Failed to read frame from camera {self.camera_stream.name}")
                        time.sleep(0.1)
                        continue
                    
                    frame_count += 1
                    
                    # Process frame for face detection
                    results = self.face_detection_service.process_frame(frame)
                    
                    # Draw results on frame
                    processed_frame = self.face_detection_service.draw_results_on_frame(frame, results)
                    
                    # Call callback if provided
                    if self.callback:
                        self.callback(processed_frame, results)
                    
                    # Calculate and log FPS
                    if frame_count % 30 == 0:
                        current_time = time.time()
                        fps = 30 / (current_time - last_fps_time)
                        logger.debug(f"Camera {self.camera_stream.name} FPS: {fps:.1f}")
                        last_fps_time = current_time
                    
                    # Small delay to prevent overwhelming the system
                    time.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"Error processing frame from camera {self.camera_stream.name}: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error in camera processing thread for {self.camera_stream.name}: {e}")
        finally:
            if self.cap:
                self.cap.release()
            self.is_running = False


class CameraManager:
    """Manages multiple camera streams."""
    
    def __init__(self):
        self.cameras = {}
        self.is_running = False
    
    def start_all_cameras(self):
        """Start processing all active camera streams."""
        if self.is_running:
            logger.warning("Camera manager is already running")
            return
        
        try:
            active_cameras = CameraStream.objects.filter(is_active=True)
            
            for camera in active_cameras:
                if camera.id not in self.cameras:
                    processor = CameraProcessor(camera)
                    self.cameras[camera.id] = processor
                    processor.start()
            
            self.is_running = True
            logger.info(f"Started {len(self.cameras)} camera streams")
            
        except Exception as e:
            logger.error(f"Error starting cameras: {e}")
    
    def stop_all_cameras(self):
        """Stop processing all camera streams."""
        for camera_id, processor in self.cameras.items():
            processor.stop()
        
        self.cameras.clear()
        self.is_running = False
        logger.info("Stopped all camera streams")
    
    def add_camera(self, camera: CameraStream):
        """Add a new camera stream."""
        if camera.id not in self.cameras and camera.is_active:
            processor = CameraProcessor(camera)
            self.cameras[camera.id] = processor
            if self.is_running:
                processor.start()
            logger.info(f"Added camera stream: {camera.name}")
    
    def remove_camera(self, camera_id: int):
        """Remove a camera stream."""
        if camera_id in self.cameras:
            processor = self.cameras[camera_id]
            processor.stop()
            del self.cameras[camera_id]
            logger.info(f"Removed camera stream: {camera_id}")
    
    def reload_cameras(self):
        """Reload camera streams from database."""
        try:
            # Stop all current cameras
            self.stop_all_cameras()
            
            # Start all active cameras
            self.start_all_cameras()
            
            logger.info("Reloaded all camera streams")
            
        except Exception as e:
            logger.error(f"Error reloading cameras: {e}")
    
    def get_camera_status(self) -> dict:
        """Get status of all camera streams."""
        status = {}
        for camera_id, processor in self.cameras.items():
            status[camera_id] = {
                'is_running': processor.is_running,
                'camera_name': processor.camera_stream.name,
                'camera_location': processor.camera_stream.location,
            }
        return status


# Global camera manager instance
camera_manager = CameraManager()
