"""
AI Models for Face Recognition and Liveness Detection
Updated to use centralized model service
"""

import logging
import numpy as np
import cv2
from typing import List, Dict, Optional, Tuple
from app.services.models import model_service
from app.config import settings

logger = logging.getLogger(__name__)

class RealFaceRecognitionSystem:
    """Real face recognition system using centralized model service"""
    
    def __init__(self):
        self.known_faces = {}  # student_id -> embedding
        self.initialized = False
        
    def initialize_models(self):
        """Initialize the face recognition models"""
        try:
            logger.info("Initializing face recognition system...")
            model_service.initialize_models()
            self.initialized = True
            logger.info("Face recognition system initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing face recognition system: {e}")
            self.initialized = False
            raise
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect faces in image using YOLOv8n"""
        try:
            if not self.initialized:
                self.initialize_models()
            
            return model_service.detect_faces(image)
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return []
    
    def extract_face_embedding(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """Extract face embedding using InsightFace ArcFace"""
        try:
            if not self.initialized:
                self.initialize_models()
            
            return model_service.extract_face_embedding(face_image)
                
        except Exception as e:
            logger.error(f"Face embedding extraction failed: {e}")
            return None
    
    def load_known_faces(self, students_data: List[Dict]):
        """Load known faces from database"""
        try:
            self.known_faces.clear()
            for student in students_data:
                if student.get('embedding'):
                    try:
                        # Parse the binary embedding data
                        embedding = np.frombuffer(student['embedding'], dtype=np.float32)
                        self.known_faces[student['student_id']] = embedding
                        logger.info(f"Loaded face embedding for student {student['student_id']}")
                    except Exception as e:
                        logger.warning(f"Failed to load embedding for student {student['student_id']}: {e}")

            logger.info(f"Loaded {len(self.known_faces)} known faces")

        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
    
    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compare two face embeddings using cosine similarity"""
        return model_service.compare_faces(embedding1, embedding2)
    
    def find_best_match(self, embedding: np.ndarray) -> Optional[Dict]:
        """
        Find best match for an embedding against known faces
        
        Args:
            embedding: Face embedding to match
            
        Returns:
            dict with student_id and confidence if match found, None otherwise
        """
        try:
            best_match = None
            best_confidence = 0.0

            # Compare with all known faces using cosine similarity
            for student_id, known_embedding in self.known_faces.items():
                confidence = self.compare_faces(embedding, known_embedding)
                if confidence > best_confidence and confidence > settings.recognition_threshold:
                    best_confidence = confidence
                    best_match = student_id

            if best_match:
                logger.info(f"Face recognized as student {best_match} with confidence {best_confidence:.3f}")
                return {
                    'student_id': best_match,
                    'confidence': best_confidence
                }
            else:
                logger.info(f"Face not recognized (no match above {settings.recognition_threshold} threshold)")
                return None

        except Exception as e:
            logger.error(f"Error finding best match: {e}")
            return None
    
    def recognize_face(self, face_image: np.ndarray) -> Optional[Dict]:
        """Recognize a face against known faces"""
        try:
            embedding = self.extract_face_embedding(face_image)
            if embedding is not None:
                return self.find_best_match(embedding)
            return None
        except Exception as e:
            logger.error(f"Face recognition failed: {e}")
            return None

class RealLivenessDetectionSystem:
    """Real liveness detection system using MediaPipe head pose estimation"""
    
    def __init__(self):
        self.initialized = False
        
    def initialize_models(self):
        """Initialize liveness detection models"""
        try:
            logger.info("Initializing liveness detection system...")
            model_service.initialize_models()
            self.initialized = True
            logger.info("Liveness detection system initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing liveness detection system: {e}")
            self.initialized = False
            raise
    
    def detect_head_pose(self, image: np.ndarray) -> Dict[str, float]:
        """Detect head pose angles using MediaPipe"""
        try:
            if not self.initialized:
                self.initialize_models()
            
            return model_service.detect_head_pose(image)
            
        except Exception as e:
            logger.error(f"Head pose detection failed: {e}")
            return {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}
    
    def verify_liveness(self, image: np.ndarray, position: str) -> Dict[str, any]:
        """Verify liveness for a specific head position"""
        try:
            if not self.initialized:
                self.initialize_models()
            
            pose = self.detect_head_pose(image)
            yaw = pose['yaw']
            
            # Define angle thresholds for each position
            thresholds = {
                'center': 8.0,   # ±8 degrees
                'left': -15.0,   # ≤ -15 degrees
                'right': 15.0    # ≥ +15 degrees
            }
            
            is_valid = False
            if position == 'center':
                is_valid = abs(yaw) <= thresholds['center']
            elif position == 'left':
                is_valid = yaw <= thresholds['left']
            elif position == 'right':
                is_valid = yaw >= thresholds['right']
            
            return {
                'is_live': is_valid,
                'pose': pose,
                'position': position,
                'confidence': 0.8 if is_valid else 0.2
            }
            
        except Exception as e:
            logger.error(f"Liveness verification failed: {e}")
            return {
                'is_live': False,
                'pose': {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0},
                'position': position,
                'confidence': 0.0
            }
    
    def extract_face_embedding(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Extract face embedding for liveness detection"""
        try:
            if not self.initialized:
                self.initialize_models()
            
            return model_service.extract_face_embedding(image)
            
        except Exception as e:
            logger.error(f"Face embedding extraction failed: {e}")
            return None

# Global instances
face_recognition_system = RealFaceRecognitionSystem()
liveness_detection_system = RealLivenessDetectionSystem()