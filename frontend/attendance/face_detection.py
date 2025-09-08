"""
Face detection and recognition service using YOLOv11 and face_recognition library.
"""

import cv2
import numpy as np
import face_recognition
import time
import logging
from typing import List, Tuple, Optional, Dict
from django.conf import settings
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from .models import Student, Attendance, DetectionLog, CameraStream

logger = logging.getLogger(__name__)


class FaceDetectionService:
    """Service for face detection and recognition using YOLOv11."""
    
    def __init__(self, camera_stream: CameraStream = None):
        self.camera_stream = camera_stream
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_students = []
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.process_this_frame = True
        self.frame_count = 0
        
        # Load YOLO model
        try:
            from ultralytics import YOLO
            self.yolo_model = YOLO(settings.YOLO_MODEL_PATH)
            logger.info(f"YOLO model loaded from {settings.YOLO_MODEL_PATH}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.yolo_model = None
        
        # Load known faces
        self._load_known_faces()
        
        # Channel layer for WebSocket updates
        self.channel_layer = get_channel_layer()
    
    def _load_known_faces(self):
        """Load known face encodings from registered students."""
        try:
            students = Student.objects.filter(is_active=True)
            self.known_face_encodings = []
            self.known_face_names = []
            self.known_face_students = []
            
            for student in students:
                face_encoding = student.get_face_encoding()
                if face_encoding is not None:
                    self.known_face_encodings.append(face_encoding)
                    self.known_face_names.append(f"{student.name} ({student.roll_number})")
                    self.known_face_students.append(student)
                    logger.info(f"Loaded face encoding for {student.name}")
            
            logger.info(f"Loaded {len(self.known_face_encodings)} known faces")
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
    
    def reload_known_faces(self):
        """Reload known faces from database."""
        self._load_known_faces()
    
    def detect_faces_yolo(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces using YOLOv11."""
        if self.yolo_model is None:
            return []
        
        try:
            # Run YOLO inference
            results = self.yolo_model(frame, verbose=False)
            
            face_locations = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        
                        # Convert to face_recognition format (top, right, bottom, left)
                        top, right, bottom, left = y1, x2, y2, x1
                        face_locations.append((top, right, bottom, left))
            
            return face_locations
            
        except Exception as e:
            logger.error(f"Error in YOLO face detection: {e}")
            return []
    
    def recognize_faces(self, frame: np.ndarray, face_locations: List[Tuple[int, int, int, int]]) -> Tuple[List[str], List[float]]:
        """Recognize faces using face_recognition library."""
        face_names = []
        confidence_scores = []
        
        if not face_locations:
            return face_names, confidence_scores
        
        try:
            # Get face encodings for the current frame
            face_encodings = face_recognition.face_encodings(frame, face_locations)
            
            for face_encoding in face_encodings:
                # Compare with known faces
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding, 
                    tolerance=settings.FACE_RECOGNITION_TOLERANCE
                )
                
                name = "Unknown"
                confidence = 0.0
                
                if True in matches:
                    # Find the best match
                    face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    
                    if matches[best_match_index]:
                        name = self.known_face_names[best_match_index]
                        confidence = 1.0 - face_distances[best_match_index]
                        
                        # Mark attendance for recognized student
                        self._mark_attendance(self.known_face_students[best_match_index], confidence)
                
                face_names.append(name)
                confidence_scores.append(confidence)
            
            return face_names, confidence_scores
            
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            return [], []
    
    def _mark_attendance(self, student: Student, confidence_score: float):
        """Mark attendance for a recognized student."""
        try:
            attendance = Attendance.mark_attendance(
                student=student,
                confidence_score=confidence_score,
                camera_location=self.camera_stream.location if self.camera_stream else None
            )
            
            # Send WebSocket update
            async_to_sync(self.channel_layer.group_send)(
                "detection_updates",
                {
                    "type": "attendance_marked",
                    "student_name": student.name,
                    "student_roll": student.roll_number,
                    "timestamp": timezone.now().isoformat(),
                    "confidence_score": confidence_score,
                }
            )
            
            logger.info(f"Attendance marked for {student.name} with confidence {confidence_score:.2f}")
            
        except Exception as e:
            logger.error(f"Error marking attendance for {student.name}: {e}")
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """Process a single frame for face detection and recognition."""
        start_time = time.time()
        
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = small_frame[:, :, ::-1]
        
        # Only process every other frame to save time
        if self.process_this_frame:
            # Detect faces using YOLOv11
            face_locations = self.detect_faces_yolo(rgb_small_frame)
            
            # Recognize faces
            face_names, confidence_scores = self.recognize_faces(rgb_small_frame, face_locations)
            
            # Scale back up face locations
            self.face_locations = [(top * 4, right * 4, bottom * 4, left * 4) for top, right, bottom, left in face_locations]
            self.face_names = face_names
            
            self.process_this_frame = False
            self.frame_count = 0
        else:
            self.frame_count += 1
            if self.frame_count >= 2:
                self.process_this_frame = True
        
        processing_time = time.time() - start_time
        
        # Log detection
        self._log_detection(len(self.face_locations), len([n for n in self.face_names if n != "Unknown"]), processing_time)
        
        # Send WebSocket update
        self._send_detection_update(len(self.face_locations), len([n for n in self.face_names if n != "Unknown"]))
        
        return {
            'face_locations': self.face_locations,
            'face_names': self.face_names,
            'processing_time': processing_time,
            'faces_detected': len(self.face_locations),
            'students_recognized': len([n for n in self.face_names if n != "Unknown"])
        }
    
    def _log_detection(self, faces_detected: int, students_recognized: int, processing_time: float):
        """Log detection results to database."""
        try:
            DetectionLog.objects.create(
                camera=self.camera_stream,
                faces_detected=faces_detected,
                students_recognized=students_recognized,
                processing_time=processing_time,
                frame_resolution=f"{self.camera_stream.rtsp_url if self.camera_stream else 'Unknown'}"
            )
        except Exception as e:
            logger.error(f"Error logging detection: {e}")
    
    def _send_detection_update(self, faces_detected: int, students_recognized: int):
        """Send detection update via WebSocket."""
        try:
            async_to_sync(self.channel_layer.group_send)(
                "detection_updates",
                {
                    "type": "detection_update",
                    "faces_detected": faces_detected,
                    "students_recognized": students_recognized,
                    "timestamp": timezone.now().isoformat(),
                    "camera_location": self.camera_stream.location if self.camera_stream else "",
                }
            )
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")
    
    def draw_results_on_frame(self, frame: np.ndarray, results: Dict) -> np.ndarray:
        """Draw detection results on the frame."""
        face_locations = results.get('face_locations', [])
        face_names = results.get('face_names', [])
        
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Draw rectangle around face
            color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Draw label
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.6, (255, 255, 255), 1)
        
        # Add processing info
        processing_time = results.get('processing_time', 0)
        cv2.putText(frame, f"Processing: {processing_time:.3f}s", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return frame
