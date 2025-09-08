from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
import numpy as np, json, logging
import shutil, uuid
from app.database import get_db
from sqlalchemy.orm import Session

try:
    from insightface.app import FaceAnalysis
    face_app = FaceAnalysis(allowed_modules=['detection','recognition'])
    try:
        face_app.prepare(ctx_id=0)
    except Exception:
        face_app.prepare(ctx_id=-1)
except Exception:
    face_app = None

logger = logging.getLogger(__name__)
router = APIRouter()

def cosine(a, b):
    a = np.array(a); b = np.array(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 1.0
    return np.dot(a, b) / denom

MATCH_THRESHOLD = 0.6

@router.post("/live")
async def detect_live(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    nparr = np.frombuffer(content, np.uint8)
    img = None
    import cv2
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    if not face_app:
        raise HTTPException(status_code=500, detail="Face model not available on server")

    faces = face_app.get(img)
    if not faces:
        return {"status": "no_face_detected"}

    face = faces[0]
    embedding = getattr(face, "embedding", None)
    if embedding is None:
        raise HTTPException(status_code=500, detail="No embedding extracted")

    # compare with database embeddings
    from app import models
    candidates = db.query(models.Embedding).all()
    best_score = -1
    best_student = None
    for c in candidates:
        try:
            vec_db = json.loads(c.vector)
            score = cosine(embedding, vec_db)
            if score > best_score:
                best_score = score
                best_student = c.student
        except Exception as e:
            logger.exception("compare error: %s", e)

    if best_student and best_score >= MATCH_THRESHOLD:
        # mark attendance
        att = models.Attendance(student_id=best_student.id)
        db.add(att)
        db.commit()
        return {"status": "matched", "student": best_student.name, "score": float(best_score)}
    else:
        return {"status": "no_match", "best_score": float(best_score)}
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import numpy as np
import cv2
import logging
from ..database import get_db
from ..models import Student, Embedding, Attendance
from app.ai_models import face_recognition_system
from app.config import settings
from datetime import datetime, date
from sqlalchemy import func

detection_router = APIRouter()
logger = logging.getLogger(__name__)


@detection_router.post("/live")
def detect_live(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = file.file.read()
        nparr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # Initialize models
        if not face_recognition_system.initialized:
            face_recognition_system.initialize_models()

        # Detect faces and extract embeddings
        face_boxes = face_recognition_system.detect_faces(img)
        if not face_boxes:
            return {"status": "no face detected", "results": []}

        # Load embeddings from DB for comparison once
        db_embeddings = db.query(Embedding).all()
        id_to_embedding = {
            e.student_id: np.frombuffer(e.embedding, dtype=np.float32)
            for e in db_embeddings if e.embedding is not None
        }

        results = []
        for (x1, y1, x2, y2) in face_boxes:
            face_img = img[y1:y2, x1:x2]
            embedding = face_recognition_system.extract_face_embedding(face_img)
            if embedding is None:
                results.append({"student": "unknown", "status": "no embedding", "bbox": [x1,y1,x2,y2]})
                continue

            # Compare against DB embeddings using cosine similarity
            best_match_id = None
            best_score = -1.0
            for student_id, known_emb in id_to_embedding.items():
                norm1 = np.linalg.norm(embedding)
                norm2 = np.linalg.norm(known_emb)
                if norm1 == 0 or norm2 == 0:
                    continue
                sim = float(np.dot(embedding, known_emb) / (norm1 * norm2))
                if sim > best_score:
                    best_score = sim
                    best_match_id = student_id

            if best_match_id is not None and best_score >= settings.recognition_threshold:
                student = db.query(Student).filter(Student.id == best_match_id).first()
                if student is None:
                    results.append({"student": "unknown", "status": "not found", "bbox": [x1,y1,x2,y2]})
                    continue

                # Deduplicate per day
                today = date.today()
                existing = (
                    db.query(Attendance)
                    .filter(Attendance.student_id == student.id, func.date(Attendance.timestamp) == today)
                    .first()
                )
                if not existing:
                    db.add(Attendance(student_id=student.id, timestamp=datetime.utcnow()))
                    db.commit()
                results.append({
                    "student": student.name,
                    "student_id": student.id,
                    "similarity": round(best_score, 3),
                    "status": "attendance marked",
                    "bbox": [x1, y1, x2, y2]
                })
            else:
                results.append({"student": "unknown", "status": "no match", "bbox": [x1,y1,x2,y2], "similarity": round(best_score, 3) if best_score>=0 else None})

        return {"results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /detection/live: {e}")
        raise HTTPException(status_code=500, detail="Detection failed")
