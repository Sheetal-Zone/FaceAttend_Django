"""
Model Service - YOLOv8n Face Detection + InsightFace ArcFace Embeddings
"""

import logging
import cv2
import numpy as np
from pathlib import Path
import torch
from ultralytics import YOLO
import insightface
from insightface.app import FaceAnalysis
import os
from typing import List, Dict, Optional, Tuple
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None

logger = logging.getLogger(__name__)

class ModelService:
    """Centralized model service for face detection and recognition"""
    
    def __init__(self):
        self.face_detector = None
        self.face_recognizer = None
        self.face_landmarks = None
        self.initialized = False
        
    def initialize_models(self):
        """Initialize all AI models"""
        try:
            logger.info("Initializing AI models...")
            
            # Initialize YOLOv8n for face detection
            self._initialize_face_detector()
            
            # Initialize InsightFace for face recognition
            self._initialize_face_recognizer()
            
            # Initialize MediaPipe for head pose estimation
            self._initialize_face_landmarks()
            
            self.initialized = True
            logger.info("All models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            self.initialized = False
            raise
    
    def _initialize_face_detector(self):
        """Initialize YOLOv8n face detector"""
        try:
            # Use YOLOv8n general model (works for face detection)
            model_path = "models/yolov8n.pt"
            if not os.path.exists(model_path):
                model_path = "../models/yolov8n.pt"
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"YOLOv8n model not found at {model_path}")
            
            self.face_detector = YOLO(model_path)
            logger.info(f"✅ YOLO model loaded: v8n from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load YOLOv8n: {e}")
            raise
    
    def _initialize_face_recognizer(self):
        """Initialize InsightFace ArcFace recognizer"""
        try:
            # Initialize InsightFace with buffalo_l model (more stable)
            self.face_recognizer = FaceAnalysis(
                name='buffalo_l',
                providers=['CPUExecutionProvider']
            )
            self.face_recognizer.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("✅ InsightFace loaded: ArcFace buffalo_l")
            
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            # Try with buffalo_s as fallback
            try:
                self.face_recognizer = FaceAnalysis(
                    name='buffalo_s',
                    providers=['CPUExecutionProvider']
                )
                self.face_recognizer.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("✅ InsightFace loaded: ArcFace buffalo_s (fallback)")
            except Exception as e2:
                logger.error(f"Failed to initialize InsightFace with fallback: {e2}")
                raise
    
    def _initialize_face_landmarks(self):
        """Initialize MediaPipe for head pose estimation"""
        if not MEDIAPIPE_AVAILABLE:
            logger.warning("MediaPipe not available - head pose estimation disabled")
            self.face_landmarks = None
            return
            
        try:
            self.face_landmarks = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            logger.info("MediaPipe face landmarks initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe: {e}")
            self.face_landmarks = None
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in image using YOLOv8n
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of bounding boxes as (x1, y1, x2, y2)
        """
        try:
            if not self.initialized:
                raise RuntimeError("Models not initialized")
            
            # Run YOLO detection
            results = self.face_detector(image, conf=0.5, verbose=False)
            
            face_boxes = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Extract coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        face_boxes.append((int(x1), int(y1), int(x2), int(y2)))
            
            logger.debug(f"Detected {len(face_boxes)} faces")
            return face_boxes
            
        except Exception as e:
            logger.error(f"Face detection failed: {e}")
            return []
    
    def extract_face_embedding(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract face embedding using InsightFace ArcFace
        
        Args:
            face_image: Cropped face image as numpy array
            
        Returns:
            512D embedding vector or None if failed
        """
        try:
            if not self.initialized:
                raise RuntimeError("Models not initialized")
            
            # Extract face embedding
            faces = self.face_recognizer.get(face_image)
            
            if len(faces) > 0:
                # Get the first face's embedding
                embedding = faces[0].embedding
                logger.debug(f"Extracted embedding with shape: {embedding.shape}")
                return embedding
            else:
                logger.warning("No face found in image for embedding extraction")
                return None
                
        except Exception as e:
            logger.error(f"Face embedding extraction failed: {e}")
            return None
    
    def detect_head_pose(self, image: np.ndarray) -> Dict[str, float]:
        """
        Detect head pose using MediaPipe landmarks
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary with yaw, pitch, roll angles
        """
        if not self.initialized:
            raise RuntimeError("Models not initialized")
            
        if not MEDIAPIPE_AVAILABLE or self.face_landmarks is None:
            logger.warning("MediaPipe not available - returning default pose")
            return {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}
            
        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process with MediaPipe
            results = self.face_landmarks.process(rgb_image)
            
            if results.multi_face_landmarks:
                # Get the first face
                face_landmarks = results.multi_face_landmarks[0]
                
                # Calculate head pose angles (simplified)
                # This is a basic implementation - in production, use proper 3D pose estimation
                landmarks = np.array([[lm.x, lm.y, lm.z] for lm in face_landmarks.landmark])
                
                # Calculate yaw (left-right rotation)
                left_eye = landmarks[33]  # Left eye corner
                right_eye = landmarks[362]  # Right eye corner
                nose_tip = landmarks[1]  # Nose tip
                
                # Simple yaw calculation
                eye_vector = right_eye - left_eye
                yaw = np.arctan2(eye_vector[0], eye_vector[1]) * 180 / np.pi
                
                # Normalize yaw to -90 to +90 degrees
                yaw = max(-90, min(90, yaw))
                
                return {
                    'yaw': yaw,
                    'pitch': 0.0,  # Simplified - would need more complex calculation
                    'roll': 0.0    # Simplified - would need more complex calculation
                }
            else:
                return {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}
                
        except Exception as e:
            logger.error(f"Head pose detection failed: {e}")
            return {'yaw': 0.0, 'pitch': 0.0, 'roll': 0.0}
    
    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compare two face embeddings using cosine similarity
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Face comparison failed: {e}")
            return 0.0

# Global model service instance
model_service = ModelService()
