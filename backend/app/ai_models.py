import cv2
import numpy as np
import json
import time
import logging
import os
from typing import List, Tuple, Optional, Dict
from pathlib import Path
from app.config import settings

logger = logging.getLogger(__name__)


class RealFaceRecognitionSystem:
    """Real implementation of face recognition system using YOLO and InsightFace with OpenCV fallback"""
    
    def __init__(self):
        """Initialize the real face recognition system"""
        self.known_faces = {}  # {student_id: embedding}
        self.initialized = False
        self.yolo_model = None
        self.face_recognition_model = None
        self.face_detector = None  # OpenCV fallback
        logger.info("Real face recognition system initialized")
        
    def initialize_models(self):
        """Initialize real AI models with optional OpenCV fallback and performance optimizations"""
        try:
            logger.info("Initializing AI models with performance optimizations...")
            # Try to initialize YOLO for face detection
            try:
                from ultralytics import YOLO
                # Try multiple candidate weights across likely locations
                file_dir = Path(__file__).resolve()
                backend_dir = file_dir.parents[1]
                project_root = file_dir.parents[2]
                configured = [Path(p) for p in ([settings.yolo_model_path] + settings.yolo_candidate_weights)]
                candidate_weights = []
                for p in configured:
                    # search both backend and project root for each configured relative path
                    candidate_weights.append((backend_dir / p).resolve())
                    candidate_weights.append((project_root / p).resolve())
                loaded = False
                for candidate in candidate_weights:
                    if candidate.exists():
                        try:
                            self.yolo_model = YOLO(str(candidate))
                            logger.info(f"YOLO model loaded from {candidate}")
                            loaded = True
                            break
                        except Exception as ye:
                            logger.warning(f"Failed loading YOLO weights {candidate}: {ye}")
                if not loaded:
                    # Attempt auto-download of lightweight YOLO (v8n) then load
                    try:
                        from backend.download_models import download_yolo_model  # type: ignore
                    except Exception:
                        try:
                            from download_models import download_yolo_model  # type: ignore
                        except Exception:
                            download_yolo_model = None  # type: ignore
                    if download_yolo_model is not None:
                        try:
                            weights_path = download_yolo_model()
                            if weights_path and Path(weights_path).exists():
                                self.yolo_model = YOLO(str(weights_path))
                                loaded = True
                                logger.info(f"YOLO model auto-downloaded and loaded from {weights_path}")
                    
                        except Exception as de:
                            logger.warning(f"Auto-download of YOLO failed: {de}")
                    if not loaded:
                        logger.warning("YOLO model not found or failed to load")
                        self.yolo_model = None
            except ImportError:
                logger.warning("Ultralytics not available, using OpenCV fallback")
                self.yolo_model = None
            except Exception as e:
                logger.warning(f"YOLO initialization failed: {e}, using OpenCV fallback")
                self.yolo_model = None
            
            # Try to initialize InsightFace for face recognition
            try:
                import insightface
                from insightface.app import FaceAnalysis
                
                # Initialize InsightFace model with CPU fallback when GPU is not available
                self.face_recognition_model = FaceAnalysis(name='buffalo_l')
                try:
                    # Prefer GPU if available
                    self.face_recognition_model.prepare(ctx_id=0, det_size=(640, 640))
                except Exception as gpu_e:
                    logger.warning(f"GPU not available for InsightFace ({gpu_e}), falling back to CPU")
                    self.face_recognition_model.prepare(ctx_id=-1, det_size=(640, 640))
                logger.info("InsightFace model initialized successfully")
                
            except ImportError:
                logger.warning("InsightFace not available, using OpenCV fallback")
                self.face_recognition_model = None
            except Exception as e:
                logger.warning(f"InsightFace initialization failed: {e}, using OpenCV fallback")
                self.face_recognition_model = None
            
            # Initialize OpenCV face detector as fallback if allowed
            if settings.allow_opencv_fallback:
                try:
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    self.face_detector = cv2.CascadeClassifier(cascade_path)
                    if self.face_detector.empty():
                        logger.warning("OpenCV face cascade not loaded")
                        self.face_detector = None
                    else:
                        logger.info("OpenCV face detector initialized as fallback")
                except Exception as e:
                    logger.error(f"Failed to load OpenCV face detector: {e}")
                    self.face_detector = None
            else:
                self.face_detector = None
            
            self.initialized = True
            logger.info("AI models initialized successfully with fallbacks")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing AI models: {e}")
            self.initialized = False
            return False
        
    def load_known_faces(self, students_data: List[Dict]):
        """Load known faces from database"""
        try:
            self.known_faces.clear()
            for student in students_data:
                if student.get('embedding_vector'):
                    try:
                        # Parse the embedding vector
                        if isinstance(student['embedding_vector'], str):
                            embedding = np.array(json.loads(student['embedding_vector']))
                        else:
                            embedding = np.array(student['embedding_vector'])
                        self.known_faces[student['id']] = embedding
                        logger.info(f"Loaded face embedding for student {student['id']}")
                    except Exception as e:
                        logger.warning(f"Failed to load embedding for student {student['id']}: {e}")
            
            logger.info(f"Loaded {len(self.known_faces)} known faces")
            
        except Exception as e:
            logger.error(f"Error loading known faces: {e}")
    
    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Real face detection using YOLO or OpenCV fallback"""
        if not self.initialized:
            logger.warning("AI models not initialized")
            return []
        
        try:
            face_locations = []
            
            # Try YOLO first
            if self.yolo_model:
                try:
                    results = self.yolo_model(
                        frame,
                        imgsz=getattr(settings, 'yolo_imgsz', 480),
                        conf=getattr(settings, 'face_detection_confidence', 0.5),
                        verbose=False,
                        device='cpu',  # Force CPU for stability
                        half=False,   # Disable half precision for compatibility
                    )
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                # Get box coordinates
                                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                                face_locations.append((x1, y1, x2, y2))
                except Exception as e:
                    logger.warning(f"YOLO detection failed: {e}")
            
            # Fallback to OpenCV if YOLO fails or no faces found and fallback allowed
            if not face_locations and self.face_detector and settings.allow_opencv_fallback:
                try:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = self.face_detector.detectMultiScale(gray, 1.1, 4)
                    for (x, y, w, h) in faces:
                        face_locations.append((x, y, x + w, y + h))
                except Exception as e:
                    logger.warning(f"OpenCV detection failed: {e}")
            
            logger.info(f"Detected {len(face_locations)} faces")
            return face_locations
            
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            return []
    
    def extract_face_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """Extract real face embedding using InsightFace or OpenCV fallback"""
        if not self.initialized:
            logger.warning("AI models not initialized for embedding extraction")
            return None
        
        try:
            # Try InsightFace first
            if self.face_recognition_model:
                try:
                    # Ensure face image is in the right format
                    if len(face_img.shape) == 3:
                        face_img_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                    else:
                        face_img_rgb = face_img
                    
                    # Extract embedding using InsightFace
                    faces = self.face_recognition_model.get(face_img_rgb)
                    if faces and len(faces) > 0:
                        embedding = faces[0].embedding
                        logger.info(f"Face embedding extracted successfully using InsightFace, shape: {embedding.shape}")
                        return embedding
                    else:
                        logger.warning("No face detected in image for embedding extraction")
                except Exception as e:
                    logger.warning(f"InsightFace embedding failed: {e}, using OpenCV fallback")
            
            # OpenCV fallback for embedding extraction
            if self.face_detector:
                try:
                    # Resize face image to standard size
                    face_img_resized = cv2.resize(face_img, (64, 64))
                    
                    # Convert to grayscale
                    face_gray = cv2.cvtColor(face_img_resized, cv2.COLOR_BGR2GRAY)
                    
                    # Extract basic features (histogram + edge features)
                    # Histogram features
                    hist = cv2.calcHist([face_gray], [0], None, [256], [0, 256])
                    hist = hist.flatten() / hist.sum()  # Normalize
                    
                    # Edge features using Sobel
                    sobel_x = cv2.Sobel(face_gray, cv2.CV_64F, 1, 0, ksize=3)
                    sobel_y = cv2.Sobel(face_gray, cv2.CV_64F, 0, 1, ksize=3)
                    edge_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
                    edge_features = cv2.resize(edge_magnitude, (16, 16)).flatten()
                    edge_features = edge_features / (edge_features.max() + 1e-8)  # Normalize
                    
                    # Combine features
                    embedding = np.concatenate([hist, edge_features])
                    
                    logger.info(f"Face embedding extracted using OpenCV fallback, shape: {embedding.shape}")
                    return embedding
                    
                except Exception as e:
                    logger.error(f"OpenCV fallback embedding failed: {e}")
                    return None
            
            logger.warning("No embedding method available")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting face embedding: {e}")
            return None
    
    def compare_faces(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Real face comparison using cosine similarity"""
        try:
            if embedding1 is None or embedding2 is None:
                return 0.0
            
            # Normalize embeddings
            embedding1_norm = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
            embedding2_norm = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1_norm, embedding2_norm)
            confidence = (similarity + 1) / 2  # Convert from [-1, 1] to [0, 1]
            
            logger.info(f"Face comparison confidence: {confidence:.3f}")
            return float(confidence)
            
        except Exception as e:
            logger.error(f"Error comparing faces: {e}")
            return 0.0
    
    def recognize_face(self, face_img: np.ndarray) -> Optional[Dict]:
        """
        Real face recognition against known faces using embedding comparison
        
        Process:
        1. Extract embedding from live face image
        2. Compare against all stored student embeddings using cosine similarity
        3. Return best match if similarity > 0.7 threshold
        
        Returns:
            dict with student_id and confidence if recognized, None otherwise
            
        No model retraining: Direct embedding comparison for real-time recognition
        """
        try:
            # Extract embedding from the face image
            embedding = self.extract_face_embedding(face_img)
            if embedding is None:
                return None
            
            best_match = None
            best_confidence = 0.0
            
            # Compare with all known faces using cosine similarity
            for student_id, known_embedding in self.known_faces.items():
                confidence = self.compare_faces(embedding, known_embedding)
                if confidence > best_confidence and confidence > 0.7:  # Recognition threshold
                    best_confidence = confidence
                    best_match = student_id
            
            if best_match:
                logger.info(f"Face recognized as student {best_match} with confidence {best_confidence:.3f}")
                return {
                    'student_id': best_match,
                    'confidence': best_confidence
                }
            else:
                logger.info("Face not recognized (no match above 0.7 threshold)")
                return None
                
        except Exception as e:
            logger.error(f"Error in face recognition: {e}")
            return None


