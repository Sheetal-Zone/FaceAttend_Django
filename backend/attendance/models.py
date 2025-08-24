from django.db import models
from django.contrib.auth.models import User
# import face_recognition  # Commented out for now
import os
from datetime import date, datetime
from django.utils import timezone
import json

class Student(models.Model):
    BRANCH_CHOICES = [
        ('CSE', 'Computer Science Engineering'),
        ('ECE', 'Electronics & Communication Engineering'),
        ('ME', 'Mechanical Engineering'),
        ('CE', 'Civil Engineering'),
        ('IT', 'Information Technology'),
        ('EEE', 'Electrical & Electronics Engineering'),
        ('AI', 'Artificial Intelligence'),
        ('DS', 'Data Science'),
    ]
    
    YEAR_CHOICES = [
        (1, '1st Year'),
        (2, '2nd Year'),
        (3, '3rd Year'),
        (4, '4th Year'),
    ]
    
    SECTION_CHOICES = [
        ('A', 'Section A'),
        ('B', 'Section B'),
        ('C', 'Section C'),
        ('D', 'Section D'),
    ]
    
    PLACEMENT_STATUS_CHOICES = [
        ('Not Placed', 'Not Placed'),
        ('Placed', 'Placed'),
    ]
    
    ASSESSMENT_STATUS_CHOICES = [
        ('Not Assessed', 'Not Assessed'),
        ('Assessed', 'Assessed'),
        ('Under Review', 'Under Review'),
        ('Completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    branch = models.CharField(max_length=10, choices=BRANCH_CHOICES, default='CSE')
    year = models.IntegerField(choices=YEAR_CHOICES, default=1)
    section = models.CharField(max_length=1, choices=SECTION_CHOICES, default='A')
    # Removed reference_image field
    placement_status = models.CharField(max_length=20, choices=PLACEMENT_STATUS_CHOICES, default='Not Placed')
    assessment_status = models.CharField(max_length=20, choices=ASSESSMENT_STATUS_CHOICES, default='Not Assessed')
    # face_encoding = models.BinaryField(blank=True, null=True)  # Commented out for now
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for face recognition and liveness detection
    face_embedding = models.TextField(blank=True, null=True, help_text="Stored face embedding for recognition")
    face_embedding_updated = models.DateTimeField(auto_now=True)
    recognition_confidence = models.FloatField(default=0.0, help_text="Average recognition confidence")
    
    # Liveness detection fields
    liveness_verified = models.BooleanField(default=False, help_text="Whether liveness detection was completed")
    liveness_verification_date = models.DateTimeField(blank=True, null=True)
    liveness_confidence_score = models.FloatField(default=0.0, help_text="Liveness detection confidence score")
    
    def __str__(self):
        return f"{self.name} ({self.roll_number})"

    def save(self, *args, **kwargs):
        # Comment out face encoding for now
        # if self.reference_image and not self.face_encoding:
        #     try:
        #         image = face_recognition.load_image_file(self.reference_image.path)
        #         face_encodings = face_recognition.face_encodings(image)
        #         if face_encodings:
        #             self.face_encoding = face_encodings[0].tobytes()
        #         else:
        #             raise ValueError("No face detected in the uploaded image")
        #     except Exception as e:
        #         raise ValueError(f"Error processing image: {str(e)}")
        super().save(*args, **kwargs)

    def get_attendance_percentage(self, start_date=None, end_date=None):
        if not start_date:
            start_date = date.today().replace(day=1)  # First day of current month
        if not end_date:
            end_date = date.today()
        
        total_days = (end_date - start_date).days + 1
        present_days = self.attendance_set.filter(
            date__gte=start_date,
            date__lte=end_date,
            status='Present'
        ).count()
        
        return round((present_days / total_days) * 100, 2) if total_days > 0 else 0

    class Meta:
        ordering = ['name']

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
    ]
    
    CAMERA_TYPE_CHOICES = [
        ('CCTV', 'CCTV Camera'),
        ('WEBCAM', 'Laptop Webcam'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(default=date.today)
    time = models.TimeField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    confidence_score = models.FloatField(blank=True, null=True)
    camera_location = models.CharField(max_length=100, blank=True, null=True)
    camera_type = models.CharField(max_length=10, choices=CAMERA_TYPE_CHOICES, default='CCTV')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for enhanced tracking
    detection_frame = models.TextField(blank=True, null=True, help_text="Base64 encoded detection frame")
    face_bbox = models.TextField(blank=True, null=True, help_text="JSON encoded face bounding box")
    processing_time = models.FloatField(default=0.0, help_text="Time taken for face detection and recognition")
    
    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date', '-time']
    
    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"
    
    @classmethod
    def mark_attendance(cls, student, status='Present', confidence_score=None, camera_location=None, camera_type='CCTV', detection_frame=None, face_bbox=None, processing_time=0.0):
        attendance, created = cls.objects.get_or_create(
            student=student,
            date=date.today(),
            defaults={
                'status': status,
                'confidence_score': confidence_score,
                'camera_location': camera_location,
                'camera_type': camera_type,
                'detection_frame': detection_frame,
                'face_bbox': face_bbox,
                'processing_time': processing_time,
            }
        )
        if not created:
            attendance.status = status
            attendance.confidence_score = confidence_score
            attendance.camera_location = camera_location
            attendance.camera_type = camera_type
            attendance.detection_frame = detection_frame
            attendance.face_bbox = face_bbox
            attendance.processing_time = processing_time
            attendance.save()
        return attendance

class CameraStream(models.Model):
    CAMERA_TYPE_CHOICES = [
        ('CCTV', 'CCTV/IP Camera'),
        ('WEBCAM', 'Laptop Webcam'),
    ]
    
    name = models.CharField(max_length=100)
    camera_type = models.CharField(max_length=10, choices=CAMERA_TYPE_CHOICES, default='CCTV')
    rtsp_url = models.URLField(blank=True, null=True)
    http_url = models.URLField(blank=True, null=True)
    webcam_device_id = models.IntegerField(default=0, help_text="Device ID for webcam (usually 0 for built-in camera)")
    is_active = models.BooleanField(default=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    resolution_width = models.IntegerField(default=1280, help_text="Camera resolution width")
    resolution_height = models.IntegerField(default=720, help_text="Camera resolution height")
    fps = models.IntegerField(default=30, help_text="Frames per second")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for persistent storage and enhanced functionality
    is_persistent = models.BooleanField(default=True, help_text="Whether to auto-load this camera on startup")
    auto_start = models.BooleanField(default=False, help_text="Automatically start detection on this camera")
    face_detection_enabled = models.BooleanField(default=True)
    attendance_auto_mark = models.BooleanField(default=True)
    confidence_threshold = models.FloatField(default=0.8, help_text="Minimum confidence for face recognition")
    last_connection_test = models.DateTimeField(blank=True, null=True)
    connection_status = models.CharField(max_length=20, default='Unknown', help_text="Last known connection status")
    
    def __str__(self):
        camera_type_display = self.get_camera_type_display()
        return f"{self.name} ({camera_type_display}) - {self.location}"
    
    def get_stream_url(self):
        """Get the appropriate stream URL based on camera type"""
        if self.camera_type == 'WEBCAM':
            return f"webcam://{self.webcam_device_id}"
        elif self.rtsp_url:
            return self.rtsp_url
        elif self.http_url:
            return self.http_url
        return None
    
    def get_camera_config(self):
        """Get camera configuration for OpenCV"""
        config = {
            'device_id': self.webcam_device_id if self.camera_type == 'WEBCAM' else None,
            'rtsp_url': self.rtsp_url if self.camera_type == 'CCTV' else None,
            'http_url': self.http_url if self.camera_type == 'CCTV' else None,
            'width': self.resolution_width,
            'height': self.resolution_height,
            'fps': self.fps,
        }
        return config

class WebcamConfiguration(models.Model):
    """Model to store webcam-specific configuration"""
    name = models.CharField(max_length=100, default="Default Webcam")
    device_id = models.IntegerField(default=0, help_text="Webcam device ID (0 for built-in camera)")
    is_enabled = models.BooleanField(default=True)
    auto_start = models.BooleanField(default=False, help_text="Automatically start webcam on system startup")
    resolution_width = models.IntegerField(default=1280)
    resolution_height = models.IntegerField(default=720)
    fps = models.IntegerField(default=30)
    face_detection_enabled = models.BooleanField(default=True)
    attendance_auto_mark = models.BooleanField(default=True, help_text="Automatically mark attendance when face is recognized")
    confidence_threshold = models.FloatField(default=0.8, help_text="Minimum confidence score for face recognition")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Webcam Configuration"
        verbose_name_plural = "Webcam Configurations"
    
    def __str__(self):
        return f"{self.name} (Device {self.device_id})"
    
    def get_opencv_config(self):
        """Get configuration for OpenCV webcam capture"""
        return {
            'device_id': self.device_id,
            'width': self.resolution_width,
            'height': self.resolution_height,
            'fps': self.fps,
        }

class DetectionLog(models.Model):
    CAMERA_TYPE_CHOICES = [
        ('CCTV', 'CCTV Camera'),
        ('WEBCAM', 'Laptop Webcam'),
    ]
    
    camera = models.ForeignKey(CameraStream, on_delete=models.CASCADE, null=True, blank=True)
    camera_type = models.CharField(max_length=20, default='CCTV', choices=[
        ('CCTV', 'CCTV Camera'),
        ('WEBCAM', 'Laptop Webcam'),
    ])
    timestamp = models.DateTimeField(auto_now_add=True)
    faces_detected = models.IntegerField(default=0)
    students_recognized = models.IntegerField(default=0)
    processing_time = models.FloatField(blank=True, null=True)  # in seconds
    frame_resolution = models.CharField(max_length=20, blank=True, null=True)  # e.g., "1920x1080"
    error_message = models.TextField(blank=True, null=True)
    confidence_scores = models.JSONField(default=list, blank=True, help_text="List of confidence scores for detected faces")
    
    # New fields for enhanced tracking
    unrecognized_faces = models.IntegerField(default=0)
    recognition_accuracy = models.FloatField(default=0.0)
    frame_data = models.TextField(blank=True, null=True, help_text="Base64 encoded frame data")
    detection_metadata = models.JSONField(default=dict, blank=True, help_text="Additional detection metadata")
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.timestamp} - {self.faces_detected} faces, {self.students_recognized} recognized"

# New models for enhanced functionality

class UnrecognizedFace(models.Model):
    """Model to store unrecognized faces for later processing"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved for Student Creation'),
        ('IGNORED', 'Ignored'),
        ('PROCESSED', 'Processed'),
    ]
    
    face_embedding = models.TextField(help_text="Face embedding data")
    face_image = models.TextField(help_text="Base64 encoded face image")
    detection_time = models.DateTimeField(auto_now_add=True)
    camera_source = models.ForeignKey(CameraStream, on_delete=models.CASCADE)
    confidence_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    suggested_name = models.CharField(max_length=100, blank=True, null=True)
    suggested_roll_number = models.CharField(max_length=20, blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-detection_time']
    
    def __str__(self):
        return f"Unrecognized Face - {self.detection_time} - {self.status}"

class RecognitionSession(models.Model):
    """Model to track active recognition sessions"""
    session_id = models.CharField(max_length=100, unique=True)
    camera = models.ForeignKey(CameraStream, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    total_frames_processed = models.IntegerField(default=0)
    total_faces_detected = models.IntegerField(default=0)
    total_faces_recognized = models.IntegerField(default=0)
    average_processing_time = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Recognition Session - {self.session_id} - {self.camera.name}"

class RealTimeStats(models.Model):
    """Model to store real-time statistics"""
    timestamp = models.DateTimeField(auto_now_add=True)
    total_faces_detected = models.IntegerField(default=0)
    total_faces_recognized = models.IntegerField(default=0)
    total_unrecognized_faces = models.IntegerField(default=0)
    total_recognized_not_assessed = models.IntegerField(default=0)
    active_cameras = models.IntegerField(default=0)
    active_sessions = models.IntegerField(default=0)
    average_processing_time = models.FloatField(default=0.0)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Stats - {self.timestamp} - {self.total_faces_detected} detected"

class LivenessDetectionSession(models.Model):
    """Model to track liveness detection sessions"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('EXPIRED', 'Expired'),
    ]
    
    session_id = models.CharField(max_length=100, unique=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    
    # Liveness detection data
    center_frame_data = models.TextField(blank=True, null=True, help_text="Base64 encoded center frame")
    left_frame_data = models.TextField(blank=True, null=True, help_text="Base64 encoded left frame")
    right_frame_data = models.TextField(blank=True, null=True, help_text="Base64 encoded right frame")
    
    # Face embeddings from each position
    center_embedding = models.TextField(blank=True, null=True, help_text="Face embedding from center position")
    left_embedding = models.TextField(blank=True, null=True, help_text="Face embedding from left position")
    right_embedding = models.TextField(blank=True, null=True, help_text="Face embedding from right position")
    
    # Verification results
    center_verified = models.BooleanField(default=False)
    left_verified = models.BooleanField(default=False)
    right_verified = models.BooleanField(default=False)
    
    # Overall results
    liveness_score = models.FloatField(default=0.0, help_text="Overall liveness detection score")
    movement_verified = models.BooleanField(default=False, help_text="Whether movement was detected and verified")
    final_embedding = models.TextField(blank=True, null=True, help_text="Final face embedding for registration")
    
    # Error tracking
    error_message = models.TextField(blank=True, null=True)
    attempts_count = models.IntegerField(default=0, help_text="Number of liveness detection attempts")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Liveness Session - {self.session_id} - {self.status}"
    
    def is_expired(self):
        """Check if the session has expired"""
        return timezone.now() > self.expires_at
    
    def mark_completed(self, final_embedding=None, liveness_score=0.0):
        """Mark the session as completed"""
        self.status = 'COMPLETED'
        self.completed_at = timezone.now()
        self.liveness_score = liveness_score
        if final_embedding:
            self.final_embedding = final_embedding
        self.save()
    
    def mark_failed(self, error_message=""):
        """Mark the session as failed"""
        self.status = 'FAILED'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save()
