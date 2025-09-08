import cv2
import numpy as np
import base64
import json
import logging
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from .models import Student, UnrecognizedFace, Attendance
import os

logger = logging.getLogger(__name__)

class FaceRecognitionEngine:
    def __init__(self):
        self.face_cascade = None
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_face_cascade()
        self.load_known_faces()
    
    def load_face_cascade(self):
        """Load OpenCV face detection cascade"""
        try:
            # Try to load from OpenCV data directory
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            else:
                # Fallback to basic face detection
                logger.warning("Haar cascade not found, using basic detection")
                self.face_cascade = None
        except Exception as e:
            logger.error(f"Error loading face cascade: {e}")
            self.face_cascade = None
    
    def load_known_faces(self):
        """Load known face embeddings from database"""
        try:
            students = Student.objects.filter(face_embedding__isnull=False).exclude(face_embedding='')
            for student in students:
                try:
                    if student.face_embedding:
                        # For now, we'll use a simple placeholder
                        # In a real implementation, this would load actual face encodings
                        self.known_face_encodings.append(student.face_embedding)
                        self.known_face_names.append(student.name)
                except Exception as e:
                    logger.error(f"Error loading face for student {student.name}: {e}")
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
    
    def detect_faces(self, frame):
        """Detect faces in frame using OpenCV"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = []
        
        if self.face_cascade:
            # Use Haar cascade for face detection
            face_locations = self.face_cascade.detectMultiScale(
                gray, 
                scaleFactor=1.1, 
                minNeighbors=5, 
                minSize=(30, 30)
            )
            
            for (x, y, w, h) in face_locations:
                faces.append({
                    'bbox': (x, y, w, h),
                    'confidence': 0.8  # Placeholder confidence
                })
        else:
            # Basic face detection using color and size
            # This is a simplified approach for demonstration
            height, width = gray.shape
            # Look for regions that might contain faces
            # This is a very basic heuristic
            for y in range(0, height, 50):
                for x in range(0, width, 50):
                    if x + 100 < width and y + 100 < height:
                        region = gray[y:y+100, x:x+100]
                        # Simple check for face-like regions
                        if np.mean(region) > 50 and np.mean(region) < 200:
                            faces.append({
                                'bbox': (x, y, 100, 100),
                                'confidence': 0.5
                            })
        
        return faces
    
    def extract_face_encoding(self, frame, face_bbox):
        """Extract face encoding (placeholder implementation)"""
        x, y, w, h = face_bbox
        face_image = frame[y:y+h, x:x+w]
        
        # Resize to standard size
        face_image = cv2.resize(face_image, (128, 128))
        
        # Convert to grayscale and flatten
        gray_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        encoding = gray_face.flatten().tolist()
        
        # Create a simple hash-based encoding
        encoding_hash = hash(str(encoding)) % 1000000
        return str(encoding_hash)
    
    def compare_faces(self, face_encoding, known_encodings, tolerance=0.6):
        """Compare face encodings (simplified implementation)"""
        if not known_encodings:
            return False, 0.0
        
        # Simple comparison for now
        # In a real implementation, this would use proper face recognition
        for known_encoding in known_encodings:
            if face_encoding == known_encoding:
                return True, 0.9
        
        return False, 0.0
    
    def process_frame(self, frame, camera):
        """Process a single frame for face detection and recognition"""
        try:
            results = {
                'faces_detected': 0,
                'faces_recognized': 0,
                'unrecognized_faces': 0,
                'confidence_scores': [],
                'recognition_accuracy': 0.0,
                'metadata': {},
                'attendance_marked': []
            }
            
            # Detect faces
            faces = self.detect_faces(frame)
            results['faces_detected'] = len(faces)
            
            if not faces:
                return results
            
            recognized_count = 0
            unrecognized_count = 0
            
            for face in faces:
                bbox = face['bbox']
                confidence = face['confidence']
                
                # Extract face encoding
                face_encoding = self.extract_face_encoding(frame, bbox)
                
                # Compare with known faces
                is_recognized, recognition_confidence = self.compare_faces(
                    face_encoding, 
                    self.known_face_encodings
                )
                
                if is_recognized:
                    recognized_count += 1
                    results['confidence_scores'].append(recognition_confidence)
                    
                    # Find the recognized student
                    student_index = self.known_face_encodings.index(face_encoding)
                    student_name = self.known_face_names[student_index]
                    
                    # Mark attendance
                    try:
                        student = Student.objects.get(name=student_name)
                        attendance, created = Attendance.objects.get_or_create(
                            student=student,
                            date=timezone.now().date(),
                            defaults={
                                'time_in': timezone.now(),
                                'status': 'Present',
                                'camera_source': camera,
                                'confidence_score': recognition_confidence,
                                'face_bbox': json.dumps(bbox),
                                'processing_time': 0.1  # Placeholder
                            }
                        )
                        
                        if created:
                            results['attendance_marked'].append({
                                'student_name': student_name,
                                'student_id': student.roll_number,
                                'status': 'Present'
                            })
                    except Student.DoesNotExist:
                        logger.error(f"Student {student_name} not found in database")
                
                else:
                    unrecognized_count += 1
                    
                    # Save unrecognized face
                    try:
                        # Convert frame to base64
                        _, buffer = cv2.imencode('.jpg', frame)
                        frame_base64 = base64.b64encode(buffer).decode('utf-8')
                        
                        UnrecognizedFace.objects.create(
                            face_embedding=face_encoding,
                            face_image=f"data:image/jpeg;base64,{frame_base64}",
                            camera_source=camera,
                            confidence_score=confidence,
                            status='PENDING'
                        )
                    except Exception as e:
                        logger.error(f"Error saving unrecognized face: {e}")
            
            results['faces_recognized'] = recognized_count
            results['unrecognized_faces'] = unrecognized_count
            
            if results['faces_detected'] > 0:
                results['recognition_accuracy'] = recognized_count / results['faces_detected']
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return {
                'error': str(e),
                'faces_detected': 0,
                'faces_recognized': 0,
                'unrecognized_faces': 0,
                'confidence_scores': [],
                'recognition_accuracy': 0.0,
                'metadata': {},
                'attendance_marked': []
            }
    
    def save_face_embedding(self, student, face_image_base64):
        """Save face embedding for a student"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(face_image_base64.split(',')[1])
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Detect faces in the image
            faces = self.detect_faces(frame)
            
            if faces:
                # Use the first detected face
                face_bbox = faces[0]['bbox']
                face_encoding = self.extract_face_encoding(frame, face_bbox)
                
                # Save to student
                student.face_embedding = face_encoding
                student.face_image = face_image_base64
                student.face_embedding_updated = timezone.now()
                student.recognition_confidence = faces[0]['confidence']
                student.save()
                
                # Reload known faces
                self.load_known_faces()
                
                return True, "Face embedding saved successfully"
            else:
                return False, "No face detected in the image"
                
        except Exception as e:
            logger.error(f"Error saving face embedding: {e}")
            return False, f"Error: {str(e)}"
