from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# Authentication Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class AdminLogin(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


# Student Schemas
class StudentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    roll_no: str = Field(..., min_length=1, max_length=50)
    branch: Optional[str] = None
    year: Optional[int] = None


class StudentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    roll_no: str = Field(..., min_length=1, max_length=50)
    branch: Optional[str] = None
    year: Optional[int] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    roll_no: Optional[str] = Field(None, min_length=1, max_length=50)
    branch: Optional[str] = None
    year: Optional[int] = None


class Student(BaseModel):
    student_id: int
    name: str
    roll_no: str
    branch: Optional[str] = None
    year: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class StudentEmbedding(BaseModel):
    student_id: int
    model_version: str
    quality_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# Attendance Schemas
class AttendanceLogBase(BaseModel):
    student_id: int
    confidence: float
    camera_source: Optional[str] = None


class AttendanceLogCreate(BaseModel):
    student_id: int
    confidence: float
    camera_source: Optional[str] = None


class AttendanceLog(BaseModel):
    log_id: int
    student_id: int
    detected_at: datetime
    confidence: float
    camera_source: Optional[str] = None
    
    class Config:
        from_attributes = True


class AttendanceLogWithStudent(BaseModel):
    student: Student


# Detection Schemas
class DetectionLogBase(BaseModel):
    faces_detected: int = 0
    students_recognized: int = 0
    processing_time: Optional[float] = None
    camera_source: Optional[str] = None
    error_message: Optional[str] = None


class DetectionLogCreate(BaseModel):
    pass


class DetectionLog(BaseModel):
    id: int
    timestamp: datetime
    faces_detected: int
    students_recognized: int
    processing_time: Optional[float] = None
    camera_source: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


# Face Recognition Schemas
class FaceDetectionRequest(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")
    camera_source: Optional[str] = None


class FaceDetectionResponse(BaseModel):
    success: bool
    message: str
    faces_detected: int = 0
    students_recognized: int = 0
    processing_time: Optional[float] = None


class RecognitionResult(BaseModel):
    student_id: int
    student_name: str
    roll_no: str
    branch: Optional[str] = None
    year: Optional[int] = None
    confidence_score: float
    timestamp: datetime


class FaceRecognitionRequest(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image data")
    camera_source: Optional[str] = None


class FaceRecognitionResponse(BaseModel):
    success: bool
    message: str
    matches: List[RecognitionResult] = []
    processing_time: Optional[float] = None


# Liveness Detection Schemas
class LivenessDetectionSessionCreate(BaseModel):
    student_id: Optional[int] = None


class LivenessDetectionSessionUpdate(BaseModel):
    center_frame_data: Optional[str] = None
    left_frame_data: Optional[str] = None
    right_frame_data: Optional[str] = None
    center_embedding: Optional[str] = None
    left_embedding: Optional[str] = None
    right_embedding: Optional[str] = None
    center_verified: Optional[bool] = None
    left_verified: Optional[bool] = None
    right_verified: Optional[bool] = None
    liveness_score: Optional[float] = None
    movement_verified: Optional[bool] = None
    final_embedding: Optional[str] = None
    error_message: Optional[str] = None
    attempts_count: Optional[int] = None


class LivenessDetectionSession(BaseModel):
    id: int
    session_id: str
    student_id: Optional[int] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: datetime
    center_frame_data: Optional[str] = None
    left_frame_data: Optional[str] = None
    right_frame_data: Optional[str] = None
    center_embedding: Optional[str] = None
    left_embedding: Optional[str] = None
    right_embedding: Optional[str] = None
    center_verified: bool = False
    left_verified: bool = False
    right_verified: bool = False
    liveness_score: float = 0.0
    movement_verified: bool = False
    final_embedding: Optional[str] = None
    error_message: Optional[str] = None
    attempts_count: int = 0
    
    class Config:
        from_attributes = True


class LivenessDetectionRequest(BaseModel):
    session_id: str
    position: str = Field(..., pattern="^(center|left|right)$")
    frame_data: str = Field(..., description="Base64 encoded image data")


class LivenessDetectionResponse(BaseModel):
    success: bool
    message: str
    position: Optional[str] = None
    is_live: Optional[bool] = None
    confidence_score: Optional[float] = None
    error: Optional[str] = None
    # New fields for completion status
    session_completed: Optional[bool] = None
    liveness_score: Optional[float] = None
    movement_verified: Optional[bool] = None
    final_embedding_saved: Optional[bool] = None
    student_id: Optional[int] = None


class LivenessVerificationRequest(BaseModel):
    session_id: str


class LivenessVerificationResponse(BaseModel):
    success: bool
    message: str
    liveness_score: Optional[float] = None
    movement_verified: Optional[bool] = None
    final_embedding: Optional[str] = None
    student_id: Optional[int] = None
    error: Optional[str] = None


class StudentRegistrationWithLiveness(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    roll_no: str = Field(..., min_length=1, max_length=50)
    branch: Optional[str] = None
    year: Optional[int] = None
    session_id: str


# API Response Schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
    pages: int


# Export Schemas
class ExportRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    student_id: Optional[int] = None
    format: str = "csv"  # csv or excel
