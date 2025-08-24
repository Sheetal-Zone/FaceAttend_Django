from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Optional
from datetime import datetime, date
import pandas as pd
import io
from app.auth import get_current_admin
from app.database import get_db
from app.models import Attendance, Student
from app.schemas import AttendanceWithStudent, APIResponse, PaginatedResponse, ExportRequest
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
        query = db.query(Attendance).join(Student)
        
        # Apply filters
        if start_date:
            query = query.filter(Attendance.timestamp >= start_date)
        if end_date:
            query = query.filter(Attendance.timestamp <= end_date)
        if student_id:
            query = query.filter(Attendance.student_id == student_id)
        if status_filter:
            query = query.filter(Attendance.status == status_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        attendance_records = query.order_by(Attendance.timestamp.desc()).offset(skip).limit(limit).all()
        
        # Convert to response format
        attendance_list = []
        for record in attendance_records:
            attendance_dict = {
                "id": record.id,
                "student_id": record.student_id,
                "student_name": record.student.name,
                "student_roll_number": record.student.roll_number,
                "timestamp": record.timestamp,
                "status": record.status,
                "confidence_score": record.confidence_score,
                "camera_location": record.camera_location,
                "created_at": record.created_at
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


@router.get("/{attendance_id}", response_model=AttendanceWithStudent)
async def get_attendance_record(
    attendance_id: int,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get a specific attendance record"""
    try:
        attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
        if not attendance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendance record not found"
            )
        
        return attendance
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting attendance record {attendance_id}: {e}")
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
        query = db.query(Attendance)
        
        # Apply date filters
        if start_date:
            query = query.filter(Attendance.timestamp >= start_date)
        if end_date:
            query = query.filter(Attendance.timestamp <= end_date)
        
        # Calculate statistics
        total_attendance = query.count()
        present_count = query.filter(Attendance.status == "Present").count()
        absent_count = query.filter(Attendance.status == "Absent").count()
        late_count = query.filter(Attendance.status == "Late").count()
        
        # Calculate attendance rate
        attendance_rate = (present_count / total_attendance * 100) if total_attendance > 0 else 0
        
        # Get unique students
        unique_students = db.query(Attendance.student_id).distinct().count()
        
        return {
            "success": True,
            "message": "Attendance summary retrieved successfully",
            "data": {
                "total_attendance": total_attendance,
                "present_count": present_count,
                "absent_count": absent_count,
                "late_count": late_count,
                "attendance_rate": round(attendance_rate, 2),
                "unique_students": unique_students,
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
        query = db.query(Attendance).join(Student)
        
        # Apply filters
        if export_request.start_date:
            query = query.filter(Attendance.timestamp >= export_request.start_date)
        if export_request.end_date:
            query = query.filter(Attendance.timestamp <= export_request.end_date)
        if export_request.student_id:
            query = query.filter(Attendance.student_id == export_request.student_id)
        
        # Get all records
        attendance_records = query.order_by(Attendance.timestamp.desc()).all()
        
        # Prepare data for export
        export_data = []
        for record in attendance_records:
            export_data.append({
                "Student Name": record.student.name,
                "Roll Number": record.student.roll_number,
                "Date": record.timestamp.date(),
                "Time": record.timestamp.time(),
                "Status": record.status,
                "Confidence Score": record.confidence_score or "",
                "Camera Location": record.camera_location or "",
                "Created At": record.created_at
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


@router.delete("/{attendance_id}", response_model=APIResponse)
async def delete_attendance_record(
    attendance_id: int,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete an attendance record"""
    try:
        attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
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
        logger.error(f"Error deleting attendance record {attendance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting attendance record: {str(e)}"
        )
