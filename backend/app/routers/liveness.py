from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict
import uuid
import base64
import numpy as np
import cv2

router = APIRouter()

# In-memory session store
SESSIONS: Dict[str, Dict] = {}


class SessionResponse(BaseModel):
    success: bool
    message: str
    data: Dict


class FrameRequest(BaseModel):
    session_id: str = Field(...)
    position: str = Field(..., pattern="^(center|left|right)$")
    frame_data: str = Field(..., description="Base64 image data without data URI prefix")


class CompleteRequest(BaseModel):
    session_id: str
    student_id: str | None = None


@router.post("/session", response_model=SessionResponse)
def create_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"steps": [], "completed": False}
    return {
        "success": True,
        "message": "Liveness session created",
        "data": {"session_id": session_id}
    }


@router.post("/frames", response_model=SessionResponse)
def process_frame(req: FrameRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    # Decode base64 image
    try:
        img_bytes = base64.b64decode(req.frame_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Invalid image data")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid frame_data")

    # Dummy logic (replace with real head pose detection)
    SESSIONS[req.session_id]["steps"].append(req.position)

    return {
        "success": True,
        "message": f"Head pose detected for {req.position}",
        "data": {
            "is_live": True,
            "position": req.position
        }
    }


@router.post("/complete", response_model=SessionResponse)
def complete_liveness(req: CompleteRequest):
    if req.session_id not in SESSIONS:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    SESSIONS[req.session_id]["completed"] = True
    return {
        "success": True,
        "message": "Liveness completed",
        "data": {"student_id": req.student_id}
    }
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import List
import uuid
import cv2
import numpy as np
from app.database import SessionLocal
from app import models

router = APIRouter()

SESSIONS = {}

@router.post("/session")
def create_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"poses": set(), "embeddings": [], "liveness_passed": False}
    return {"session_id": session_id, "status": "created"}

@router.post("/frames")
async def process_frames(
    session_id: str = Form(...),
    files: List[UploadFile] = File(...)
):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    poses = SESSIONS[session_id]["poses"]
    embeddings = SESSIONS[session_id]["embeddings"]

    for file in files:
        img_bytes = await file.read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Dummy pose check (replace with actual pose estimation)
        poses.add("straight")

        # Dummy embedding (replace with InsightFace later)
        dummy_embedding = np.random.rand(512).tolist()
        embeddings.append(dummy_embedding)

    passed = len(poses) >= 1
    SESSIONS[session_id]["liveness_passed"] = passed

    return {
        "success": True,
        "liveness_passed": passed,
        "poses": list(poses)
    }

@router.post("/complete")
def complete_session(session_id: str = Form(...)):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Invalid session_id")

    data = SESSIONS[session_id]
    if not data["liveness_passed"]:
        return {"success": False, "reason": "Liveness not passed"}

    db = SessionLocal()
    student = db.query(models.Student).first()
    if student:
        emb = models.Embedding(vector=str(data["embeddings"][0]), student_id=student.id)
        db.add(emb)
        db.commit()

        att = models.Attendance(student_id=student.id)
        db.add(att)
        db.commit()

    return {"success": True, "liveness_passed": True}
from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends
from typing import List
import uuid, io, json, logging
import cv2, numpy as np
from app.database import get_db, SessionLocal
from sqlalchemy.orm import Session

# InsightFace import (prepare for CPU fallback)
try:
    from insightface.app import FaceAnalysis
    face_app = FaceAnalysis(allowed_modules=['detection','recognition'])
    # If GPU not available, ctx_id = -1; try auto-prep with cpu first
    try:
        face_app.prepare(ctx_id=0)
    except Exception:
        face_app.prepare(ctx_id=-1)
except Exception:
    face_app = None

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session store (replace with Redis for production)
SESSIONS = {}
EMBEDDING_SIZE = 512  # depending on model

