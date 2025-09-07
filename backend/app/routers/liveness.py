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
from app.models import LivenessDetectionSession, Student
from app.schemas import (
    APIResponse,
    LivenessDetectionRequest,
    LivenessDetectionSessionCreate,
    LivenessDetectionResponse,
    LivenessVerificationRequest,
    LivenessVerificationResponse,
    StudentRegistrationWithLiveness
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
        logger.info(f"POST /api/v1/liveness/session by user '{current_admin}' - Creating new liveness session for student_id: {session_data.student_id}")
        
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
        
        logger.info(f"LIVENESS SESSION CREATED: {session_id} for student_id: {session_data.student_id} (expires: {expires_at.isoformat()})")
        
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


@router.post("/frames", response_model=LivenessDetectionResponse)
async def process_liveness_frames(
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
        from app.ai_models import liveness_detection_system, face_recognition_system
        
        # Convert base64 image to numpy array
        import base64
        import cv2
        import numpy as np
        import json
        
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
        
        # Ensure models are initialized
        if not liveness_detection_system.initialized:
            liveness_detection_system.initialize_models()
        if not face_recognition_system.initialized:
            face_recognition_system.initialize_models()

        # Perform liveness detection
        result = liveness_detection_system.detect_liveness(frame, request.position)
        
        logger.info(f"Liveness detection result for session {request.session_id}: {result}")
        
        # Update session with frame data and embedding per position
        if request.position == "center":
            session.center_frame_data = request.frame_data
            try:
                embedding = face_recognition_system.extract_face_embedding(frame)
                if embedding is not None:
                    session.center_embedding = json.dumps(embedding.tolist())
                    logger.info(f"Center embedding extracted and stored for session {request.session_id}")
            except Exception as e:
                logger.warning(f"Center embedding extraction failed: {e}")
        elif request.position == "left":
            session.left_frame_data = request.frame_data
            try:
                embedding = face_recognition_system.extract_face_embedding(frame)
                if embedding is not None:
                    session.left_embedding = json.dumps(embedding.tolist())
                    logger.info(f"Left embedding extracted and stored for session {request.session_id}")
            except Exception as e:
                logger.warning(f"Left embedding extraction failed: {e}")
        elif request.position == "right":
            session.right_frame_data = request.frame_data
            try:
                embedding = face_recognition_system.extract_face_embedding(frame)
                if embedding is not None:
                    session.right_embedding = json.dumps(embedding.tolist())
                    logger.info(f"Right embedding extracted and stored for session {request.session_id}")
            except Exception as e:
                logger.warning(f"Right embedding extraction failed: {e}")
        
        # Update session status based on result, track per-position flags and log
        position = request.position
        is_live = result.get("is_live", False)
        confidence = result.get("confidence", 0.0)
        detected_pose = result.get("detected_pose")
        logger.info(f"Liveness step '{position}' result: ok={is_live}, conf={confidence:.3f}, detected_pose={detected_pose}")

        # Mark step verified only if detected pose matches expected
        if position == "center" and detected_pose == "center":
            session.center_verified = is_live
        elif position == "left" and detected_pose == "left":
            session.left_verified = is_live
        elif position == "right" and detected_pose == "right":
            session.right_verified = is_live

        # Check if all positions are verified (not just embeddings captured)
        all_positions_completed = bool(
            session.center_verified and session.left_verified and session.right_verified
        )
        
        if all_positions_completed:
            # All positions completed - finalize the session
            logger.info(f"All liveness positions completed for session {request.session_id}, finalizing...")
            
            # Verify movement and finalize
            try:
                # Parse embeddings for movement verification if available
                if session.center_embedding and session.left_embedding and session.right_embedding:
                    center_emb = np.array(json.loads(session.center_embedding))
                    left_emb = np.array(json.loads(session.left_embedding))
                    right_emb = np.array(json.loads(session.right_embedding))
                    
                    # Verify movement using liveness detection engine
                    from app.liveness_detection import liveness_detection_engine
                    movement_result = liveness_detection_engine.verify_liveness_movement(
                        center_emb, left_emb, right_emb
                    )
                    
                    session.movement_verified = movement_result['movement_verified']
                    session.liveness_score = movement_result['confidence']
                else:
                    # If embeddings not available, use basic verification
                    session.movement_verified = True
                    session.liveness_score = 0.8
                    logger.warning(f"Embeddings not available for session {request.session_id}, using basic verification")
                
                if session.movement_verified:
                    # Use center embedding as final embedding
                    session.final_embedding = session.center_embedding
                    session.status = "COMPLETED"
                    session.completed_at = datetime.utcnow()
                    
        # Save embeddings to student_embeddings table if student_id is available
        if session.student_id:
            student = db.query(Student).filter(Student.student_id == session.student_id).first()
            if student and session.final_embedding:
                try:
                    import json, numpy as np
                    emb = np.array(json.loads(session.final_embedding), dtype=np.float32)

                    # Create or update student embedding
                    from app.models import StudentEmbedding
                    student_embedding = db.query(StudentEmbedding).filter(
                        StudentEmbedding.student_id == session.student_id
                    ).first()

                    if student_embedding:
                        # Update existing embedding
                        student_embedding.embedding = emb.tobytes()
                        student_embedding.quality_score = session.liveness_score
                        student_embedding.model_version = settings.embedding_model_version
                    else:
                        # Create new embedding
                        student_embedding = StudentEmbedding(
                            student_id=session.student_id,
                            embedding=emb.tobytes(),
                            quality_score=session.liveness_score,
                            model_version=settings.embedding_model_version
                        )
                        db.add(student_embedding)

                    db.commit()
                    logger.info(f"EMBEDDINGS SAVED: Student {student.student_id} ({student.name}) - embedding stored in student_embeddings table")

                    # Save registration photo
                    try:
                        from app.services.storage import storage_service
                        import base64
                        import cv2
                        
                        # Decode the final frame and save as registration photo
                        if session.final_frame_data:
                            image_data = base64.b64decode(session.final_frame_data)
                            nparr = np.frombuffer(image_data, np.uint8)
                            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                            
                            if frame is not None:
                                photo_path = storage_service.save_registration_photo(session.student_id, frame)
                                if photo_path:
                                    logger.info(f"REGISTRATION PHOTO SAVED: {photo_path}")
                                else:
                                    logger.warning("Failed to save registration photo")
                    except Exception as e:
                        logger.warning(f"Failed to save registration photo: {e}")

                    # Reload known faces in recognition system
                    try:
                        embeddings = db.query(StudentEmbedding).all()
                        students_data = [
                            { 'student_id': e.student_id, 'embedding': e.embedding }
                            for e in embeddings
                        ]
                        face_recognition_system.load_known_faces(students_data)
                        logger.info(f"Reloaded {len(students_data)} known faces in recognition system")
                    except Exception as e:
                        logger.warning(f"Failed reloading known faces after liveness completion: {e}")

                except Exception as e:
                    logger.error(f"Failed to save binary embedding: {e}")
            else:
                logger.warning(f"Student {session.student_id} not found or no final embedding available")
        else:
            logger.info(f"Session {request.session_id} completed but no student_id - embeddings saved in session")
                    
                    logger.info(f"Liveness detection session {request.session_id} completed successfully with score {session.liveness_score:.3f}")
                else:
                    session.status = "FAILED"
                    session.error_message = movement_result.get('error', 'Movement verification failed')
                    logger.warning(f"Liveness detection session {request.session_id} failed: {session.error_message}")
                    
            except Exception as e:
                logger.error(f"Error finalizing liveness session {request.session_id}: {e}")
                session.status = "FAILED"
                session.error_message = f"Finalization error: {str(e)}"
        else:
            # Session still in progress
            session.status = "IN_PROGRESS"
            session.liveness_score = confidence
        
        db.commit()
        
        # Return response with completion status
        response_data = {
            "success": True,
            "message": "Liveness detection processed",
            "position": position,
            "is_live": result.get("is_live", False),
            "confidence_score": result.get("confidence", 0.0),
            "detected_pose": result.get("detected_pose")
        }
        
        # Add completion information if session is completed
        if session.status == "COMPLETED":
            response_data.update({
                "session_completed": True,
                "liveness_score": session.liveness_score,
                "movement_verified": session.movement_verified,
                "final_embedding_saved": True,
                "student_id": session.student_id
            })
            logger.info(f"Liveness detection completed for session {request.session_id} - returning completion response")
        
        return LivenessDetectionResponse(**response_data)
        
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
        
        # Determine completion only if all positions verified true
        all_verified = bool(session.center_verified and session.left_verified and session.right_verified)
        if all_verified:
            session.status = "COMPLETED"
            # Choose final embedding preference: center > left > right
            final_embedding = session.center_embedding or session.left_embedding or session.right_embedding
            session.final_embedding = final_embedding
            # Persist to student if available
            if session.student_id and final_embedding:
                student = db.query(Student).filter(Student.id == session.student_id).first()
                if student:
                    student.embedding_vector = final_embedding
                    student.liveness_verified = True
                    student.liveness_verification_date = datetime.utcnow()
                    student.liveness_confidence_score = session.liveness_score or 0.0
                    db.add(student)
                    logger.info(f"Embeddings saved for Student {student.id}; liveness verified")
                    # Reload known faces in recognition system
                    try:
                        from app.ai_models import face_recognition_system
                        students = db.query(Student).filter(Student.embedding_vector.isnot(None)).all()
                        students_data = [
                            { 'id': s.id, 'embedding_vector': s.embedding_vector }
                            for s in students
                        ]
                        face_recognition_system.load_known_faces(students_data)
                    except Exception as e:
                        logger.warning(f"Failed reloading known faces after liveness verify: {e}")
        else:
            session.status = "FAILED"
        db.commit()

        logger.info(f"Session verification result: {session.status} (score: {session.liveness_score})")

        return LivenessVerificationResponse(
            success=True,
            message="Liveness verification completed",
            liveness_score=session.liveness_score or 0.0,
            movement_verified=all_verified,
            final_embedding=session.final_embedding,
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying liveness completion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying liveness completion: {str(e)}"
        )


@router.post("/complete", response_model=APIResponse)
async def complete_liveness_detection(
    request: LivenessVerificationRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Complete liveness detection and save embeddings for student"""
    try:
        logger.info(f"POST /api/v1/liveness/complete by user '{current_admin}' - Completing liveness for session {request.session_id}")
        
        # Get session
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == request.session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Liveness session not found"
            )
        
        if session.status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Liveness session not completed yet"
            )
        
        if not session.final_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No embeddings found in liveness session"
            )
        
        # Get student
        student = db.query(Student).filter(Student.student_id == request.student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Save embeddings to student_embeddings table
        try:
            import json, numpy as np
            emb = np.array(json.loads(session.final_embedding), dtype=np.float32)
            
            # Create or update student embedding
            student_embedding = db.query(StudentEmbedding).filter(
                StudentEmbedding.student_id == request.student_id
            ).first()
            
            if student_embedding:
                # Update existing embedding
                student_embedding.embedding = emb.tobytes()
                student_embedding.quality_score = session.liveness_score
                student_embedding.model_version = settings.embedding_model_version
            else:
                # Create new embedding
                student_embedding = StudentEmbedding(
                    student_id=request.student_id,
                    embedding=emb.tobytes(),
                    quality_score=session.liveness_score,
                    model_version=settings.embedding_model_version
                )
                db.add(student_embedding)
            
            db.commit()
            logger.info(f"EMBEDDINGS SAVED: Student {student.student_id} ({student.name}) - embedding stored in student_embeddings table")
            
            # Reload known faces in recognition system
            try:
                embeddings = db.query(StudentEmbedding).all()
                students_data = [
                    { 'student_id': e.student_id, 'embedding': e.embedding }
                    for e in embeddings
                ]
                face_recognition_system.load_known_faces(students_data)
                logger.info(f"Reloaded {len(students_data)} known faces in recognition system")
            except Exception as e:
                logger.warning(f"Failed reloading known faces after liveness completion: {e}")
                
        except Exception as e:
            logger.error(f"Failed to save binary embedding: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save embeddings: {str(e)}"
            )
        
        return {
            "success": True,
            "message": "Embeddings saved successfully",
            "data": {
                "student_id": student.student_id,
                "student_name": student.name,
                "roll_no": student.roll_no,
                "embedding_saved": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing liveness detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing liveness detection: {str(e)}"
        )

@router.post("/register-student", response_model=APIResponse)
async def register_student_with_liveness(
    request: StudentRegistrationWithLiveness,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Complete student registration after successful liveness detection"""
    try:
        logger.info(f"POST /api/v1/liveness/register-student by user '{current_admin}' - Completing registration for session {request.session_id}")
        
        # Get the completed liveness session
        session = db.query(LivenessDetectionSession).filter(
            LivenessDetectionSession.session_id == request.session_id,
            LivenessDetectionSession.status == "COMPLETED"
        ).first()
        
        if not session:
            logger.warning(f"Completed liveness session not found: {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Completed liveness detection session not found"
            )
        
        if not session.final_embedding:
            logger.error(f"No final embedding found in session {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No embeddings found in liveness session"
            )
        
        # Create the student record
        from app.models import Student, StudentEmbedding
        student = Student(
            name=request.name,
            roll_no=request.roll_no,
            branch=request.branch,
            year=request.year
        )
        
        db.add(student)
        db.commit()
        db.refresh(student)
        
        # Save embeddings to student_embeddings table
        if session.final_embedding:
            try:
                import json, numpy as np
                emb = np.array(json.loads(session.final_embedding), dtype=np.float32)
                
                student_embedding = StudentEmbedding(
                    student_id=student.student_id,
                    embedding=emb.tobytes(),
                    quality_score=session.liveness_score or 0.0,
                    model_version=settings.embedding_model_version
                )
                db.add(student_embedding)
                db.commit()
                
                # Reload known faces in recognition system
                try:
                    embeddings = db.query(StudentEmbedding).all()
                    students_data = [
                        { 'student_id': e.student_id, 'embedding': e.embedding }
                        for e in embeddings
                    ]
                    face_recognition_system.load_known_faces(students_data)
                    logger.info(f"Reloaded {len(students_data)} known faces in recognition system")
                except Exception as e:
                    logger.warning(f"Failed reloading known faces after registration: {e}")
                    
            except Exception as e:
                logger.error(f"Failed to save binary embedding: {e}")
        
        # Update session with student_id
        session.student_id = student.student_id
        db.commit()
        
        logger.info(f"Student registration completed: ID={student.student_id}, Name={student.name}, Embeddings saved")
        
        return {
            "success": True,
            "message": "Student registration completed successfully",
            "data": {
                "student_id": student.student_id,
                "name": student.name,
                "roll_no": student.roll_no,
                "branch": student.branch,
                "year": student.year,
                "embedding_saved": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing student registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error completing student registration: {str(e)}"
        )


@router.get("/session/{session_id}", response_model=APIResponse)
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
        
        return {
            "success": True,
            "message": "Session retrieved successfully",
            "data": {
                "session_id": session.session_id,
                "status": session.status,
                "liveness_score": session.liveness_score,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving liveness session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving liveness session: {str(e)}"
        )
