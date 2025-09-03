from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main views
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Student management
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:student_id>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:student_id>/delete/', views.student_delete, name='student_delete'),
    
    # Attendance
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/export/', views.export_attendance, name='export_attendance'),
    
    # Camera management
    path('cameras/', views.camera_streams, name='camera_streams'),
    path('cameras/<int:camera_id>/edit/', views.camera_edit, name='camera_edit'),
    path('cameras/<int:camera_id>/delete/', views.camera_delete, name='camera_delete'),
    path('cameras/<int:camera_id>/toggle/', views.camera_toggle, name='camera_toggle'),
    
    # Detection and recognition
    path('live-detection/', views.live_detection, name='live_detection'),
    path('detection-logs/', views.detection_logs, name='detection_logs'),
    
    # Detection control
    path('detection/start/', views.start_detection, name='start_detection'),
    path('detection/stop/', views.stop_detection, name='stop_detection'),
    path('detection/status/', views.detection_status, name='detection_status'),
    
    # API endpoints for enhanced functionality
    path('api/students/', views.api_students, name='api_students'),
    path('api/cameras/', views.api_cameras, name='api_cameras'),
    path('api/unrecognized-faces/', views.api_unrecognized_faces, name='api_unrecognized_faces'),
    path('api/unrecognized-faces/<int:face_id>/', views.api_unrecognized_face_detail, name='api_unrecognized_face_detail'),
    path('api/unrecognized-faces/<int:face_id>/ignore/', views.api_ignore_face, name='api_ignore_face'),
    path('api/not-assessed-students/', views.api_not_assessed_students, name='api_not_assessed_students'),
    path('api/attendance-stats/', views.api_attendance_stats, name='api_attendance_stats'),
    path('api/webcam-status/', views.api_webcam_status, name='api_webcam_status'),
    path('api/webcam/', views.webcam_api, name='webcam_api'),
]
