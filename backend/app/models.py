from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Student(Base):
    __tablename__ = "students"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    roll_number = Column(String(50), unique=True, nullable=False, index=True)
    # New fields per updated schema (kept old for backward-compat)
    roll_no = Column(String(50), unique=False, nullable=True, index=True)
    face_embedding = Column(LargeBinary, nullable=True)
    # Legacy field retained to avoid breaking existing data paths
    embedding_vector = Column(Text, nullable=True)  # JSON string (legacy)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Liveness detection fields
    liveness_verified = Column(Boolean, default=False)
    liveness_verification_date = Column(DateTime(timezone=True), nullable=True)
    liveness_confidence_score = Column(Float, default=0.0)
    
    # Relationship
    attendances = relationship("Attendance", back_populates="student")


class LivenessDetectionSession(Base):
    __tablename__ = "liveness_detection_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    status = Column(String(20), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, FAILED, EXPIRED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Liveness detection data
    center_frame_data = Column(Text, nullable=True)  # Base64 encoded center frame
    left_frame_data = Column(Text, nullable=True)    # Base64 encoded left frame
    right_frame_data = Column(Text, nullable=True)   # Base64 encoded right frame
    
    # Face embeddings from each position
    center_embedding = Column(Text, nullable=True)  # JSON string
    left_embedding = Column(Text, nullable=True)    # JSON string
    right_embedding = Column(Text, nullable=True)   # JSON string
    
    # Verification results
    center_verified = Column(Boolean, default=False)
    left_verified = Column(Boolean, default=False)
    right_verified = Column(Boolean, default=False)
    
    # Overall results
    liveness_score = Column(Float, default=0.0)
    movement_verified = Column(Boolean, default=False)
    final_embedding = Column(Text, nullable=True)  # JSON string
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    attempts_count = Column(Integer, default=0)
    
    # Relationship
    student = relationship("Student", back_populates="liveness_sessions")


# Update Student model to include the relationship
Student.liveness_sessions = relationship("LivenessDetectionSession", back_populates="student")


class Attendance(Base):
    __tablename__ = "attendance_log"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String(20), default="Present", nullable=False)
    confidence_score = Column(Float, nullable=True)
    camera_location = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    student = relationship("Student", back_populates="attendances")


class DetectionLog(Base):
    __tablename__ = "detection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    faces_detected = Column(Integer, default=0)
    students_recognized = Column(Integer, default=0)
    processing_time = Column(Float, nullable=True)
    camera_location = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
