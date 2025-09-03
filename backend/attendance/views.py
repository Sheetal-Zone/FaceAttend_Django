from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import date, datetime, timedelta
import csv
import io
from .models import (
    Student, Attendance, CameraStream, DetectionLog, WebcamConfiguration,
    UnrecognizedFace, RecognitionSession, RealTimeStats
)
from .face_recognition_engine import FaceRecognitionEngine
import json
import base64
import cv2
import numpy as np

from .forms import StudentForm, AttendanceFilterForm, CameraStreamForm


def login_view(request):
    if request.user.is_authenticated:
        return redirect('attendance:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'attendance:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'attendance/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('attendance:login')

@login_required
def dashboard(request):
    # Get real-time statistics
    stats, created = RealTimeStats.objects.get_or_create(
        timestamp__date=timezone.now().date(),
        defaults={
            'total_faces_detected': 0,
            'total_faces_recognized': 0,
            'total_unrecognized_faces': 0,
            'total_recognized_not_assessed': 0,
            'active_cameras': CameraStream.objects.filter(is_active=True).count(),
            'active_sessions': RecognitionSession.objects.filter(is_active=True).count(),
            'average_processing_time': 0.0
        }
    )
    
    # Update stats with current data
    stats.total_faces_detected = DetectionLog.objects.filter(
        timestamp__date=timezone.now().date()
    ).aggregate(total=Sum('faces_detected'))['total'] or 0
    
    stats.total_faces_recognized = DetectionLog.objects.filter(
        timestamp__date=timezone.now().date()
    ).aggregate(total=Sum('students_recognized'))['total'] or 0
    
    stats.total_unrecognized_faces = UnrecognizedFace.objects.filter(
        status='PENDING'
    ).count()
    
    stats.total_recognized_not_assessed = Student.objects.filter(
        assessment_status='Not Assessed'
    ).count()
    
    stats.active_cameras = CameraStream.objects.filter(is_active=True).count()
    stats.active_sessions = RecognitionSession.objects.filter(is_active=True).count()
    
    # Calculate average processing time
    avg_time = DetectionLog.objects.filter(
        timestamp__date=timezone.now().date()
    ).aggregate(avg=Avg('processing_time'))['avg'] or 0.0
    stats.average_processing_time = avg_time
    
    stats.save()
    
    # Get recent attendance
    recent_attendance = Attendance.objects.select_related('student').order_by('-created_at')[:5]
    
    context = {
        'total_students': Student.objects.count(),
        'today_attendance': Attendance.objects.filter(date=date.today()).count(),
        'total_cameras': CameraStream.objects.filter(is_active=True).count(),
        'detection_logs_count': DetectionLog.objects.count(),
        'recent_attendance': recent_attendance,
        
        # Real-time stats
        'total_faces_detected': stats.total_faces_detected,
        'total_faces_recognized': stats.total_faces_recognized,
        'total_unrecognized_faces': stats.total_unrecognized_faces,
        'total_recognized_not_assessed': stats.total_recognized_not_assessed,
        'active_cameras': stats.active_cameras,
        'active_sessions': stats.active_sessions,
        'average_processing_time': stats.average_processing_time,
    }
    
    return render(request, 'attendance/dashboard.html', context)

@login_required
def student_list(request):
    # Get all students
    students = Student.objects.all().order_by('name')
    
    # Apply filters
    search_query = request.GET.get('search', '')
    branch_filter = request.GET.get('branch', '')
    year_filter = request.GET.get('year', '')
    section_filter = request.GET.get('section', '')
    placement_filter = request.GET.get('placement_status', '')
    assessment_filter = request.GET.get('assessment_status', '')
    
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(roll_number__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    if branch_filter:
        students = students.filter(branch=branch_filter)
    
    if year_filter:
        students = students.filter(year=year_filter)
    
    if section_filter:
        students = students.filter(section=section_filter)
    
    if placement_filter:
        students = students.filter(placement_status=placement_filter)
    
    if assessment_filter:
        students = students.filter(assessment_status=assessment_filter)
    
    # Calculate statistics
    total_count = students.count()
    active_count = students.filter(is_active=True).count()
    not_assessed_count = students.filter(assessment_status='Not Assessed').count()
    
    context = {
        'students': students,
        'search_query': search_query,
        'total_count': total_count,
        'active_count': active_count,
        'not_assessed_count': not_assessed_count,
    }
    
    return render(request, 'attendance/student_list.html', context)

@login_required
def student_add(request):
    if request.method == 'POST':
        try:
            # Create new student
            student = Student.objects.create(
                name=request.POST.get('name'),
                roll_number=request.POST.get('roll_number'),
                email=request.POST.get('email', ''),
                phone_number=request.POST.get('phone_number', ''),
                branch=request.POST.get('branch', 'CSE'),
                year=request.POST.get('year', '1'),
                section=request.POST.get('section', 'A'),
                placement_status=request.POST.get('placement_status', 'Not Placed'),
                assessment_status=request.POST.get('assessment_status', 'Not Assessed'),
            )
            
            # Handle liveness detection data if provided
            face_embedding = request.POST.get('face_embedding')
            if face_embedding:
                student.face_embedding = face_embedding
                student.liveness_verified = True
                student.liveness_verification_date = timezone.now()
                student.liveness_confidence_score = float(request.POST.get('liveness_score', 0.0))
                student.save()
                
                # Initialize face recognition engine and add face
                engine = FaceRecognitionEngine()
                if 'face_image' in request.POST:
                    face_image_b64 = request.POST.get('face_image')
                    face_image_bytes = base64.b64decode(face_image_b64)
                    face_image_np = np.frombuffer(face_image_bytes, np.uint8)
                    face_image = cv2.imdecode(face_image_np, cv2.IMREAD_COLOR)
                    engine.add_new_student_face(student, face_image)
            
            messages.success(request, f'Student "{student.name}" added successfully.')
            return redirect('attendance:student_list')
            
        except Exception as e:
            messages.error(request, f'Error adding student: {str(e)}')
    
    return render(request, 'attendance/student_form.html', {'student': None})

@login_required
def student_edit(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        try:
            # Update student
            student.name = request.POST.get('name')
            student.roll_number = request.POST.get('roll_number')
            student.email = request.POST.get('email', '')
            student.phone_number = request.POST.get('phone_number', '')
            student.branch = request.POST.get('branch', 'CSE')
            student.year = request.POST.get('year', '1')
            student.section = request.POST.get('section', 'A')
            student.placement_status = request.POST.get('placement_status', 'Not Placed')
            student.assessment_status = request.POST.get('assessment_status', 'Not Assessed')
            
            # Handle liveness detection data if provided for updating face embedding
            face_embedding = request.POST.get('face_embedding')
            if face_embedding:
                student.face_embedding = face_embedding
                student.liveness_verified = True
                student.liveness_verification_date = timezone.now()
                student.liveness_confidence_score = float(request.POST.get('liveness_score', 0.0))
            
            student.save()
            
            messages.success(request, f'Student "{student.name}" updated successfully.')
            return redirect('attendance:student_list')
            
        except Exception as e:
            messages.error(request, f'Error updating student: {str(e)}')
    
    return render(request, 'attendance/student_form.html', {'student': student})

@login_required
def student_delete(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        student_name = student.name
        student.delete()
        messages.success(request, f'Student "{student_name}" deleted successfully.')
        return redirect('attendance:student_list')
    
    return render(request, 'attendance/student_confirm_delete.html', {'student': student})

@login_required
def attendance_list(request):
    attendances = Attendance.objects.select_related('student').order_by('-date', '-time')
    students = Student.objects.filter(is_active=True).order_by('name')
    
    context = {
        'attendances': attendances,
        'students': students,
    }
    
    return render(request, 'attendance/attendance_list.html', context)

@login_required
def camera_streams(request):
    cameras = CameraStream.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        try:
            # Create new camera
            camera = CameraStream.objects.create(
                name=request.POST.get('name'),
                camera_type=request.POST.get('camera_type', 'CCTV'),
                rtsp_url=request.POST.get('rtsp_url', ''),
                http_url=request.POST.get('http_url', ''),
                webcam_device_id=request.POST.get('webcam_device_id', 0),
                location=request.POST.get('location', ''),
                resolution_width=request.POST.get('resolution_width', 1280),
                resolution_height=request.POST.get('resolution_height', 720),
                fps=request.POST.get('fps', 30),
                is_active=request.POST.get('is_active') == 'on',
                is_persistent=request.POST.get('is_persistent') == 'on',
                auto_start=request.POST.get('auto_start') == 'on',
                face_detection_enabled=request.POST.get('face_detection_enabled') == 'on',
                attendance_auto_mark=request.POST.get('attendance_auto_mark') == 'on',
                confidence_threshold=request.POST.get('confidence_threshold', 0.8),
            )
            
            messages.success(request, f'Camera "{camera.name}" added successfully.')
            return redirect('attendance:camera_streams')
            
        except Exception as e:
            messages.error(request, f'Error adding camera: {str(e)}')
    
    context = {
        'cameras': cameras,
    }
    
    return render(request, 'attendance/camera_streams.html', context)

@login_required
def camera_edit(request, camera_id):
    camera = get_object_or_404(CameraStream, id=camera_id)
    
    if request.method == 'POST':
        try:
            # Update camera
            camera.name = request.POST.get('name')
            camera.camera_type = request.POST.get('camera_type', 'CCTV')
            camera.rtsp_url = request.POST.get('rtsp_url', '')
            camera.http_url = request.POST.get('http_url', '')
            camera.webcam_device_id = request.POST.get('webcam_device_id', 0)
            camera.location = request.POST.get('location', '')
            camera.resolution_width = request.POST.get('resolution_width', 1280)
            camera.resolution_height = request.POST.get('resolution_height', 720)
            camera.fps = request.POST.get('fps', 30)
            camera.is_active = request.POST.get('is_active') == 'on'
            camera.is_persistent = request.POST.get('is_persistent') == 'on'
            camera.auto_start = request.POST.get('auto_start') == 'on'
            camera.face_detection_enabled = request.POST.get('face_detection_enabled') == 'on'
            camera.attendance_auto_mark = request.POST.get('attendance_auto_mark') == 'on'
            camera.confidence_threshold = request.POST.get('confidence_threshold', 0.8)
            
            camera.save()
            
            messages.success(request, f'Camera "{camera.name}" updated successfully.')
            return redirect('attendance:camera_streams')
            
        except Exception as e:
            messages.error(request, f'Error updating camera: {str(e)}')
    
    return render(request, 'attendance/camera_form.html', {'camera': camera})

@login_required
def camera_delete(request, camera_id):
    camera = get_object_or_404(CameraStream, id=camera_id)
    
    if request.method == 'POST':
        camera_name = camera.name
        camera.delete()
        return JsonResponse({'success': True, 'message': f'Camera "{camera_name}" deleted successfully.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def camera_toggle(request, camera_id):
    camera = get_object_or_404(CameraStream, id=camera_id)
    
    if request.method == 'POST':
        camera.is_active = not camera.is_active
        camera.save()
        
        status = 'activated' if camera.is_active else 'deactivated'
        return JsonResponse({
            'success': True, 
            'message': f'Camera "{camera.name}" {status} successfully.',
            'is_active': camera.is_active
        })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

@login_required
def laptop_camera_management(request):
    """Manage laptop camera for attendance"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start':
            try:
                # Start laptop camera detection via FastAPI
                import requests
                response = requests.post(
                    'http://localhost:8001/api/v1/detection/laptop-camera/start',
                    json={'camera_index': 0},
                    headers={'Authorization': f'Bearer {request.session.get("access_token", "")}'}
                )
                
                if response.status_code == 200:
                    messages.success(request, 'Laptop camera detection started successfully.')
                else:
                    messages.error(request, f'Failed to start laptop camera: {response.text}')
                    
            except Exception as e:
                messages.error(request, f'Error starting laptop camera: {str(e)}')
                
        elif action == 'stop':
            try:
                # Stop laptop camera detection via FastAPI
                import requests
                response = requests.post(
                    'http://localhost:8001/api/v1/detection/laptop-camera/stop',
                    json={'camera_index': 0},
                    headers={'Authorization': f'Bearer {request.session.get("access_token", "")}'}
                )
                
                if response.status_code == 200:
                    messages.success(request, 'Laptop camera detection stopped successfully.')
                else:
                    messages.error(request, f'Failed to stop laptop camera: {response.text}')
                    
            except Exception as e:
                messages.error(request, f'Error stopping laptop camera: {str(e)}')
    
    # Get laptop camera status
    laptop_camera_status = None
    try:
        import requests
        response = requests.get(
            'http://localhost:8001/api/v1/detection/laptop-camera/status',
            headers={'Authorization': f'Bearer {request.session.get("access_token", "")}'}
        )
        
        if response.status_code == 200:
            laptop_camera_status = response.json().get('data', {})
    except:
        pass
    
    context = {
        'laptop_camera_status': laptop_camera_status,
    }
    
    return render(request, 'attendance/laptop_camera_management.html', context)

@login_required
def live_detection(request):
    cameras = CameraStream.objects.filter(is_active=True)
    webcam_config = WebcamConfiguration.objects.first()
    
    context = {
        'cameras': cameras,
        'webcam_config': webcam_config,
    }
    
    return render(request, 'attendance/live_detection.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def webcam_api(request):
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        confidence_score = data.get('confidence_score', 0.0)
        
        student = get_object_or_404(Student, id=student_id)
        
        # Mark attendance
        attendance = Attendance.mark_attendance(
            student=student,
            status='Present',
            confidence_score=confidence_score,
            camera_location='Webcam',
            camera_type='WEBCAM'
        )
        
        # Create detection log
        DetectionLog.objects.create(
            camera_type='WEBCAM',
            faces_detected=1,
            students_recognized=1,
            confidence_scores=[confidence_score]
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Attendance marked for {student.name}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
def detection_logs(request):
    logs = DetectionLog.objects.select_related('camera').order_by('-timestamp')
    
    context = {
        'logs': logs,
    }
    
    return render(request, 'attendance/detection_logs.html', context)

# API Endpoints for enhanced functionality

@login_required
def api_students(request):
    """API endpoint to get all students"""
    students = Student.objects.filter(is_active=True)
    data = []
    
    for student in students:
        data.append({
            'id': student.id,
            'name': student.name,
            'roll_number': student.roll_number,
            'branch': student.get_branch_display(),
            'year': student.get_year_display(),
            'section': student.get_section_display(),
            'assessment_status': student.assessment_status,
            'has_face_embedding': bool(student.face_embedding)
        })
    
    return JsonResponse({'students': data})

@login_required
def api_cameras(request):
    """API endpoint to get all cameras"""
    cameras = CameraStream.objects.all()
    data = []
    
    for camera in cameras:
        data.append({
            'id': camera.id,
            'name': camera.name,
            'camera_type': camera.camera_type,
            'location': camera.location,
            'is_active': camera.is_active,
            'is_persistent': camera.is_persistent,
            'auto_start': camera.auto_start,
            'face_detection_enabled': camera.face_detection_enabled,
            'attendance_auto_mark': camera.attendance_auto_mark,
            'confidence_threshold': camera.confidence_threshold,
            'resolution': f"{camera.resolution_width}x{camera.resolution_height}",
            'fps': camera.fps,
            'stream_url': camera.get_stream_url()
        })
    
    return JsonResponse({'cameras': data})

@login_required
def api_unrecognized_faces(request):
    """API endpoint to get unrecognized faces"""
    faces = UnrecognizedFace.objects.filter(status='PENDING').select_related('camera_source')
    data = []
    
    for face in faces:
        data.append({
            'id': face.id,
            'face_image': face.face_image,
            'detection_time': face.detection_time.strftime('%Y-%m-%d %H:%M:%S'),
            'camera_source': face.camera_source.name if face.camera_source else 'Unknown',
            'confidence_score': face.confidence_score,
            'status': face.status
        })
    
    return JsonResponse({'faces': data})

@login_required
def api_unrecognized_face_detail(request, face_id):
    """API endpoint to get specific unrecognized face"""
    face = get_object_or_404(UnrecognizedFace, id=face_id)
    
    data = {
        'id': face.id,
        'face_embedding': face.face_embedding,
        'face_image': face.face_image,
        'detection_time': face.detection_time.strftime('%Y-%m-%d %H:%M:%S'),
        'camera_source': face.camera_source.name if face.camera_source else 'Unknown',
        'confidence_score': face.confidence_score,
        'status': face.status
    }
    
    return JsonResponse(data)

@login_required
def api_ignore_face(request, face_id):
    """API endpoint to ignore an unrecognized face"""
    face = get_object_or_404(UnrecognizedFace, id=face_id)
    
    if request.method == 'POST':
        face.status = 'IGNORED'
        face.processed_at = timezone.now()
        face.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Face ignored successfully'
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })

@login_required
def api_not_assessed_students(request):
    """API endpoint to get students not assessed"""
    students = Student.objects.filter(assessment_status='Not Assessed')
    data = []
    
    for student in students:
        # Get last recognition time
        last_attendance = Attendance.objects.filter(student=student).order_by('-created_at').first()
        last_recognition = last_attendance.created_at.strftime('%Y-%m-%d %H:%M:%S') if last_attendance else None
        
        data.append({
            'id': student.id,
            'name': student.name,
            'roll_number': student.roll_number,
            'branch': student.get_branch_display(),
            'year': student.get_year_display(),
            'section': student.get_section_display(),
            'last_recognition': last_recognition
        })
    
    return JsonResponse({'students': data})

@login_required
def api_attendance_stats(request):
    """API endpoint to get attendance statistics"""
    today = date.today()
    
    stats = {
        'total_students': Student.objects.count(),
        'today_attendance': Attendance.objects.filter(date=today).count(),
        'total_cameras': CameraStream.objects.filter(is_active=True).count(),
        'detection_logs_count': DetectionLog.objects.count(),
    }
    
    return JsonResponse(stats)

@login_required
def api_webcam_status(request):
    """API endpoint to get webcam status"""
    webcam_config = WebcamConfiguration.objects.first()
    
    if webcam_config:
        data = {
            'is_enabled': webcam_config.is_enabled,
            'device_id': webcam_config.device_id,
            'resolution': f"{webcam_config.resolution_width}x{webcam_config.resolution_height}",
            'fps': webcam_config.fps,
            'face_detection_enabled': webcam_config.face_detection_enabled,
            'attendance_auto_mark': webcam_config.attendance_auto_mark,
            'confidence_threshold': webcam_config.confidence_threshold
        }
    else:
        data = {
            'is_enabled': False,
            'device_id': 0,
            'resolution': '1280x720',
            'fps': 30,
            'face_detection_enabled': True,
            'attendance_auto_mark': True,
            'confidence_threshold': 0.8
        }
    
    return JsonResponse(data)

@login_required
def export_attendance(request):
    """Export attendance data to CSV"""
    try:
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        student_id = request.GET.get('student_id')
        
        # Build query
        queryset = Attendance.objects.select_related('student').order_by('-date', '-time')
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="attendance_export_{date.today()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Student Name', 'Roll Number', 'Branch', 'Year', 'Section',
            'Date', 'Time', 'Status', 'Camera Location', 'Confidence Score'
        ])
        
        for attendance in queryset:
            writer.writerow([
                attendance.student.name,
                attendance.student.roll_number,
                attendance.student.get_branch_display(),
                attendance.student.get_year_display(),
                attendance.student.get_section_display(),
                attendance.date,
                attendance.time,
                attendance.status,
                attendance.camera_location,
                attendance.confidence_score or 0.0
            ])
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error exporting attendance: {str(e)}')
        return redirect('attendance:attendance_list')

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def start_detection(request):
    """Start face detection on all active cameras"""
    try:
        # Get active cameras
        active_cameras = CameraStream.objects.filter(is_active=True, face_detection_enabled=True)
        
        if not active_cameras.exists():
            return JsonResponse({
                'success': False,
                'message': 'No active cameras with face detection enabled'
            })
        
        # Start detection on each camera
        started_cameras = []
        for camera in active_cameras:
            try:
                # Create or update recognition session
                session, created = RecognitionSession.objects.get_or_create(
                    camera=camera,
                    is_active=True,
                    defaults={
                        'start_time': timezone.now(),
                        'total_faces_detected': 0,
                        'total_students_recognized': 0
                    }
                )
                
                if not created:
                    session.start_time = timezone.now()
                    session.total_faces_detected = 0
                    session.total_students_recognized = 0
                    session.save()
                
                started_cameras.append(camera.name)
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error starting detection on {camera.name}: {str(e)}'
                })
        
        return JsonResponse({
            'success': True,
            'message': f'Detection started on {len(started_cameras)} cameras: {", ".join(started_cameras)}',
            'cameras': started_cameras
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error starting detection: {str(e)}'
        })

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def stop_detection(request):
    """Stop face detection on all cameras"""
    try:
        # Stop all active recognition sessions
        active_sessions = RecognitionSession.objects.filter(is_active=True)
        
        if not active_sessions.exists():
            return JsonResponse({
                'success': False,
                'message': 'No active detection sessions found'
            })
        
        stopped_cameras = []
        for session in active_sessions:
            session.is_active = False
            session.end_time = timezone.now()
            session.save()
            stopped_cameras.append(session.camera.name)
        
        return JsonResponse({
            'success': True,
            'message': f'Detection stopped on {len(stopped_cameras)} cameras: {", ".join(stopped_cameras)}',
            'cameras': stopped_cameras
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error stopping detection: {str(e)}'
        })

@login_required
def detection_status(request):
    """Get current detection status"""
    try:
        active_sessions = RecognitionSession.objects.filter(is_active=True)
        active_cameras = CameraStream.objects.filter(is_active=True, face_detection_enabled=True)
        
        status = {
            'is_detection_active': active_sessions.exists(),
            'active_cameras_count': active_cameras.count(),
            'active_sessions_count': active_sessions.count(),
            'active_cameras': [session.camera.name for session in active_sessions],
            'total_faces_detected_today': DetectionLog.objects.filter(
                timestamp__date=date.today()
            ).aggregate(total=Sum('faces_detected'))['total'] or 0,
            'total_students_recognized_today': DetectionLog.objects.filter(
                timestamp__date=date.today()
            ).aggregate(total=Sum('students_recognized'))['total'] or 0
        }
        
        return JsonResponse(status)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error getting detection status: {str(e)}'
        })
