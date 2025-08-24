import cv2
import numpy as np
import json
import time
import logging
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class MockFaceRecognitionSystem:
    """Mock implementation of face recognition system for development/testing"""
    
    def __init__(self):
        """Initialize the mock face recognition system"""
        self.known_faces = {}  # {student_id: embedding}
        self.initialized = True
        logger.info("Mock face recognition system initialized")
        
    def initialize_models(self):
        """Mock model initialization"""
        self.initialized = True
        logger.info("Mock AI models initialized successfully")
        
    def load_known_faces(self, students_data: List[Dict]):
        """Load known faces from database"""
        try:
            self.known_faces.clear()
            for student in students_data:
                if student.get('embedding_vector'):
                    # Mock embedding - just store the student ID
                    self.known_faces[student['id']] = f"mock_embedding_{student['id']}"
            logger.info(f"Loaded {len(self.known_faces)} known faces (mock)")
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Mock face detection - returns a dummy face box"""
        logger.info("Mock face detection called")
        # Return a mock face box in the center of the frame
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        face_size = min(w, h) // 4
        return [(center_x - face_size, center_y - face_size, 
                center_x + face_size, center_y + face_size)]
    
    def extract_face_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """Mock face embedding extraction"""
        logger.info("Mock face embedding extraction called")
        # Return a mock embedding vector
        return np.random.rand(512).astype(np.float32)
    
    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Mock face comparison - returns random confidence"""
        logger.info("Mock face comparison called")
        # Return a random confidence score between 0.7 and 0.95
        return np.random.uniform(0.7, 0.95)
    
    def recognize_face(self, face_img: np.ndarray) -> Optional[Dict]:
        """Mock face recognition"""
        logger.info("Mock face recognition called")
        # Randomly return a recognized student or None
        if np.random.random() > 0.3:  # 70% chance of recognition
            student_id = np.random.choice(list(self.known_faces.keys())) if self.known_faces else 1
            return {
                'student_id': student_id,
                'confidence': np.random.uniform(0.8, 0.95)
            }
        return None


# Create a mock instance
face_recognition_system = MockFaceRecognitionSystem()


class MockLivenessDetectionSystem:
    """Mock implementation of liveness detection system"""
    
    def __init__(self):
        self.initialized = True
        logger.info("Mock liveness detection system initialized")
    
    def initialize_models(self):
        """Mock model initialization"""
        self.initialized = True
        logger.info("Mock liveness detection models initialized")
    
    def detect_liveness(self, frame: np.ndarray, position: str) -> Dict:
        """Mock liveness detection"""
        logger.info(f"Mock liveness detection called for position: {position}")
        return {
            'is_live': True,
            'confidence': np.random.uniform(0.85, 0.98),
            'position': position,
            'timestamp': time.time()
        }
    
    def verify_movement(self, session_data: Dict) -> Dict:
        """Mock movement verification"""
        logger.info("Mock movement verification called")
        return {
            'movement_verified': True,
            'confidence': np.random.uniform(0.8, 0.95),
            'timestamp': time.time()
        }


# Create a mock instance
liveness_detection_system = MockLivenessDetectionSystem()
