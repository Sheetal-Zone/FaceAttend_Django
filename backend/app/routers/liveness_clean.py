"""
Liveness Detection Router - Clean version without duplicates
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_admin
from app.database import get_db
from app.models import LivenessDetectionSession
from app.schemas import (
    APIResponse,
    LivenessDetectionRequest,
    LivenessDetectionSessionCreate,
    LivenessDetectionResponse,
    LivenessVerificationRequest,
    LivenessVerificationResponse,
    StudentRegistrationWithLiveness,
    LivenessSessionSchema
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/liveness", tags=["Liveness Detection"])


@router.post("/session", response_model=APIResponse)
async def create_liveness_session(
    session_data: LivenessDetectionSessionCreate,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new liveness detection session"""
    try:
        logger.info(f"POST /api/v1/liveness/session by user '{current_admin}' - Creating new liveness session")
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Set expiration time (10 minutes from now)
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Create session
        session = LivenessDetectionSession(
            session_id=session_id,
            student_id=session_data.student_id,
            status="PENDING",
            expires_at=expires_at
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        logger.info(f"Created liveness detection session: {session_id} (expires: {expires_at.isoformat()})")
        
        return {
            "success": True,
            "message": "Liveness detection session created successfully",
            "data": {
                "session_id": session_id,
                "expires_at": expires_at.isoformat(),
                "status": "PENDING"
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating liveness session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating liveness session: {str(e)}"
        )


@router.post("/detect", response_model=LivenessDetectionResponse)
async def detect_liveness(
    request: LivenessDetectionRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Detect liveness from captured frame"""
    try:
        logger.info(f"POST /api/v1/liveness/detect by user '{current_admin}' - Processing liveness detection for session {request.session_id}")
        
        # Verify session exists and is valid
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == request.session_id
        ).first()
        
        if not session:
            logger.warning(f"Invalid session ID: {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.expires_at < datetime.utcnow():
            logger.warning(f"Expired session: {request.session_id}")
            session.status = "EXPIRED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Session expired"
            )
        
        # Process liveness detection
        from app.ai_models import liveness_detection_system
        
        # Convert base64 image to numpy array
        import base64
        import cv2
        import numpy as np
        
        try:
            # Decode base64 image
            image_data = base64.b64decode(request.frame_data)
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
        
        # Perform liveness detection
        result = liveness_detection_system.detect_liveness(frame, request.position)
        
        logger.info(f"Liveness detection result for session {request.session_id}: {result}")
        
        # Update session with frame data
        if request.position == "center":
            session.center_frame_data = request.frame_data
        elif request.position == "left":
            session.left_frame_data = request.frame_data
        elif request.position == "right":
            session.right_frame_data = request.frame_data
        
        # Update session status based on result
        if result.get("is_live", False):
            session.status = "COMPLETED"
            session.liveness_score = result.get("confidence", 0.0)
        else:
            session.status = "FAILED"
            session.liveness_score = result.get("confidence", 0.0)
        
        db.commit()
        
        return LivenessDetectionResponse(
            success=True,
            message="Liveness detection completed",
            is_live=result.get("is_live", False),
            confidence_score=result.get("confidence", 0.0),
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in liveness detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in liveness detection: {str(e)}"
        )


@router.post("/verify", response_model=LivenessVerificationResponse)
async def verify_liveness_completion(
    request: LivenessVerificationRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Verify liveness detection completion"""
    try:
        logger.info(f"POST /api/v1/liveness/verify by user '{current_admin}' - Verifying session {request.session_id}")
        
        # Get session
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == request.session_id
        ).first()
        
        if not session:
            logger.warning(f"Session not found: {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liveness detection session not found"
            )
        
        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            session.status = "EXPIRED"
            db.commit()
            logger.warning(f"Session expired: {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Liveness detection session has expired"
            )
        
        logger.info(f"Session verification result: {session.status} (score: {session.liveness_score})")
        
        return LivenessVerificationResponse(
            success=True,
            message="Liveness verification completed",
            is_completed=session.status == "COMPLETED",
            liveness_score=session.liveness_score or 0.0,
            status=session.status,
            timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying liveness completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying liveness completion: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=LivenessSessionSchema)
async def get_liveness_session(
    session_id: str,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get liveness detection session details"""
    try:
        logger.info(f"GET /api/v1/liveness/session/{session_id} by user '{current_admin}'")
        
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == session_id
        ).first()
        
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liveness detection session not found"
            )
        
        logger.info(f"Retrieved session: {session_id} (status: {session.status})")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving liveness session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving liveness session: {str(e)}"
        )
