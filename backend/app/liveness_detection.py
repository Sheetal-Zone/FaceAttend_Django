import cv2
import numpy as np
import json
import time
import logging
import base64
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
from app.ai_models import face_recognition_system, liveness_detection_system

logger = logging.getLogger(__name__)


class RealLivenessDetectionEngine:
    """Real implementation of liveness detection engine using AI models"""
    
    def __init__(self):
        """Initialize the real liveness detection engine"""
        self.initialized = False
        self.sessions = {}  # In-memory session storage
        logger.info("Real liveness detection engine initialized")
        
    def initialize_models(self):
        """Initialize AI models for liveness detection"""
        try:
            # Initialize face recognition system
            if not face_recognition_system.initialize_models():
                logger.error("Failed to initialize face recognition system")
                return False
            
            # Initialize liveness detection system
            if not liveness_detection_system.initialize_models():
                logger.error("Failed to initialize liveness detection system")
                return False
            
            self.initialized = True
            logger.info("Real liveness detection engine models initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing real liveness detection engine: {e}")
            self.initialized = False
            return False
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Real face detection using AI models"""
        if not self.initialized:
            logger.warning("Liveness detection engine not initialized")
            return []
        
        return face_recognition_system.detect_faces(frame)
    
    def extract_face_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """Real face embedding extraction using AI models"""
        if not self.initialized:
            logger.warning("Liveness detection engine not initialized")
            return None
        
        return face_recognition_system.extract_face_embedding(face_img)
    
    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Real face comparison using AI models"""
        if not self.initialized:
            logger.warning("Liveness detection engine not initialized")
            return 0.0
        
        return face_recognition_system.compare_faces(embedding1, embedding2)
    
    def verify_liveness_movement(self, center_embedding: np.ndarray, 
                                left_embedding: np.ndarray, 
                                right_embedding: np.ndarray) -> Dict:
        """Real liveness movement verification"""
        if not self.initialized:
            return {
                'movement_verified': False,
                'confidence': 0.0,
                'timestamp': time.time(),
                'error': 'Engine not initialized'
            }
        
        try:
            # Check if all embeddings are present
            if center_embedding is None or left_embedding is None or right_embedding is None:
                return {
                    'movement_verified': False,
                    'confidence': 0.0,
                    'timestamp': time.time(),
                    'error': 'Missing embeddings for movement verification'
                }
            
            # Calculate similarity between positions
            center_left_similarity = self.compare_faces(center_embedding, left_embedding)
            center_right_similarity = self.compare_faces(center_embedding, right_embedding)
            left_right_similarity = self.compare_faces(left_embedding, right_embedding)
            
            # Movement verification logic:
            # - Center-left and center-right should be similar (same person)
            # - Left-right should be different (different head positions)
            # - All should be above threshold for same person
            person_similarity = min(center_left_similarity, center_right_similarity)
            movement_difference = 1.0 - left_right_similarity  # Higher difference = better movement
            
            # Calculate overall movement verification score
            if person_similarity > 0.7 and movement_difference > 0.1:
                movement_score = (person_similarity + movement_difference) / 2
                movement_verified = movement_score > 0.6
            else:
                movement_score = 0.0
                movement_verified = False
            
            logger.info(f"Movement verification: person_sim={person_similarity:.3f}, "
                       f"movement_diff={movement_difference:.3f}, score={movement_score:.3f}")
            
            return {
                'movement_verified': movement_verified,
                'confidence': movement_score,
                'timestamp': time.time(),
                'details': {
                    'person_similarity': person_similarity,
                    'movement_difference': movement_difference,
                    'center_left_similarity': center_left_similarity,
                    'center_right_similarity': center_right_similarity,
                    'left_right_similarity': left_right_similarity
                }
            }
            
        except Exception as e:
            logger.error(f"Error in movement verification: {e}")
            return {
                'movement_verified': False,
                'confidence': 0.0,
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def detect_liveness(self, frame: np.ndarray, position: str) -> Dict:
        """Real liveness detection using AI models"""
        if not self.initialized:
            return {
                'is_live': False,
                'confidence': 0.0,
                'position': position,
                'timestamp': time.time(),
                'error': 'Engine not initialized'
            }
        
        return liveness_detection_system.detect_liveness(frame, position)
    
    def create_session(self, student_id: Optional[int] = None) -> Dict:
        """Create a new liveness detection session"""
        session_id = f"session_{int(time.time())}_{np.random.randint(1000, 9999)}"
        expires_at = datetime.now() + timedelta(minutes=10)
        
        session_data = {
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
        
        self.sessions[session_id] = session_data
        logger.info(f"Created liveness detection session: {session_id}")
        
        return session_data
    
    def update_session(self, session_id: str, position: str, 
                      frame_data: str, embedding: str) -> Dict:
        """Update session with captured frame and embedding"""
        if session_id not in self.sessions:
            return {
                'success': False,
                'message': f"Session {session_id} not found",
                'error': 'Session not found'
            }
        
        session = self.sessions[session_id]
        
        try:
            # Update session data
            session[f'{position}_frame_data'] = frame_data
            session[f'{position}_embedding'] = embedding
            session[f'{position}_verified'] = True
            session['attempts_count'] += 1
            
            # Check if all positions are captured
            positions_captured = sum([
                session['center_verified'],
                session['left_verified'],
                session['right_verified']
            ])
            
            if positions_captured == 3:
                # All positions captured, verify movement
                center_emb = session.get('center_embedding')
                left_emb = session.get('left_embedding')
                right_emb = session.get('right_embedding')
                
                if center_emb and left_emb and right_emb:
                    # Parse embeddings if they're strings
                    if isinstance(center_emb, str):
                        center_emb = json.loads(center_emb)
                    if isinstance(left_emb, str):
                        left_emb = json.loads(left_emb)
                    if isinstance(right_emb, str):
                        right_emb = json.loads(right_emb)
                    
                    # Convert to numpy arrays
                    center_emb = np.array(center_emb)
                    left_emb = np.array(left_emb)
                    right_emb = np.array(right_emb)
                    
                    # Verify movement
                    movement_result = self.verify_liveness_movement(center_emb, left_emb, right_emb)
                    session['movement_verified'] = movement_result['movement_verified']
                    session['liveness_score'] = movement_result['confidence']
                    
                    if movement_result['movement_verified']:
                        session['status'] = 'completed'
                        session['final_embedding'] = center_emb.tolist()  # Use center as final
                        logger.info(f"Session {session_id} completed successfully")
                    else:
                        session['status'] = 'failed'
                        session['error_message'] = movement_result.get('error', 'Movement verification failed')
                        logger.warning(f"Session {session_id} failed: {session['error_message']}")
            
            logger.info(f"Session {session_id} updated for {position}")
            
            return {
                'success': True,
                'message': f"Session {session_id} updated for {position}",
                'verified': True,
                'liveness_score': session['liveness_score'],
                'status': session['status']
            }
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return {
                'success': False,
                'message': f"Error updating session: {str(e)}",
                'error': str(e)
            }
    
    def verify_session(self, session_id: str) -> Dict:
        """Verify a completed liveness detection session"""
        if session_id not in self.sessions:
            return {
                'success': False,
                'message': f"Session {session_id} not found",
                'error': 'Session not found'
            }
        
        session = self.sessions[session_id]
        
        if session['status'] == 'completed':
            return {
                'success': True,
                'message': f"Session {session_id} verified successfully",
                'liveness_score': session['liveness_score'],
                'movement_verified': session['movement_verified'],
                'final_embedding': session['final_embedding']
            }
        elif session['status'] == 'failed':
            return {
                'success': False,
                'message': f"Session {session_id} failed",
                'error': session['error_message'],
                'liveness_score': session['liveness_score']
            }
        else:
            return {
                'success': False,
                'message': f"Session {session_id} is still in progress",
                'status': session['status']
            }
    
    def process_frame_for_liveness(self, frame: np.ndarray, position: str) -> Dict:
        """Process a frame for liveness detection"""
        if not self.initialized:
            return {
                'is_live': False,
                'confidence': 0.0,
                'position': position,
                'timestamp': time.time(),
                'error': 'Engine not initialized'
            }
        
        # Detect faces in the frame
        face_locations = self.detect_faces(frame)
        
        if not face_locations:
            return {
                'is_live': False,
                'confidence': 0.0,
                'position': position,
                'timestamp': time.time(),
                'error': 'No face detected'
            }
        
        # Use the first detected face
        x1, y1, x2, y2 = face_locations[0]
        face_img = frame[y1:y2, x1:x2]
        
        # Perform liveness detection
        liveness_result = self.detect_liveness(face_img, position)
        
        # Extract face embedding
        embedding = self.extract_face_embedding(face_img)
        
        return {
            **liveness_result,
            'face_detected': True,
            'face_location': face_locations[0],
            'embedding': embedding.tolist() if embedding is not None else None
        }


# Create real instance
liveness_detection_engine = RealLivenessDetectionEngine()
