import cv2
import numpy as np
import json
import time
import logging
import base64
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MockLivenessDetectionEngine:
    """Mock implementation of liveness detection engine for development/testing"""
    
    def __init__(self):
        """Initialize the mock liveness detection engine"""
        self.initialized = True
        logger.info("Mock liveness detection engine initialized")
        
    def initialize_models(self):
        """Mock model initialization"""
        self.initialized = True
        logger.info("Mock liveness detection models initialized successfully")
    
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
    
    def verify_liveness_movement(self, center_embedding: np.ndarray, 
                                left_embedding: np.ndarray, 
                                right_embedding: np.ndarray) -> Dict:
        """Mock liveness movement verification"""
        logger.info("Mock liveness movement verification called")
        return {
            'movement_verified': True,
            'confidence': np.random.uniform(0.85, 0.98),
            'timestamp': time.time()
        }
    
    def detect_liveness(self, frame: np.ndarray, position: str) -> Dict:
        """Mock liveness detection"""
        logger.info(f"Mock liveness detection called for position: {position}")
        return {
            'is_live': True,
            'confidence': np.random.uniform(0.85, 0.98),
            'position': position,
            'timestamp': time.time()
        }
    
    def create_session(self, student_id: Optional[int] = None) -> Dict:
        """Mock session creation"""
        session_id = f"mock_session_{int(time.time())}"
        expires_at = datetime.now() + timedelta(minutes=10)
        
        return {
            'session_id': session_id,
            'student_id': student_id,
            'status': 'active',
            'created_at': datetime.now(),
            'expires_at': expires_at,
            'center_frame_data': None,
            'left_frame_data': None,
            'right_frame_data': None,
            'center_verified': False,
            'left_verified': False,
            'right_verified': False,
            'liveness_score': 0.0,
            'movement_verified': False,
            'final_embedding': None,
            'error_message': None,
            'attempts_count': 0
        }
    
    def update_session(self, session_id: str, position: str, 
                      frame_data: str, embedding: str) -> Dict:
        """Mock session update"""
        logger.info(f"Mock session update: {session_id}, position: {position}")
        return {
            'success': True,
            'message': f"Session {session_id} updated for {position}",
            'position': position,
            'verified': True,
            'liveness_score': np.random.uniform(0.85, 0.98)
        }
    
    def verify_session(self, session_id: str) -> Dict:
        """Mock session verification"""
        logger.info(f"Mock session verification: {session_id}")
        return {
            'success': True,
            'message': f"Session {session_id} verified successfully",
            'liveness_score': np.random.uniform(0.85, 0.98),
            'movement_verified': True,
            'final_embedding': 'mock_final_embedding'
        }


# Create a mock instance
liveness_detection_engine = MockLivenessDetectionEngine()
