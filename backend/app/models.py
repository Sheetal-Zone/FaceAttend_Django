from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, LargeBinary, UniqueConstraint, Index
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
    
    # Single primary key as required
    student_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    roll_no = Column(String(50), unique=True, nullable=False, index=True)
    branch = Column(String(50), nullable=True)
    year = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    embedding = relationship("StudentEmbedding", back_populates="student", uselist=False)
    attendances = relationship("AttendanceLog", back_populates="student")


class StudentEmbedding(Base):
    __tablename__ = "student_embeddings"
    
    # Single primary key referencing students.student_id
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), primary_key=True)
    embedding = Column(LargeBinary, nullable=False)  # Binary embedding data
    model_version = Column(String(50), default="buffalo_l")
    quality_score = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    student = relationship("Student", back_populates="embedding")


class AttendanceLog(Base):
    __tablename__ = "attendance_log"
    
    log_id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id", ondelete="CASCADE"), nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confidence = Column(Float, nullable=False)
    camera_source = Column(String(100), nullable=True)
    
    # Unique constraint to prevent duplicate attendance in one day
    __table_args__ = (
        UniqueConstraint('student_id', 'detected_at', name='unique_daily_attendance'),
        Index('idx_student_date', 'student_id', 'detected_at'),
    )
    
    # Relationship
    student = relationship("Student", back_populates="attendances")


class LivenessDetectionSession(Base):
    __tablename__ = "liveness_detection_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("students.student_id"), nullable=True)
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
    student = relationship("Student")


class DetectionLog(Base):
    __tablename__ = "detection_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    faces_detected = Column(Integer, default=0)
    students_recognized = Column(Integer, default=0)
    processing_time = Column(Float, nullable=True)
    camera_source = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