def estimate_head_pose_from_kps(kps):
    """
    kps: 5 or 68 landmarks from InsightFace (x,y)
    returns: yaw, pitch, roll (in degrees) approximate
    """
    try:
        # Use 6 points (nose tip, chin, left eye corner, right eye corner, left mouth corner, right mouth corner)
        # If only 5 kps are available (InsightFace often gives 5), map them appropriately.
        if len(kps) >= 5:
            # define 3D model points of a generic face
            model_points = np.array([
                (0.0, 0.0, 0.0),        # nose tip
                (0.0, -330.0, -65.0),   # chin
                (-225.0, 170.0, -135.0),# left eye left corner
                (225.0, 170.0, -135.0), # right eye right corner
                (-150.0, -150.0, -125.0),# left mouth corner
                (150.0, -150.0, -125.0) # right mouth corner
            ], dtype=np.float64)

            # choose image points from kps (if 5 points, expand roughly)
            # InsightFace 5 kps order: left eye, right eye, nose, left mouth, right mouth
            if len(kps) == 5:
                left_eye = kps[0]; right_eye = kps[1]; nose = kps[2]; left_mouth = kps[3]; right_mouth = kps[4]
                # approximate chin as nose + vector
                chin = (nose[0], nose[1] + 100)
                image_points = np.array([
                    (nose[0], nose[1]),
                    (chin[0], chin[1]),
                    (left_eye[0], left_eye[1]),
                    (right_eye[0], right_eye[1]),
                    (left_mouth[0], left_mouth[1]),
                    (right_mouth[0], right_mouth[1])
                ], dtype=np.float64)
            else:
                # if more landmarks available, pick similar points
                pts = np.array(kps)
                image_points = np.vstack([pts[30], pts[8], pts[36], pts[45], pts[48], pts[54]]).astype(np.float64)
            size = (480, 640)  # default camera size; not used beyond focal calc
            focal_length = size[1]
            center = (size[1]/2, size[0]/2)
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype="double")
            dist_coeffs = np.zeros((4,1)) # assume no lens distortion
            success, rotation_vector, translation_vector = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE)
            if not success:
                return None
            rmat, _ = cv2.Rodrigues(rotation_vector)
            sy = np.sqrt(rmat[0,0]*rmat[0,0] + rmat[1,0]*rmat[1,0])
            singular = sy < 1e-6
            if not singular:
                x = np.arctan2(rmat[2,1], rmat[2,2])
                y = np.arctan2(-rmat[2,0], sy)
                z = np.arctan2(rmat[1,0], rmat[0,0])
            else:
                x = np.arctan2(-rmat[1,2], rmat[1,1])
                y = np.arctan2(-rmat[2,0], sy)
                z = 0
            # convert to degrees (pitch=x, yaw=y, roll=z)
            return np.degrees([y, x, z]).tolist()
    except Exception as e:
        logger.exception("pose error: %s", e)
    return None

@router.post("/session")
def create_session():
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"poses": [], "embeddings": [], "liveness_passed": False}
    logger.info("Created liveness session %s", session_id)
    return {"session_id": session_id}

@router.post("/frames")
async def process_frame(session_id: str = Form(...), file: UploadFile = File(...)):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Invalid session_id")
    content = await file.read()
    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")
    # run insightface if available
    if face_app:
        faces = face_app.get(img)
    else:
        faces = []
    if not faces:
        logger.info("No face detected in frame for session %s", session_id)
        return {"status": "no_face_detected", "liveness_passed": SESSIONS[session_id]["liveness_passed"]}

    # use first face
    face = faces[0]
    kps = getattr(face, "kps", None)
    pose = estimate_head_pose_from_kps(kps) if kps is not None else None
    if pose:
        yaw = pose[0]  # approximate
        # categorize simple poses
        if abs(yaw) < 15:
            SESSIONS[session_id]["poses"].append("straight")
        elif yaw >= 15:
            SESSIONS[session_id]["poses"].append("right")
        elif yaw <= -15:
            SESSIONS[session_id]["poses"].append("left")

    # extract embedding
    embedding = getattr(face, "embedding", None)
    if embedding is not None:
        vec = np.array(embedding).astype(float).tolist()
        SESSIONS[session_id]["embeddings"].append(vec)

    # decide liveness: require at least straight + (left or right) and >=1 embedding
    poses_seen = set(SESSIONS[session_id]["poses"])
    if ("straight" in poses_seen) and (("left" in poses_seen) or ("right" in poses_seen)) and len(SESSIONS[session_id]["embeddings"])>=1:
        SESSIONS[session_id]["liveness_passed"] = True

    return {
        "status": "frame_processed",
        "poses": list(poses_seen),
        "liveness_passed": SESSIONS[session_id]["liveness_passed"]
    }

