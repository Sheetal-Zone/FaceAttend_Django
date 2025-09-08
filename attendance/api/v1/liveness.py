from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
import uuid

router = APIRouter()

# In-memory store for sessions
sessions: Dict[str, Dict] = {}

# ------------------------------
# Request Models
# ------------------------------
class SessionRequest(BaseModel):
    pass  # no input, just create

class FrameRequest(BaseModel):
    session_id: str
    position: str  # left, right, up, down
    frame_data: str  # base64 string

class CompleteRequest(BaseModel):
    session_id: str
    student_id: str

# ------------------------------
# Routes
# ------------------------------
@router.post("/session")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"frames": [], "completed": False}
    return {
        "success": True,
        "message": "Session created",
        "data": {"session_id": session_id}
    }

@router.post("/frames")
async def process_frame(req: FrameRequest):
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Simulate head pose detection → always pass for demo
    is_live = True

    sessions[req.session_id]["frames"].append({
        "position": req.position,
        "frame": req.frame_data
    })

    return {
        "success": True,
        "message": "Frame processed",
        "data": {
            "is_live": is_live,
            "position": req.position
        }
    }

@router.post("/complete")
async def complete_liveness(req: CompleteRequest):
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    sessions[req.session_id]["completed"] = True
    sessions[req.session_id]["student_id"] = req.student_id

    return {
        "success": True,
        "message": "Liveness completed",
        "data": {"student_id": req.student_id}
    }


