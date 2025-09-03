"""
Face Detection Router
"""

import logging
import base64
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.schemas import APIResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/face", tags=["Face Detection"])


class FaceDetectionRequest(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")


class FaceDetectionResponse(BaseModel):
    success: bool
    message: str
    faces: list = []
    processing_time: float = 0.0


@router.post("/detect", response_model=FaceDetectionResponse)
async def detect_faces(
    request: FaceDetectionRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Detect faces in an image"""
    import time
    start_time = time.time()
    
    try:
        logger.info(f"POST /api/v1/face/detect by user '{current_admin}' - Processing face detection")
        
        # Convert base64 image to numpy array
        try:
            # Decode base64 image
            image_data = base64.b64decode(request.image_data)
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                raise ValueError("Invalid image data")
                
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image data"
            )
        
        # Initialize face recognition system if not already done
        from app.ai_models import face_recognition_system
        if not face_recognition_system.initialized:
            face_recognition_system.initialize_models()
        
        # Detect faces
        face_locations = face_recognition_system.detect_faces(frame)
        
        # Format results
        faces = []
        for i, (x1, y1, x2, y2) in enumerate(face_locations):
            faces.append({
                "face_id": i,
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "width": int(x2 - x1),
                "height": int(y2 - y1),
                "confidence": 0.9  # YOLO confidence would be available here
            })
        
        processing_time = time.time() - start_time
        
        logger.info(f"Face detection completed: {len(faces)} faces found in {processing_time:.3f}s")
        
        return FaceDetectionResponse(
            success=True,
            message=f"Detected {len(faces)} faces",
            faces=faces,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in face detection: {str(e)}"
        )


@router.post("/recognize", response_model=APIResponse)
async def recognize_faces(
    request: FaceDetectionRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Recognize faces against known students"""
    import time
    start_time = time.time()
    
    try:
        logger.info(f"POST /api/v1/face/recognize by user '{current_admin}' - Processing face recognition")
        
        # Convert base64 image to numpy array
        try:
            # Decode base64 image
            image_data = base64.b64decode(request.image_data)
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                raise ValueError("Invalid image data")
                
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image data"
            )
        
        # Initialize face recognition system if not already done
        from app.ai_models import face_recognition_system
        if not face_recognition_system.initialized:
            face_recognition_system.initialize_models()
        
        # Detect and recognize faces
        face_locations = face_recognition_system.detect_faces(frame)
        
        matches = []
        for (x1, y1, x2, y2) in face_locations:
            # Extract face region
            face_img = frame[y1:y2, x1:x2]
            
            # Extract embedding
            embedding = face_recognition_system.extract_face_embedding(face_img)
            
            if embedding is not None:
                # Find best match
                best_match = face_recognition_system.find_best_match(embedding)
                
                if best_match:
                    logger.info(f"Match found student_id={best_match['student_id']} confidence={best_match['confidence']:.3f}")
                    matches.append({
                        "student_id": best_match["student_id"],
                        "confidence": best_match["confidence"],
                        "bbox": [int(x1), int(y1), int(x2), int(y2)]
                    })
                else:
                    logger.info("Embedding did not match any known student")
            else:
                logger.info("No embedding extracted for detected face region")
        
        processing_time = time.time() - start_time
        
        logger.info(f"Face recognition completed: {len(matches)} matches found in {processing_time:.3f}s")
        
        return {
            "success": True,
            "message": f"Recognized {len(matches)} faces",
            "data": {
                "matches": matches,
                "processing_time": processing_time
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in face recognition: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in face recognition: {str(e)}"
        )
