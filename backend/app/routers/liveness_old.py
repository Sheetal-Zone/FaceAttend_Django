from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import json
import numpy as np
import cv2
import base64
import uuid
from datetime import datetime, timedelta
from app.auth import get_current_admin
from app.database import get_db
from app.models import Student, LivenessDetectionSession
from app.schemas import (
    LivenessDetectionSessionCreate, LivenessDetectionSession as LivenessSessionSchema,
    LivenessDetectionRequest, LivenessDetectionResponse,
    LivenessVerificationRequest, LivenessVerificationResponse,
    StudentRegistrationWithLiveness, APIResponse
)
from app.liveness_detection import liveness_detection_engine
import logging

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
        
        logger.info(f"Created liveness detection session: {session_id}")
        
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


@router.post("/detect", response_model=APIResponse)
async def detect_liveness(
    request: LivenessDetectionRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Detect liveness from captured frame"""
    try:
        logger.info(f"POST /api/v1/liveness/detect by user '{current_admin}' - Processing liveness detection")
        
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
        
        logger.info(f"Liveness detection result: {result}")
        
        return {
            "success": True,
            "message": "Liveness detection completed",
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in liveness detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error in liveness detection: {str(e)}"
        )


@router.post("/detect", response_model=LivenessDetectionResponse)
async def process_liveness_frame(
    request: LivenessDetectionRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Process a frame for liveness detection"""
    try:
        # Get session
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == request.session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liveness detection session not found"
            )
        
        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            session.status = "EXPIRED"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Liveness detection session has expired"
            )
        
        # Check if session is already completed
        if session.status in ["COMPLETED", "FAILED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Liveness detection session is already {session.status.lower()}"
            )
        
        # Update session status
        if session.status == "PENDING":
            session.status = "IN_PROGRESS"
            db.commit()
        
        # Decode base64 image
        try:
            image_data = base64.b64decode(request.frame_data)
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image data: {str(e)}"
            )
        
        # Process frame for liveness detection
        result = liveness_detection_engine.process_frame_for_liveness(frame, request.position)
        
        if result['success']:
            # Store the processed data
            if request.position == "center":
                session.center_frame_data = result['frame_data']
                session.center_embedding = json.dumps(result['embedding'])
                session.center_verified = True
            elif request.position == "left":
                session.left_frame_data = result['frame_data']
                session.left_embedding = json.dumps(result['embedding'])
                session.left_verified = True
            elif request.position == "right":
                session.right_frame_data = result['frame_data']
                session.right_embedding = json.dumps(result['embedding'])
                session.right_verified = True
            
            session.attempts_count += 1
            db.commit()
            
            logger.info(f"Successfully processed {request.position} frame for session {request.session_id}")
            
            return LivenessDetectionResponse(
                success=True,
                message=f"Successfully processed {request.position} position",
                position=request.position,
                verified=True
            )
        else:
            session.attempts_count += 1
            session.error_message = result['error']
            db.commit()
            
            logger.warning(f"Failed to process {request.position} frame: {result['error']}")
            
            return LivenessDetectionResponse(
                success=False,
                message=result['error'],
                position=request.position,
                verified=False,
                error=result['error']
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing liveness frame: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing liveness frame: {str(e)}"
        )


@router.post("/verify", response_model=LivenessVerificationResponse)
async def verify_liveness_completion(
    request: LivenessVerificationRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Verify liveness detection completion"""
    try:
        # Get session
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == request.session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liveness detection session not found"
            )
        
        # Check if all positions are verified
        if not all([session.center_verified, session.left_verified, session.right_verified]):
            missing_positions = []
            if not session.center_verified:
                missing_positions.append("center")
            if not session.left_verified:
                missing_positions.append("left")
            if not session.right_verified:
                missing_positions.append("right")
            
            return LivenessVerificationResponse(
                success=False,
                message=f"Missing positions: {', '.join(missing_positions)}",
                error=f"Please complete all positions: {', '.join(missing_positions)}"
            )
        
        # Complete liveness verification
        center_data = {
            'success': True,
            'embedding': json.loads(session.center_embedding)
        }
        left_data = {
            'success': True,
            'embedding': json.loads(session.left_embedding)
        }
        right_data = {
            'success': True,
            'embedding': json.loads(session.right_embedding)
        }
        
        verification_result = liveness_detection_engine.complete_liveness_verification(
            center_data, left_data, right_data
        )
        
        if verification_result['success']:
            # Update session with final results
            session.liveness_score = verification_result['liveness_score']
            session.movement_verified = verification_result['movement_verified']
            session.final_embedding = json.dumps(verification_result['final_embedding'])
            session.status = "COMPLETED"
            session.completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Liveness verification completed successfully for session {request.session_id}")
            
            return LivenessVerificationResponse(
                success=True,
                message="Liveness verification completed successfully",
                liveness_score=verification_result['liveness_score'],
                movement_verified=verification_result['movement_verified'],
                final_embedding=json.dumps(verification_result['final_embedding'])
            )
        else:
            # Mark session as failed
            session.status = "FAILED"
            session.error_message = verification_result['error']
            session.completed_at = datetime.utcnow()
            db.commit()
            
            logger.warning(f"Liveness verification failed for session {request.session_id}: {verification_result['error']}")
            
            return LivenessVerificationResponse(
                success=False,
                message="Liveness verification failed",
                error=verification_result['error']
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying liveness completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying liveness completion: {str(e)}"
        )


@router.post("/register-student", response_model=APIResponse)
async def register_student_with_liveness(
    student_data: StudentRegistrationWithLiveness,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Register a new student using completed liveness detection"""
    try:
        # Check if student with roll number already exists
        existing_student = db.query(Student).filter(Student.roll_number == student_data.roll_number).first()
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student with this roll number already exists"
            )
        
        # Get completed liveness session
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == student_data.session_id,
            LivenessDetectionSession.status == "COMPLETED"
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Completed liveness detection session not found"
            )
        
        # Create student with liveness verification
        student = Student(
            name=student_data.name,
            roll_number=student_data.roll_number,
            embedding_vector=session.final_embedding,
            liveness_verified=True,
            liveness_verification_date=session.completed_at,
            liveness_confidence_score=session.liveness_score
        )
        
        db.add(student)
        db.commit()
        db.refresh(student)
        
        # Update session with student reference
        session.student_id = student.id
        db.commit()
        
        logger.info(f"Student {student.name} registered successfully with liveness verification")
        
        return {
            "success": True,
            "message": f"Student {student.name} registered successfully with liveness verification",
            "data": {
                "student_id": student.id,
                "liveness_score": session.liveness_score,
                "verification_date": session.completed_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering student with liveness: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering student: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=LivenessSessionSchema)
async def get_liveness_session(
    session_id: str,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get liveness detection session details"""
    try:
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liveness detection session not found"
            )
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting liveness session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving liveness session: {str(e)}"
        )
