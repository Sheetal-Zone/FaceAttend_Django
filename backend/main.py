from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from app.database import create_tables, get_db
from app.auth import get_current_admin
from app.routers import students, attendance, detection, auth, liveness, face_detection
from app.ai_models import face_recognition_system
from app.liveness_detection import liveness_detection_engine
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Face Attendance System API",
    description="Advanced face recognition and liveness detection system for student attendance",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(students.router, prefix="/api/v1")
app.include_router(attendance.router, prefix="/api/v1")
app.include_router(detection.router, prefix="/api/v1")
app.include_router(liveness.router, prefix="/api/v1")
app.include_router(face_detection.router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    try:
        logger.info("Starting Face Attendance System...")
        
        # Create database tables
        create_tables()
        logger.info("Database tables created/verified")
        
        # Initialize AI models
        logger.info("Initializing AI models...")
        face_recognition_system.initialize_models()
        liveness_detection_engine.initialize_models()
        logger.info("AI models initialized successfully")
        
        logger.info("Face Attendance System started successfully!")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down Face Attendance System...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Face Attendance System API",
        "version": "2.0.0",
        "docs": "/docs",
        "features": [
            "Face Recognition",
            "Liveness Detection",
            "Student Management",
            "Attendance Tracking",
            "Real-time Detection"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {
            "database": "connected",
            "ai_models": "initialized",
            "liveness_detection": "ready"
        }
    }


@app.get("/api/v1/status")
async def api_status(current_admin: str = Depends(get_current_admin)):
    """API status endpoint (requires authentication)"""
    return {
        "status": "operational",
        "authenticated_user": current_admin,
        "features": {
            "face_recognition": True,
            "liveness_detection": True,
            "student_management": True,
            "attendance_tracking": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
