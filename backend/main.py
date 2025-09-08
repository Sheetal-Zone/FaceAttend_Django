from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, liveness, detection
from app.database import create_tables
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Face Attendance")

# CORS - allow all origins for now (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create tables
create_tables()

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(liveness.router, prefix="/api/v1/liveness", tags=["liveness"])
app.include_router(detection.router, prefix="/api/v1/detection", tags=["detection"])

@app.get("/api/v1/ping")
def ping():
    return {"status": "ok"}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.config import settings
from app.routers.auth import auth_router
from app.routers.liveness import liveness_router
from app.routers.detection import detection_router
import logging

# Create tables (SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Face Attendance System", version="1.0.0")
logger = logging.getLogger(__name__)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS enabled for: * (all origins)")

# Routers
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(liveness_router, prefix="/api/v1/liveness")
app.include_router(detection_router, prefix="/api/v1/detection")

@app.get("/health")
def health():
    return {"status": "ok"}
