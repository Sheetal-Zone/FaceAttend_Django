#!/usr/bin/env python3
"""
Face Attendance System - Production Ready FastAPI Backend
"""

import logging
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime

from app.database import create_tables, get_db
from app.models import Student, StudentEmbedding, AttendanceLog, DetectionLog
from app.ai_models import face_recognition_system, liveness_detection_system
from app.config import settings
from app.routers import auth, students, attendance, detection, liveness, face_detection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
app_state = {
    "models_loaded": False,
    "db_connected": False
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Face Attendance System...")
    
    try:
        # Create database tables
        create_tables()
        app_state["db_connected"] = True
        logger.info("Database tables created/verified")
        
        # Initialize AI models
        logger.info("Initializing AI models...")
        face_recognition_system.initialize_models()
        liveness_detection_system.initialize_models()
        app_state["models_loaded"] = True
        logger.info("AI models initialized successfully")
        
        logger.info("Face Attendance System started successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        app_state["models_loaded"] = False
        app_state["db_connected"] = False
    
    yield
    
    # Shutdown
    logger.info("Shutting down Face Attendance System...")

# Create FastAPI app
app = FastAPI(
    title="Face Attendance System",
    description="Production-ready face recognition and liveness detection system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(students.router, prefix="/api/v1/students", tags=["Students"])
app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
app.include_router(detection.router, prefix="/api/v1/detection", tags=["Detection"])
app.include_router(liveness.router, prefix="/api/v1/liveness", tags=["Liveness"])
app.include_router(face_detection.router, prefix="/api/v1/face", tags=["Face Detection"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Face Attendance System API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint - basic process alive check"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/ready")
async def ready_check():
    """Readiness check - verifies DB connectivity and model loading"""
    try:
        # Check database connectivity
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = True
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        db_status = False
    
    # Check model loading
    models_ready = app_state["models_loaded"]
    
    ready = db_status and models_ready
    
    return {
        "ready": ready,
        "database": "connected" if db_status else "disconnected",
        "models": "loaded" if models_ready else "not_loaded",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/api/v1/models")
async def get_models():
    """Get loaded model information"""
    return {
        "face_detection": {
            "model": "YOLOv8n",
            "status": "loaded" if face_recognition_system.initialized else "not_loaded"
        },
        "face_recognition": {
            "model": "InsightFace Buffalo_L",
            "status": "loaded" if face_recognition_system.initialized else "not_loaded"
        },
        "liveness_detection": {
            "model": "InsightFace + OpenCV",
            "status": "loaded" if liveness_detection_system.initialized else "not_loaded"
        }
    }

@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint for monitoring"""
    try:
        db = next(get_db())
        
        # Get counts
        total_students = db.query(Student).count()
        total_embeddings = db.query(StudentEmbedding).count()
        total_attendance_logs = db.query(AttendanceLog).count()
        
        # Get recent detection stats
        recent_detections = db.query(DetectionLog).order_by(DetectionLog.timestamp.desc()).limit(10).all()
        avg_processing_time = sum(d.processing_time for d in recent_detections if d.processing_time) / len(recent_detections) if recent_detections else 0
        
        return {
            "embeddings_count": total_embeddings,
            "students_count": total_students,
            "attendance_logs_count": total_attendance_logs,
            "recognition_count": sum(d.students_recognized for d in recent_detections),
            "average_processing_time_ms": round(avg_processing_time * 1000, 2) if avg_processing_time else 0,
            "frames_processed": sum(d.faces_detected for d in recent_detections),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

@app.get("/debug/logs")
async def get_debug_logs():
    """Get recent error logs for debugging"""
    # This would typically read from a log file or database
    # For now, return a simple response
    return {
        "message": "Debug logs endpoint - implement log retrieval as needed",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info"
    )