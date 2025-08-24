"""
Celery tasks for the attendance system.
"""

from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

from .models import Student, Attendance, DetectionLog
from .camera_processor import camera_manager

logger = logging.getLogger(__name__)


@shared_task
def start_camera_processing():
    """Start processing all active camera streams."""
    try:
        camera_manager.start_all_cameras()
        logger.info("Started camera processing via Celery task")
        return "Camera processing started successfully"
    except Exception as e:
        logger.error(f"Error starting camera processing: {e}")
        return f"Error: {str(e)}"


@shared_task
def stop_camera_processing():
    """Stop processing all camera streams."""
    try:
        camera_manager.stop_all_cameras()
        logger.info("Stopped camera processing via Celery task")
        return "Camera processing stopped successfully"
    except Exception as e:
        logger.error(f"Error stopping camera processing: {e}")
        return f"Error: {str(e)}"


@shared_task
def reload_camera_streams():
    """Reload camera streams from database."""
    try:
        camera_manager.reload_cameras()
        logger.info("Reloaded camera streams via Celery task")
        return "Camera streams reloaded successfully"
    except Exception as e:
        logger.error(f"Error reloading camera streams: {e}")
        return f"Error: {str(e)}"


@shared_task
def cleanup_old_logs():
    """Clean up old detection logs to prevent database bloat."""
    try:
        # Keep logs for the last 30 days
        cutoff_date = timezone.now().date() - timezone.timedelta(days=30)
        deleted_count, _ = DetectionLog.objects.filter(
            timestamp__date__lt=cutoff_date
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old detection logs")
        return f"Cleaned up {deleted_count} old logs"
        
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {e}")
        return f"Error: {str(e)}"


@shared_task
def generate_attendance_report(start_date=None, end_date=None, email_to=None):
    """Generate and email attendance report."""
    try:
        if not start_date:
            start_date = timezone.now().date() - timezone.timedelta(days=7)
        if not end_date:
            end_date = timezone.now().date()
        
        # Get attendance data
        attendances = Attendance.objects.filter(
            date__range=[start_date, end_date]
        ).select_related('student').order_by('date', 'student__name')
        
        # Generate report content
        report_lines = [
            f"Attendance Report: {start_date} to {end_date}",
            "=" * 50,
            ""
        ]
        
        current_date = None
        for attendance in attendances:
            if attendance.date != current_date:
                current_date = attendance.date
                report_lines.append(f"\nDate: {current_date}")
                report_lines.append("-" * 20)
            
            report_lines.append(
                f"{attendance.student.name} ({attendance.student.roll_number}): {attendance.status}"
            )
        
        # Calculate summary
        total_days = (end_date - start_date).days + 1
        total_students = Student.objects.filter(is_active=True).count()
        total_attendance = attendances.count()
        present_count = attendances.filter(status='Present').count()
        
        report_lines.extend([
            "\n" + "=" * 50,
            "SUMMARY",
            "=" * 50,
            f"Total Days: {total_days}",
            f"Total Students: {total_students}",
            f"Total Attendance Records: {total_attendance}",
            f"Present Count: {present_count}",
            f"Overall Attendance Rate: {(present_count / (total_days * total_students) * 100):.1f}%" if total_days * total_students > 0 else "N/A"
        ])
        
        report_content = "\n".join(report_lines)
        
        # Send email if recipient specified
        if email_to:
            send_mail(
                subject=f"Attendance Report: {start_date} to {end_date}",
                message=report_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_to],
                fail_silently=False,
            )
            logger.info(f"Attendance report sent to {email_to}")
        
        return f"Report generated successfully. {len(attendances)} records processed."
        
    except Exception as e:
        logger.error(f"Error generating attendance report: {e}")
        return f"Error: {str(e)}"


@shared_task
def reload_face_encodings():
    """Reload face encodings for all active students."""
    try:
        students = Student.objects.filter(is_active=True)
        reloaded_count = 0
        
        for student in students:
            try:
                # Force regeneration of face encoding
                if student.reference_image:
                    student.save()  # This will trigger the save method to regenerate encoding
                    reloaded_count += 1
            except Exception as e:
                logger.error(f"Error reloading face encoding for {student.name}: {e}")
        
        logger.info(f"Reloaded face encodings for {reloaded_count} students")
        return f"Reloaded {reloaded_count} face encodings"
        
    except Exception as e:
        logger.error(f"Error reloading face encodings: {e}")
        return f"Error: {str(e)}"


@shared_task
def health_check():
    """Health check task to monitor system status."""
    try:
        # Check camera status
        camera_status = camera_manager.get_camera_status()
        active_cameras = len([c for c in camera_status.values() if c['is_running']])
        
        # Check database connectivity
        student_count = Student.objects.count()
        attendance_count = Attendance.objects.count()
        
        # Check recent activity
        recent_attendance = Attendance.objects.filter(
            date=timezone.now().date()
        ).count()
        
        health_status = {
            'timestamp': timezone.now().isoformat(),
            'cameras_active': active_cameras,
            'total_cameras': len(camera_status),
            'total_students': student_count,
            'total_attendance_records': attendance_count,
            'today_attendance': recent_attendance,
            'status': 'healthy' if active_cameras > 0 else 'warning'
        }
        
        logger.info(f"Health check completed: {health_status}")
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'timestamp': timezone.now().isoformat(),
            'status': 'error',
            'error': str(e)
        }
