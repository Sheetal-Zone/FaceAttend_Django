"""
Live Detection Router - Attendance marking only
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Student, StudentEmbedding, AttendanceLog, DetectionLog
from app.ai_models import face_recognition_system
from app.config import settings
from app.auth import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session storage (use Redis in production)
detection_sessions: Dict[str, Dict] = {}

class DetectionStartRequest(BaseModel):
    camera_source: Optional[str] = "webcam"

class DetectionStartResponse(BaseModel):
    session_id: str
    message: str

class FrameData(BaseModel):
    image_data: str  # Base64 encoded image
    session_id: str

class DetectionResponse(BaseModel):
    success: bool
    message: str
    faces_detected: int = 0
    students_recognized: int = 0
    matches: List[Dict] = []
    processing_time_ms: float = 0.0

class DetectionStopRequest(BaseModel):
    session_id: str

@router.post("/start", response_model=DetectionStartResponse)
async def start_detection(
    request: DetectionStartRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Start live detection session"""
    try:
        session_id = str(uuid.uuid4())
        
        # Initialize session
        detection_sessions[session_id] = {
            "started_at": datetime.utcnow(),
            "camera_source": request.camera_source,
            "frames_processed": 0,
            "students_recognized": 0,
            "attendance_marked": 0
        }
        
        logger.info(f"Detection session started: {session_id} by {current_admin}")
        
        return DetectionStartResponse(
            session_id=session_id,
            message="Detection session started successfully"
            )
        
    except Exception as e:
        logger.error(f"Error starting detection session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start detection session: {str(e)}"
        )

@router.post("/frame", response_model=DetectionResponse)
async def process_frame(
    request: FrameData,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Process detection frame and mark attendance"""
    import base64
    import cv2
    import numpy as np
    
    start_time = time.time()
    
    try:
        # Validate session
        if request.session_id not in detection_sessions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID"
            )
        
        session = detection_sessions[request.session_id]
        session["frames_processed"] += 1
        
        # Decode image
        try:
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
        
        # Detect faces
        face_locations = face_recognition_system.detect_faces(frame)
        faces_detected = len(face_locations)
        
        matches = []
        attendance_marked = 0
        
        # Process each detected face
        for (x1, y1, x2, y2) in face_locations:
            # Extract face region
            face_img = frame[y1:y2, x1:x2]
            
            # Extract embedding
            embedding = face_recognition_system.extract_face_embedding(face_img)
            
            if embedding is not None:
                # Find best match
                best_match = face_recognition_system.find_best_match(embedding)
                
                if best_match:
                    student_id = best_match["student_id"]
                    confidence = best_match["confidence"]
                    
                    # Get student details
                    student = db.query(Student).filter(Student.student_id == student_id).first()
                    
                        if student:
                            # Check if attendance already marked today
                            today = datetime.utcnow().date()
                            existing_attendance = db.query(AttendanceLog).filter(
                                AttendanceLog.student_id == student_id,
                                AttendanceLog.detected_at >= today
                            ).first()
                            
                            if not existing_attendance:
                                # Mark attendance
                                attendance_log = AttendanceLog(
                                    student_id=student_id,
                                    confidence=confidence,
                                    camera_source=session["camera_source"]
                                )
                                db.add(attendance_log)
                                attendance_marked += 1
                                
                                logger.info(f"ATTENDANCE MARKED: Student {student_id} ({student.name}) - confidence={confidence:.3f}")
                                
                                # Save detection photo
                                try:
                                    from app.services.storage import storage_service
                                    detection_photo_path = storage_service.save_detection_photo(
                                        student_id, frame, datetime.utcnow()
                                    )
                                    if detection_photo_path:
                                        logger.info(f"DETECTION PHOTO SAVED: {detection_photo_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to save detection photo: {e}")
                            
                            # Add to matches for response
                            matches.append({
                                "student_id": student_id,
                                "student_name": student.name,
                                "roll_no": student.roll_no,
                                "branch": student.branch,
                                "year": student.year,
                                "confidence": confidence,
                                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                                "attendance_marked": not bool(existing_attendance)
                            })
                            
                            session["students_recognized"] += 1
                    else:
                        logger.warning(f"Student {student_id} not found in database")
                else:
                    # Unknown face
                    matches.append({
                        "student_id": None,
                        "student_name": "Unknown",
                        "roll_no": None,
                        "branch": None,
                        "year": None,
                        "confidence": 0.0,
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                        "attendance_marked": False
                    })
        
        # Commit attendance logs
        if attendance_marked > 0:
            db.commit()
            session["attendance_marked"] += attendance_marked
        
        # Log detection statistics
        detection_log = DetectionLog(
            faces_detected=faces_detected,
            students_recognized=len([m for m in matches if m["student_id"]]),
            processing_time=time.time() - start_time,
            camera_source=session["camera_source"]
        )
        db.add(detection_log)
        db.commit()
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Frame processed: {faces_detected} faces, {len(matches)} matches, {attendance_marked} attendance marked")
        
        return DetectionResponse(
            success=True,
            message=f"Processed {faces_detected} faces, {len(matches)} matches, {attendance_marked} attendance marked",
            faces_detected=faces_detected,
            students_recognized=len([m for m in matches if m["student_id"]]),
            matches=matches,
            processing_time_ms=processing_time_ms
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing detection frame: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing frame: {str(e)}"
        )

@router.post("/stop")
async def stop_detection(
    request: DetectionStopRequest,
    current_admin: str = Depends(get_current_admin)
):
    """Stop detection session"""
    try:
        if request.session_id not in detection_sessions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID"
            )
        
        session = detection_sessions.pop(request.session_id)
        
        logger.info(f"Detection session stopped: {request.session_id} by {current_admin}")
        logger.info(f"Session stats: {session['frames_processed']} frames, {session['students_recognized']} recognized, {session['attendance_marked']} attendance marked")
        
        return {
            "success": True,
            "message": "Detection session stopped successfully",
            "session_stats": session
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping detection session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping detection session: {str(e)}"
        )