# Create real instance
face_recognition_system = RealFaceRecognitionSystem()


class RealLivenessDetectionSystem:
    """Real implementation of liveness detection system using InsightFace with OpenCV fallback"""
    
    def __init__(self):
        self.initialized = False
        self.face_recognition_model = None
        self.face_detector = None  # OpenCV fallback
        logger.info("Real liveness detection system initialized")
    
    def initialize_models(self):
        """Initialize real liveness detection models with fallbacks"""
        try:
            # Try to initialize InsightFace
            try:
                import insightface
                from insightface.app import FaceAnalysis
                
                self.face_recognition_model = FaceAnalysis(name='buffalo_l')
                try:
                    self.face_recognition_model.prepare(ctx_id=0, det_size=(640, 640))
                except Exception as gpu_e:
                    logger.warning(f"GPU not available for InsightFace ({gpu_e}), falling back to CPU")
                    self.face_recognition_model.prepare(ctx_id=-1, det_size=(640, 640))
                logger.info("Liveness detection models initialized with InsightFace")
                
            except ImportError:
                logger.warning("InsightFace not available, using OpenCV fallback")
                self.face_recognition_model = None
            except Exception as e:
                logger.warning(f"InsightFace initialization failed: {e}, using OpenCV fallback")
                self.face_recognition_model = None
            
            # Initialize OpenCV fallback
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_detector = cv2.CascadeClassifier(cascade_path)
                if self.face_detector.empty():
                    logger.warning("OpenCV face cascade not loaded")
                    self.face_detector = None
                else:
                    logger.info("OpenCV face detector initialized as fallback")
            except Exception as e:
                logger.error(f"Failed to load OpenCV face detector: {e}")
                self.face_detector = None
            
            self.initialized = True
            logger.info("Liveness detection models initialized with fallbacks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize liveness detection models: {e}")
            self.initialized = False
            return False
    
    def detect_liveness(self, frame: np.ndarray, position: str) -> Dict:
        """Real liveness detection using InsightFace or OpenCV fallback"""
        if not self.initialized:
            return {
                'is_live': False,
                'confidence': 0.0,
                'position': position,
                'timestamp': time.time(),
                'error': 'Models not initialized'
            }
        
        try:
            def estimate_yaw_using_landmarks(face_obj) -> float:
                try:
                    # face_obj.kps: array of 5 landmarks [ (x_eye_left,y), (x_eye_right,y), (x_nose,y), (x_mouth_left,y), (x_mouth_right,y) ]
                    kps = getattr(face_obj, 'kps', None)
                    if kps is None:
                        return 0.0
                    eye_left_x, eye_left_y = kps[0]
                    eye_right_x, eye_right_y = kps[1]
                    nose_x, nose_y = kps[2]
                    eye_mid_x = (eye_left_x + eye_right_x) / 2.0
                    eye_dist = max(abs(eye_right_x - eye_left_x), 1e-6)
                    # Yaw proxy: normalized horizontal displacement of nose from eye midpoint
                    yaw_norm = (nose_x - eye_mid_x) / eye_dist
                    return float(yaw_norm)
                except Exception:
                    return 0.0

            def evaluate_expected_pose(yaw_norm: float, expected: str) -> (bool, float, str):
                # thresholds tuned empirically; positive yaw_norm => head turned right (from camera perspective)
                center_thresh = 0.15
                side_thresh = 0.25
                detected = 'center'
                if yaw_norm > side_thresh:
                    detected = 'right'
                elif yaw_norm < -side_thresh:
                    detected = 'left'
                # Match expected
                if expected == 'center':
                    ok = abs(yaw_norm) <= center_thresh
                    conf = max(0.0, 1.0 - abs(yaw_norm) / (center_thresh + 1e-6))
                elif expected == 'left':
                    ok = yaw_norm < -side_thresh
                    conf = min(1.0, max(0.0, (-yaw_norm - side_thresh) / (0.5)))
                elif expected == 'right':
                    ok = yaw_norm > side_thresh
                    conf = min(1.0, max(0.0, (yaw_norm - side_thresh) / (0.5)))
                else:
                    ok = False
                    conf = 0.0
                return ok, float(conf), detected

            # Try InsightFace first
            if self.face_recognition_model:
                try:
                    # Convert to RGB for InsightFace
                    if len(frame.shape) == 3:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    else:
                        frame_rgb = frame
                    
                    # Analyze face for liveness
                    faces = self.face_recognition_model.get(frame_rgb)
                    
                    if faces and len(faces) > 0:
                        face = faces[0]
                        # Estimate yaw/pose and validate expected step
                        yaw_norm = estimate_yaw_using_landmarks(face)
                        ok, conf, detected_pose = evaluate_expected_pose(yaw_norm, position)
                        logger.info(f"Liveness step '{position}': detected_pose={detected_pose}, yaw_norm={yaw_norm:.3f}, ok={ok}")
                        return {
                            'is_live': ok,
                            'confidence': conf,
                            'position': position,
                            'detected_pose': detected_pose,
                            'timestamp': time.time()
                        }
                    else:
                        logger.warning(f"No face detected for liveness detection at {position}")
                        return {
                            'is_live': False,
                            'confidence': 0.0,
                            'position': position,
                            'timestamp': time.time(),
                            'error': 'No face detected'
                        }
                        
                except Exception as e:
                    logger.warning(f"InsightFace liveness detection failed: {e}, using OpenCV fallback")
            
            # OpenCV fallback for liveness detection
            if self.face_detector:
                try:
                    # Convert to grayscale
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    
                    # Detect faces
                    faces = self.face_detector.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
                    
                    if len(faces) == 0:
                        return {
                            'is_live': False,
                            'confidence': 0.0,
                            'position': position,
                            'timestamp': time.time(),
                            'error': 'No face detected'
                        }
                    
                    # Without landmarks, we cannot reliably validate head turn; only allow center
                    ok = (position == 'center')
                    conf = 0.6 if ok else 0.0
                    logger.info(f"Liveness step '{position}' (OpenCV fallback): ok={ok}")
                    return {
                        'is_live': ok,
                        'confidence': conf,
                        'position': position,
                        'timestamp': time.time()
                    }
                    
                except Exception as e:
                    logger.error(f"OpenCV fallback liveness detection failed: {e}")
            
            return {
                'is_live': False,
                'confidence': 0.0,
                'position': position,
                'timestamp': time.time(),
                'error': 'No liveness detection method available'
            }
            
        except Exception as e:
            logger.error(f"Error in liveness detection: {e}")
            return {
                'is_live': False,
                'confidence': 0.0,
                'position': position,
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def verify_movement(self, session_data: Dict) -> Dict:
        """Verify movement patterns for liveness"""
        try:
            # Check if all three positions are captured
            required_positions = ['center', 'left', 'right']
            captured_positions = []
            
            for pos in required_positions:
                if session_data.get(f'{pos}_embedding'):
                    captured_positions.append(pos)
            
            if len(captured_positions) < 3:
                return {
                    'movement_verified': False,
                    'confidence': 0.0,
                    'timestamp': time.time(),
                    'error': f'Missing positions: {set(required_positions) - set(captured_positions)}'
                }
            
            # Calculate movement verification score
            movement_score = 0.8  # Base score for having all positions
            
            # Additional checks can be added here
            # For now, we'll use a simple approach
            
            logger.info(f"Movement verification completed: score {movement_score:.3f}")
            
            return {
                'movement_verified': movement_score > 0.7,
                'confidence': movement_score,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error in movement verification: {e}")
            return {
                'movement_verified': False,
                'confidence': 0.0,
                'timestamp': time.time(),
                'error': str(e)
            }


# Create real instance
liveness_detection_system = RealLivenessDetectionSystem()
