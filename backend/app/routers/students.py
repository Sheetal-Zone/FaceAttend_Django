from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import numpy as np
import cv2
from app.auth import get_current_admin
from app.database import get_db
from app.models import Student, StudentEmbedding
from app.schemas import StudentCreate, StudentUpdate, Student as StudentSchema, APIResponse, PaginatedResponse
from app.ai_models import face_recognition_system
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/students", tags=["Students"])


@router.post("/", response_model=APIResponse)
async def create_student(
    student_data: StudentCreate,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new student (without photo upload - use liveness detection instead)"""
    try:
        # Check if student with roll number already exists
        existing_student = db.query(Student).filter(Student.roll_no == student_data.roll_no).first()
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student with this roll number already exists"
            )
        
        # Create student object (without photo/embedding - will be added via liveness detection)
        student = Student(
            name=student_data.name,
            roll_no=student_data.roll_no,
            branch=student_data.branch,
            year=student_data.year
        )
        
        # Save to database
        db.add(student)
        db.commit()
        db.refresh(student)
        
        logger.info(f"Student {student.name} created successfully (pending liveness verification)")
        
        return {
            "success": True,
            "message": f"Student {student.name} created successfully. Please complete liveness detection to add face data.",
            "data": {
                "student_id": student.student_id,
                "liveness_required": True
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating student: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating student: {str(e)}"
        )


@router.get("/", response_model=PaginatedResponse)
async def get_students(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get list of students with pagination and search"""
    try:
        query = db.query(Student)
        
        # Apply search filter
        if search:
            query = query.filter(
                Student.name.contains(search) | 
                Student.roll_no.contains(search)
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        students = query.offset(skip).limit(limit).all()
        
        # Convert to schema
        student_list = []
        for student in students:
            # Check if student has embedding
            has_embedding = db.query(StudentEmbedding).filter(StudentEmbedding.student_id == student.student_id).first() is not None
            
            student_dict = {
                "student_id": student.student_id,
                "name": student.name,
                "roll_no": student.roll_no,
                "branch": student.branch,
                "year": student.year,
                "has_embedding": has_embedding,
                "created_at": student.created_at
            }
            student_list.append(student_dict)
        
        return {
            "items": student_list,
            "total": total,
            "page": skip // limit + 1,
            "size": limit,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Error getting students: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving students: {str(e)}"
        )


@router.get("/{student_id}", response_model=StudentSchema)
async def get_student(
    student_id: int,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific student by ID"""
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        return student
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving student: {str(e)}"
        )


@router.put("/{student_id}", response_model=APIResponse)
async def update_student(
    student_id: int,
    student_data: StudentUpdate,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a student (without photo upload)"""
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        # Update fields
        if student_data.name is not None:
            student.name = student_data.name
        if student_data.roll_no is not None:
            # Check if roll number already exists
            existing = db.query(Student).filter(
                Student.roll_no == student_data.roll_no,
                Student.student_id != student_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Student with this roll number already exists"
                )
            student.roll_no = student_data.roll_no
        if student_data.branch is not None:
            student.branch = student_data.branch
        if student_data.year is not None:
            student.year = student_data.year
        
        db.commit()
        db.refresh(student)
        
        return {
            "success": True,
            "message": f"Student {student.name} updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating student: {str(e)}"
        )


@router.delete("/{student_id}", response_model=APIResponse)
async def delete_student(
    student_id: int,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a student"""
    try:
        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )
        
        student_name = student.name
        db.delete(student)
        db.commit()
        
        # Reload known faces in AI system
        _reload_known_faces(db)
        
        return {
            "success": True,
            "message": f"Student {student_name} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting student {student_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting student: {str(e)}"
        )


def _reload_known_faces(db: Session):
    """Reload known faces in the AI system"""
    try:
        embeddings = db.query(StudentEmbedding).all()
        students_data = []
        for embedding in embeddings:
            students_data.append({
                'student_id': embedding.student_id,
                'embedding': embedding.embedding
            })
        face_recognition_system.load_known_faces(students_data)
    except Exception as e:
        logger.error(f"Error reloading known faces: {e}")
