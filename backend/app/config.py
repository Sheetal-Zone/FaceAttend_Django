from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database Configuration
    database_url: str = "sqlite:///./face_attendance.db"
    
    # JWT Configuration
    secret_key: str = "your-super-secret-key-here-make-it-long-and-random"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Admin Credentials
    admin_username: str = "admin"
    admin_password: str = "admin123"
    
    # AI Model Configuration
    yolo_model_path: str = "yolov11n.pt"
    face_recognition_model: str = "arcface_r100_v1"
    face_recognition_threshold: float = 0.6
    face_detection_confidence: float = 0.5
    
    # Camera Configuration
    default_camera_rtsp_url: str = "rtsp://admin:password@192.168.1.100:554/stream1"
    default_camera_http_url: str = "http://192.168.1.100:8080/video"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create settings instance
settings = Settings()

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)
