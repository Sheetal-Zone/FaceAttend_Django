import cv2
import numpy as np
import time
import threading
from typing import Optional, Callable, Dict
from app.ai_models import face_recognition_system
from app.database import SessionLocal
from app.models import Student, AttendanceLog, DetectionLog
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
            # Open camera stream with reconnect logic
            open_attempts = 0
            self.cap = cv2.VideoCapture(self.camera_url)
            while not self.cap.isOpened() and open_attempts < 5 and self.is_running:
                logger.warning(f"Failed to open camera stream: {self.camera_url}. Retrying ({open_attempts+1}/5)...")
                time.sleep(1.0)
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = cv2.VideoCapture(self.camera_url)
                open_attempts += 1
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera stream after retries: {self.camera_url}")
                return
            
            logger.info(f"Successfully opened camera stream: {self.camera_url}")
            
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FPS, 10)  # Limit to 10 FPS for processing
            
            while self.is_running:
                try:
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        logger.warning(f"Failed to read frame from camera {self.camera_url}")
                        # attempt to reconnect non-intrusively
                        try:
                            self.cap.release()
                        except Exception:
                            pass
                        self.cap = cv2.VideoCapture(self.camera_url)
                        if not self.cap.isOpened():
                            logger.error(f"Camera {self.camera_url} disconnected. Attempting periodic reconnects while keeping loop alive.")
                            reconnect_attempts = 0
                            while self.is_running and reconnect_attempts < 10 and not self.cap.isOpened():
                                time.sleep(1.0)
                                self.cap = cv2.VideoCapture(self.camera_url)
                                reconnect_attempts += 1
                            if not self.cap.isOpened():
                                time.sleep(2.0)
                                continue
                        time.sleep(0.1)
                        continue
                    
                    self.frame_count += 1
                    
                    # Process frame for face detection using real AI models
                    results = self._process_frame_real(frame)
                    
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
    
    def _process_frame_simplified(self, frame: np.ndarray) -> Dict:
        """Simplified frame processing using OpenCV-based AI models"""
        start_time = time.time()
        
        try:
            # Detect faces using real AI models
            face_boxes = face_recognition_system.detect_faces(frame)
            recognized_students = []
            
            # Process each detected face
            for (x1, y1, x2, y2) in face_boxes:
                # Extract face region
                face_img = frame[y1:y2, x1:x2]
                
                # Recognize face using real AI models
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
            
            # Only mark attendance once per minute window globally; still ensure per-student dedupe below
            if current_time - self.last_processing_time < 60:
                return
            
            for student_data in recognized_students:
                student_id = student_data['student_id']
                confidence = student_data['confidence']
                
                # Only mark attendance if confidence > 0.7
                if confidence > 0.7:
                    # Check if attendance already marked for today
                    from sqlalchemy import func
                    from datetime import date
                    today = date.today()
                    # Prevent duplicate per day per student
                    existing_attendance = db.query(Attendance).filter(
                        Attendance.student_id == student_id,
                        func.date(Attendance.timestamp) == today
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
                        logger.info(f"Attendance marked for student {student_id} with confidence {confidence:.3f} at {self.camera_location}")
                    else:
                        logger.info(f"Attendance already marked for student {student_id} today")
                else:
                    logger.info(f"Confidence {confidence:.3f} too low for student {student_id}, skipping attendance")
            
            db.commit()
            logger.info("Attendance commit completed for recognized students batch")
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


class LaptopCameraProcessor:
    """Processor for laptop built-in camera streams"""
    
    def __init__(self, camera_index: int = 0, camera_location: str = "Laptop Camera"):
        """Initialize laptop camera processor"""
        self.camera_index = camera_index
        self.camera_location = camera_location
        self.cap = None
        self.is_running = False
        self.thread = None
        self.callback = None
        self.frame_count = 0
        self.last_processing_time = time.time()
        self.available_cameras = self._get_available_cameras()
        self.mock_mode = len(self.available_cameras) == 0  # Use mock mode if no cameras available
        
    def _get_available_cameras(self) -> list:
        """Get list of available camera indices"""
        available = []
        for i in range(5):  # Check first 5 camera indices
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available.append(i)
                cap.release()
            except:
                pass
        logger.info(f"Available camera indices: {available}")
        return available
    
    def _create_mock_frame(self) -> np.ndarray:
        """Create a mock frame for testing when no camera is available"""
        # Create a 640x480 mock frame with some visual elements
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add some visual elements to simulate a camera feed
        cv2.rectangle(frame, (200, 150), (440, 330), (255, 255, 255), 2)
        cv2.putText(frame, "Mock Camera", (250, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, "No Physical Camera", (220, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(frame, "Available", (280, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        return frame
    
    def get_camera_info(self) -> Dict:
        """Get information about available cameras"""
        return {
            'available_cameras': self.available_cameras,
            'current_camera': self.camera_index,
            'camera_location': self.camera_location,
            'status': 'running' if self.is_running else 'stopped',
            'mock_mode': self.mock_mode
        }
    
    def switch_camera(self, camera_index: int) -> bool:
        """Switch to a different camera index"""
        if self.mock_mode:
            # In mock mode, just update the index
            self.camera_index = camera_index
            logger.info(f"Mock camera switched to index: {camera_index}")
            return True
        
        if camera_index in self.available_cameras:
            if self.is_running:
                self.stop()
            self.camera_index = camera_index
            if self.is_running:
                self.start(self.callback)
            logger.info(f"Switched to camera index: {camera_index}")
            return True
        else:
            logger.error(f"Camera index {camera_index} not available")
            return False
    
    def start(self, callback: Optional[Callable] = None):
        """Start processing laptop camera stream"""
        if self.is_running:
            logger.warning(f"Laptop camera {self.camera_index} is already running")
            return
        
        self.callback = callback
        self.is_running = True
        self.thread = threading.Thread(target=self._process_stream)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Started processing laptop camera stream: {self.camera_index} (Mock mode: {self.mock_mode})")
    
    def stop(self):
        """Stop processing laptop camera stream"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"Stopped processing laptop camera stream: {self.camera_index}")
    
    def _process_stream(self):
        """Main processing loop for laptop camera stream"""
        try:
            if self.mock_mode:
                self._process_mock_stream()
            else:
                self._process_physical_stream()
        except Exception as e:
            logger.error(f"Error in laptop camera processing thread for {self.camera_index}: {e}")
        finally:
            if self.cap:
                self.cap.release()
            self.is_running = False
    
    def _process_physical_stream(self):
        """Process physical camera stream"""
        # Open laptop camera with retries; fall back to mock if unavailable
        open_attempts = 0
        while open_attempts < 3 and not self.is_running:
            # If stopped during attempts
            return
        
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            logger.warning(f"Initial open failed for laptop camera {self.camera_index}, retrying...")
            open_attempts = 1
            while open_attempts < 3 and not self.cap.isOpened():
                time.sleep(0.5)
                self.cap.release()
                self.cap = cv2.VideoCapture(self.camera_index)
                open_attempts += 1
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open laptop camera after retries: {self.camera_index}. Switching to mock mode.")
            self.mock_mode = True
            self._process_mock_stream()
            return
        
        logger.info(f"Successfully opened laptop camera: {self.camera_index}")
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FPS, 15)  # Higher FPS for laptop camera
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        consecutive_failures = 0
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= 10:
                        logger.warning(f"Repeated frame read failures from laptop camera {self.camera_index}. Attempting to reopen.")
                        try:
                            self.cap.release()
                        except Exception:
                            pass
                        self.cap = cv2.VideoCapture(self.camera_index)
                        if not self.cap.isOpened():
                            logger.error(f"Reopen failed. Switching to mock mode to keep feed alive.")
                            self.mock_mode = True
                            self._process_mock_stream()
                            return
                        consecutive_failures = 0
                    else:
                        logger.warning(f"Failed to read frame from laptop camera {self.camera_index}")
                        time.sleep(0.1)
                        continue
                
                consecutive_failures = 0
                self.frame_count += 1
                
                # Process frame for face detection using simplified AI models
                results = self._process_frame_simplified(frame)
                
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
                logger.error(f"Error processing frame from laptop camera {self.camera_index}: {e}")
                time.sleep(0.1)
    
    def _process_mock_stream(self):
        """Process mock camera stream for testing"""
        logger.info("Processing mock camera stream")
        
        while self.is_running:
            try:
                # Create mock frame
                frame = self._create_mock_frame()
                
                self.frame_count += 1
                
                # Process frame for face detection using simplified AI models
                results = self._process_frame_simplified(frame)
                
                # Log detection results
                self._log_detection(results)
                
                # Mark attendance for recognized students
                self._mark_attendance(results.get('recognized_students', []))
                
                # Call callback if provided
                if self.callback:
                    self.callback(results)
                
                # Simulate camera frame rate
                time.sleep(0.067)  # ~15 FPS
                
            except Exception as e:
                logger.error(f"Error processing mock frame: {e}")
                time.sleep(0.1)
    
    def _process_frame_real(self, frame: np.ndarray) -> Dict:
        """Real frame processing using AI models"""
        start_time = time.time()
        
        try:
            # Detect faces using real AI models
            face_boxes = face_recognition_system.detect_faces(frame)
            recognized_students = []
            
            # Process each detected face
            for (x1, y1, x2, y2) in face_boxes:
                # Extract face region
                face_img = frame[y1:y2, x1:x2]
                
                # Recognize face using real AI models
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
                'processing_time': processing_time,
                'camera_type': 'laptop',
                'mock_mode': self.mock_mode
            }
            
        except Exception as e:
            logger.error(f"Error processing laptop camera frame: {e}")
            return {
                'faces_detected': 0,
                'students_recognized': 0,
                'recognized_students': [],
                'processing_time': time.time() - start_time,
                'error': str(e),
                'camera_type': 'laptop',
                'mock_mode': self.mock_mode
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
            logger.error(f"Error logging laptop camera detection: {e}")
    
    def _mark_attendance(self, recognized_students: list):
        """Mark attendance for recognized students from laptop camera"""
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
                
                # Only mark attendance if confidence > 0.7
                if confidence > 0.7:
                    # Check if attendance already marked for today
                    from sqlalchemy import func
                    from datetime import date
                    today = date.today()
                    existing_attendance = db.query(Attendance).filter(
                        Attendance.student_id == student_id,
                        func.date(Attendance.timestamp) == today
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
                        logger.info(f"Laptop camera: Attendance marked for student {student_id} with confidence {confidence:.3f}")
                    else:
                        logger.info(f"Laptop camera: Attendance already marked for student {student_id} today")
                else:
                    logger.info(f"Laptop camera: Confidence {confidence:.3f} too low for student {student_id}, skipping attendance")
                    logger.info(f"Marked attendance for student {student_id} via laptop camera")
            
            db.commit()
            self.last_processing_time = current_time
            db.close()
            
        except Exception as e:
            logger.error(f"Error marking attendance from laptop camera: {e}")
    
    def get_frame(self) -> Optional[np.ndarray]:
        """Get current frame from laptop camera"""
        if self.mock_mode:
            return self._create_mock_frame()
        
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                return frame
        return None
