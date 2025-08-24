import cv2
import numpy as np
import time
import threading
from typing import Optional, Callable, Dict
from app.ai_models import face_recognition_system
from app.database import SessionLocal
from app.models import Student, Attendance, DetectionLog
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class CameraProcessor:
    def __init__(self, camera_url: str, camera_location: str = "Unknown"):
        """Initialize camera processor"""
        self.camera_url = camera_url
        self.camera_location = camera_location
        self.cap = None
        self.is_running = False
        self.thread = None
        self.callback = None
        self.frame_count = 0
        self.last_processing_time = time.time()
        
    def start(self, callback: Optional[Callable] = None):
        """Start processing camera stream"""
        if self.is_running:
            logger.warning(f"Camera {self.camera_url} is already running")
            return
        
        self.callback = callback
        self.is_running = True
        self.thread = threading.Thread(target=self._process_stream)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Started processing camera stream: {self.camera_url}")
    
    def stop(self):
        """Stop processing camera stream"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"Stopped processing camera stream: {self.camera_url}")
    
    def _process_stream(self):
        """Main processing loop for camera stream"""
        try:
            # Open camera stream
            self.cap = cv2.VideoCapture(self.camera_url)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera stream: {self.camera_url}")
                return
            
            logger.info(f"Successfully opened camera stream: {self.camera_url}")
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 10)  # Limit to 10 FPS for processing
            
            while self.is_running:
                try:
                    ret, frame = self.cap.read()
                    if not ret:
                        logger.warning(f"Failed to read frame from camera {self.camera_url}")
                        time.sleep(0.1)
                        continue
                    
                    self.frame_count += 1
                    
                    # Process frame for face detection using mock AI models
                    results = self._process_frame_mock(frame)
                    
                    # Log detection results
                    self._log_detection(results)
                    
                    # Mark attendance for recognized students
                    self._mark_attendance(results.get('recognized_students', []))
                    
                    # Call callback if provided
                    if self.callback:
                        self.callback(results)
                    
                    # Small delay to prevent overwhelming the system
                    time.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"Error processing frame from camera {self.camera_url}: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"Error in camera processing thread for {self.camera_url}: {e}")
        finally:
            if self.cap:
                self.cap.release()
            self.is_running = False
    
    def _process_frame_mock(self, frame: np.ndarray) -> Dict:
        """Mock frame processing for development/testing"""
        start_time = time.time()
        
        try:
            # Detect faces using mock AI models
            face_boxes = face_recognition_system.detect_faces(frame)
            recognized_students = []
            
            # Process each detected face
            for (x1, y1, x2, y2) in face_boxes:
                # Extract face region
                face_img = frame[y1:y2, x1:x2]
                
                # Recognize face using mock AI models
                recognition_result = face_recognition_system.recognize_face(face_img)
                if recognition_result:
                    recognized_students.append({
                        'student_id': recognition_result['student_id'],
                        'confidence': recognition_result['confidence'],
                        'bbox': (x1, y1, x2, y2)
                    })
            
            processing_time = time.time() - start_time
            
            return {
                'faces_detected': len(face_boxes),
                'students_recognized': len(recognized_students),
                'recognized_students': recognized_students,
                'processing_time': processing_time
            }
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {
                'faces_detected': 0,
                'students_recognized': 0,
                'recognized_students': [],
                'processing_time': time.time() - start_time,
                'error': str(e)
            }
    
    def _log_detection(self, results: Dict):
        """Log detection results to database"""
        try:
            db = SessionLocal()
            detection_log = DetectionLog(
                faces_detected=results.get('faces_detected', 0),
                students_recognized=results.get('students_recognized', 0),
                processing_time=results.get('processing_time'),
                camera_location=self.camera_location,
                error_message=results.get('error')
            )
            db.add(detection_log)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Error logging detection: {e}")
    
    def _mark_attendance(self, recognized_students: list):
        """Mark attendance for recognized students"""
        if not recognized_students:
            return
        
        try:
            db = SessionLocal()
            current_time = time.time()
            
            # Only mark attendance once per minute per student
            if current_time - self.last_processing_time < 60:
                return
            
            for student_data in recognized_students:
                student_id = student_data['student_id']
                confidence = student_data['confidence']
                
                # Check if attendance already marked for today
                today = time.strftime('%Y-%m-%d')
                existing_attendance = db.query(Attendance).filter(
                    Attendance.student_id == student_id,
                    Attendance.timestamp >= today
                ).first()
                
                if not existing_attendance:
                    # Mark new attendance
                    attendance = Attendance(
                        student_id=student_id,
                        status="Present",
                        confidence_score=confidence,
                        camera_location=self.camera_location
                    )
                    db.add(attendance)
                    logger.info(f"Marked attendance for student {student_id}")
            
            db.commit()
            self.last_processing_time = current_time
            db.close()
            
        except Exception as e:
            logger.error(f"Error marking attendance: {e}")


class CameraManager:
    def __init__(self):
        """Initialize camera manager"""
        self.cameras = {}
        self.is_running = False
    
    def start_camera(self, camera_url: str, camera_location: str = "Unknown", callback: Optional[Callable] = None):
        """Start a camera stream"""
        if camera_url in self.cameras:
            logger.warning(f"Camera {camera_url} is already running")
            return
        
        processor = CameraProcessor(camera_url, camera_location)
        self.cameras[camera_url] = processor
        processor.start(callback)
        logger.info(f"Started camera: {camera_url}")
    
    def stop_camera(self, camera_url: str):
        """Stop a camera stream"""
        if camera_url in self.cameras:
            processor = self.cameras[camera_url]
            processor.stop()
            del self.cameras[camera_url]
            logger.info(f"Stopped camera: {camera_url}")
    
    def stop_all_cameras(self):
        """Stop all camera streams"""
        for camera_url in list(self.cameras.keys()):
            self.stop_camera(camera_url)
        logger.info("Stopped all camera streams")
    
    def get_camera_status(self) -> Dict:
        """Get status of all camera streams"""
        status = {}
        for camera_url, processor in self.cameras.items():
            status[camera_url] = {
                'is_running': processor.is_running,
                'camera_location': processor.camera_location,
                'frame_count': processor.frame_count
            }
        return status


# Global camera manager instance
camera_manager = CameraManager()