@router.post("/complete")
def complete(session_id: str = Form(...), db: Session = Depends(get_db)):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Invalid session_id")
    data = SESSIONS.pop(session_id)
    if not data["liveness_passed"]:
        return {"status": "failed", "reason": "liveness not passed"}

    # Persist the first embedding (or aggregated) to DB for demonstration
    if not data["embeddings"]:
        raise HTTPException(status_code=400, detail="No embeddings to save")
    vec = data["embeddings"][0]  # choose first
    from app import models
    # For demo: either find an existing student or create a "guest" entry
    student = db.query(models.Student).first()
    if student is None:
        student = models.Student(name="Unknown", roll_no="N/A")
        db.add(student)
        db.commit()
        db.refresh(student)
    emb = models.Embedding(vector=json.dumps(vec), student_id=student.id)
    db.add(emb)
    db.commit()
    att = models.Attendance(student_id=student.id)
    db.add(att)
    db.commit()
    logger.info("Saved embedding and attendance for student %s", student.id)
    return {"status": "completed", "student_id": student.id}
from fastapi import APIRouter, UploadFile, File, HTTPException
import cv2
import numpy as np
import base64
import logging
from typing import Optional
from app.liveness_detection import liveness_detection_engine

liveness_router = APIRouter()
logger = logging.getLogger(__name__)

sessions = {}

@liveness_router.post("/session")
def create_session():
    try:
        # Ensure models are initialized once
        if not liveness_detection_engine.initialized:
            liveness_detection_engine.initialize_models()
        session = liveness_detection_engine.create_session()
        session_id = session["session_id"]
        sessions[session_id] = {"frames": [], "status": "active"}
        logger.info(f"Liveness session created: {session_id}")
    return {"session_id": session_id}
    except Exception as e:
        logger.error(f"Failed to create liveness session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@liveness_router.post("/frames")
def process_frame(
    session_id: str,
    position: Optional[str] = None,
    frame_data: Optional[str] = None,
    file: Optional[UploadFile] = File(None)
):
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        # Decode image from either base64 JSON or multipart file
        img = None
        if frame_data:
            try:
                raw = base64.b64decode(frame_data.split(",")[-1])
                nparr = np.frombuffer(raw, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid base64 frame data")
        elif file is not None:
    content = file.file.read()
    nparr = np.frombuffer(content, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            raise HTTPException(status_code=400, detail="No frame provided")

        if img is None:
            raise HTTPException(status_code=400, detail="Failed to decode image")

        # Default position when not provided
        if not position:
            position = "center"

        # Initialize models once
        if not liveness_detection_engine.initialized:
            liveness_detection_engine.initialize_models()

        # Process frame with engine (detect face, verify liveness, get embedding)
        result = liveness_detection_engine.process_frame_for_liveness(img, position)

        sessions[session_id]["frames"].append({
            "position": position,
            "is_live": result.get("is_live", False),
            "confidence": result.get("confidence", 0.0)
        })

        # Update engine session with embedding if available
        if result.get("embedding") is not None:
            try:
                emb_list = result["embedding"]
                liveness_detection_engine.update_session(
                    session_id=session_id,
                    position=position,
                    frame_data="provided",
                    embedding=np.array(emb_list).tolist() if isinstance(emb_list, list) else emb_list
                )
            except Exception as e:
                logger.warning(f"Could not update engine session {session_id}: {e}")

        return {
            "status": "frame received",
            "frame_count": len(sessions[session_id]["frames"]),
            "is_live": result.get("is_live", False),
            "confidence": result.get("confidence", 0.0),
            "position": position
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing liveness frame: {e}")
        raise HTTPException(status_code=500, detail="Failed to process frame")

@liveness_router.post("/complete")
def complete_session(session_id: str):
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
    frame_count = len(sessions[session_id]["frames"])

        # Verify session status in engine
        engine_result = liveness_detection_engine.verify_session(session_id)
        sessions[session_id]["status"] = "completed"
        summary = {
            "status": "session complete",
            "total_frames": frame_count,
            "engine": engine_result
        }
    del sessions[session_id]
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete session")
