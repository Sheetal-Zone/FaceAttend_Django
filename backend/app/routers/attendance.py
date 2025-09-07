from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime, date
import pandas as pd
import io
from app.auth import get_current_admin
from app.database import get_db
from app.models import AttendanceLog, Student
from app.schemas import AttendanceLogWithStudent, APIResponse, PaginatedResponse, ExportRequest
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/", response_model=PaginatedResponse)
async def get_attendance(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    student_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get attendance records with filtering and pagination"""
    try:
        query = db.query(AttendanceLog).join(Student)
        
        # Apply filters
        if start_date:
            query = query.filter(AttendanceLog.detected_at >= start_date)
        if end_date:
            query = query.filter(AttendanceLog.detected_at <= end_date)
        if student_id:
            query = query.filter(AttendanceLog.student_id == student_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        attendance_records = query.order_by(AttendanceLog.detected_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        attendance_list = []
        for record in attendance_records:
            attendance_dict = {
                "log_id": record.log_id,
                "student_id": record.student_id,
                "student_name": record.student.name,
                "student_roll_no": record.student.roll_no,
                "student_branch": record.student.branch,
                "student_year": record.student.year,
                "detected_at": record.detected_at,
                "confidence": record.confidence,
                "camera_source": record.camera_source
            }
            attendance_list.append(attendance_dict)
        
        return {
            "items": attendance_list,
            "total": total,
            "page": skip // limit + 1,
            "size": limit,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Error getting attendance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving attendance: {str(e)}"
        )


@router.post("/mark", response_model=APIResponse)
async def mark_attendance(
    student_id: int,
    confidence: float,
    camera_source: Optional[str] = None,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Mark attendance for a student. Prevent duplicate entries per day."""
    try:
        logger.info(f"Marking attendance for student_id={student_id} by user '{current_admin}'")

        student = db.query(Student).filter(Student.student_id == student_id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        # Prevent duplicate attendance for the same student on the same day
        today = date.today()
        existing = (
            db.query(AttendanceLog)
            .filter(
                AttendanceLog.student_id == student_id,
                func.date(AttendanceLog.detected_at) == today,
            )
            .first()
        )
        if existing:
            logger.info(f"Attendance already marked today for student_id={student_id}")
            return {
                "success": True,
                "message": "Attendance already marked today",
                "data": {
                    "log_id": existing.log_id,
                    "student_id": existing.student_id,
                    "detected_at": existing.detected_at,
                    "confidence": existing.confidence,
                },
            }

        # Create new attendance record
        record = AttendanceLog(
            student_id=student_id,
            detected_at=datetime.utcnow(),
            confidence=confidence,
            camera_source=camera_source,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(f"Attendance marked: log_id={record.log_id} student={student_id}")

        return {
            "success": True,
            "message": f"Attendance marked for {student.name}",
            "data": {
                "log_id": record.log_id,
                "student_id": record.student_id,
                "detected_at": record.detected_at,
                "confidence": record.confidence,
            },
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking attendance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error marking attendance: {str(e)}",
        )

@router.get("/{log_id}", response_model=AttendanceLogWithStudent)
async def get_attendance_record(
    log_id: int,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific attendance record"""
    try:
        attendance = db.query(AttendanceLog).filter(AttendanceLog.log_id == log_id).first()
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendance record not found"
            )
        
        return attendance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting attendance record {log_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving attendance record: {str(e)}"
        )


@router.get("/stats/summary", response_model=APIResponse)
async def get_attendance_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get attendance summary statistics"""
    try:
        query = db.query(AttendanceLog)
        
        # Apply date filters
        if start_date:
            query = query.filter(AttendanceLog.detected_at >= start_date)
        if end_date:
            query = query.filter(AttendanceLog.detected_at <= end_date)
        
        # Calculate statistics
        total_attendance = query.count()
        
        # Get unique students
        unique_students = db.query(AttendanceLog.student_id).distinct().count()
        
        # Calculate average confidence
        avg_confidence = db.query(func.avg(AttendanceLog.confidence)).scalar() or 0
        
        return {
            "success": True,
            "message": "Attendance summary retrieved successfully",
            "data": {
                "total_attendance": total_attendance,
                "unique_students": unique_students,
                "average_confidence": round(avg_confidence, 3),
                "date_range": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting attendance summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving attendance summary: {str(e)}"
        )


@router.post("/export", response_model=APIResponse)
async def export_attendance(
    export_request: ExportRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Export attendance data as CSV or Excel"""
    try:
        query = db.query(AttendanceLog).join(Student)
        
        # Apply filters
        if export_request.start_date:
            query = query.filter(AttendanceLog.detected_at >= export_request.start_date)
        if export_request.end_date:
            query = query.filter(AttendanceLog.detected_at <= export_request.end_date)
        if export_request.student_id:
            query = query.filter(AttendanceLog.student_id == export_request.student_id)
        
        # Get all records
        attendance_records = query.order_by(AttendanceLog.detected_at.desc()).all()
        
        # Prepare data for export
        export_data = []
        for record in attendance_records:
            export_data.append({
                "Student Name": record.student.name,
                "Roll Number": record.student.roll_no,
                "Branch": record.student.branch or "",
                "Year": record.student.year or "",
                "Date": record.detected_at.date(),
                "Time": record.detected_at.time(),
                "Confidence": record.confidence,
                "Camera Source": record.camera_source or ""
            })
        
        # Create DataFrame
        df = pd.DataFrame(export_data)
        
        # Generate file
        if export_request.format.lower() == "excel":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Attendance', index=False)
            output.seek(0)
            
            filename = f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            
        else:  # CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            filename = f"attendance_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            media_type = "text/csv"
        
        return Response(
            content=output.getvalue(),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting attendance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting attendance: {str(e)}"
        )


@router.delete("/{log_id}", response_model=APIResponse)
async def delete_attendance_record(
    log_id: int,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete an attendance record"""
    try:
        attendance = db.query(AttendanceLog).filter(AttendanceLog.log_id == log_id).first()
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendance record not found"
            )
        
        db.delete(attendance)
        db.commit()
        
        return {
            "success": True,
            "message": "Attendance record deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting attendance record {log_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting attendance record: {str(e)}"
        )
