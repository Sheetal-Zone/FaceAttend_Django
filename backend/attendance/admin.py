from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Student, Attendance, CameraStream, DetectionLog, WebcamConfiguration,
    UnrecognizedFace, RecognitionSession, RealTimeStats
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['name', 'roll_number', 'branch', 'year', 'section', 'placement_status', 'assessment_status', 'is_active', 'attendance_percentage_display']
    list_filter = ['branch', 'year', 'section', 'placement_status', 'assessment_status', 'is_active']
    search_fields = ['name', 'roll_number', 'email', 'phone_number']
    readonly_fields = ['attendance_percentage_display', 'face_embedding_updated', 'recognition_confidence']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'roll_number', 'email', 'phone_number')
        }),
        ('Academic Information', {
            'fields': ('branch', 'year', 'section')
        }),
        ('Career Status', {
            'fields': ('placement_status', 'assessment_status')
        }),
        ('Face Recognition', {
            'fields': ('reference_image', 'face_embedding', 'face_embedding_updated', 'recognition_confidence'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Statistics', {
            'fields': ('attendance_percentage_display',),
            'classes': ('collapse',)
        })
    )
    
    def attendance_percentage_display(self, obj):
        return f"{obj.get_attendance_percentage()}%"
    attendance_percentage_display.short_description = 'Attendance %'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'date', 'time', 'status', 'confidence_score', 'camera_type', 'camera_location']
    list_filter = ['date', 'status', 'camera_type', 'camera_location']
    search_fields = ['student__name', 'student__roll_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student', 'date', 'time')
        }),
        ('Attendance Details', {
            'fields': ('status', 'confidence_score')
        }),
        ('Camera Information', {
            'fields': ('camera_type', 'camera_location')
        }),
        ('Detection Data', {
            'fields': ('detection_frame', 'face_bbox', 'processing_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CameraStream)
class CameraStreamAdmin(admin.ModelAdmin):
    list_display = ['name', 'camera_type', 'location', 'is_active', 'resolution_display', 'fps', 'connection_status']
    list_filter = ['camera_type', 'is_active', 'face_detection_enabled', 'attendance_auto_mark']
    search_fields = ['name', 'location']
    readonly_fields = ['created_at', 'updated_at', 'last_connection_test', 'connection_status']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'camera_type', 'location', 'is_active')
        }),
        ('CCTV Settings', {
            'fields': ('rtsp_url', 'http_url'),
            'classes': ('collapse',)
        }),
        ('Webcam Settings', {
            'fields': ('webcam_device_id',),
            'classes': ('collapse',)
        }),
        ('Technical Settings', {
            'fields': ('resolution_width', 'resolution_height', 'fps')
        }),
        ('Face Recognition Settings', {
            'fields': ('face_detection_enabled', 'attendance_auto_mark', 'confidence_threshold')
        }),
        ('Persistent Settings', {
            'fields': ('is_persistent', 'auto_start')
        }),
        ('Connection Status', {
            'fields': ('last_connection_test', 'connection_status'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.camera_type == 'WEBCAM':
            # Show webcam fields, hide CCTV fields
            fieldsets = list(fieldsets)
            for i, (title, options) in enumerate(fieldsets):
                if title == 'CCTV Settings':
                    options['classes'] = ('collapse',)
                elif title == 'Webcam Settings':
                    options['classes'] = ()
        elif obj and obj.camera_type == 'CCTV':
            # Show CCTV fields, hide webcam fields
            fieldsets = list(fieldsets)
            for i, (title, options) in enumerate(fieldsets):
                if title == 'CCTV Settings':
                    options['classes'] = ()
                elif title == 'Webcam Settings':
                    options['classes'] = ('collapse',)
        return fieldsets
    
    def resolution_display(self, obj):
        return f"{obj.resolution_width}x{obj.resolution_height}"
    resolution_display.short_description = 'Resolution'


@admin.register(WebcamConfiguration)
class WebcamConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_id', 'is_enabled', 'auto_start', 'resolution_display', 'fps', 'face_detection_enabled']
    list_filter = ['is_enabled', 'auto_start', 'face_detection_enabled', 'attendance_auto_mark']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('name', 'device_id', 'is_enabled', 'auto_start')
        }),
        ('Video Settings', {
            'fields': ('resolution_width', 'resolution_height', 'fps')
        }),
        ('Face Recognition Settings', {
            'fields': ('face_detection_enabled', 'attendance_auto_mark', 'confidence_threshold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def resolution_display(self, obj):
        return f"{obj.resolution_width}x{obj.resolution_height}"
    resolution_display.short_description = 'Resolution'


@admin.register(DetectionLog)
class DetectionLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'camera', 'camera_type', 'faces_detected', 'students_recognized', 'unrecognized_faces', 'processing_time']
    list_filter = ['timestamp', 'camera_type', 'camera']
    search_fields = ['camera__name']
    readonly_fields = ['timestamp', 'confidence_scores_display', 'recognition_accuracy']
    
    fieldsets = (
        ('Detection Information', {
            'fields': ('camera', 'camera_type', 'timestamp')
        }),
        ('Results', {
            'fields': ('faces_detected', 'students_recognized', 'unrecognized_faces', 'recognition_accuracy')
        }),
        ('Technical Details', {
            'fields': ('processing_time', 'frame_resolution', 'confidence_scores_display'),
            'classes': ('collapse',)
        }),
        ('Additional Data', {
            'fields': ('frame_data', 'detection_metadata'),
            'classes': ('collapse',)
        })
    )
    
    def confidence_scores_display(self, obj):
        if obj.confidence_scores:
            scores = [f"{score:.2f}" for score in obj.confidence_scores]
            return ", ".join(scores)
        return "No scores"
    confidence_scores_display.short_description = 'Confidence Scores'


@admin.register(UnrecognizedFace)
class UnrecognizedFaceAdmin(admin.ModelAdmin):
    list_display = ['detection_time', 'camera_source', 'confidence_score', 'status', 'suggested_name']
    list_filter = ['status', 'detection_time', 'camera_source']
    search_fields = ['suggested_name', 'suggested_roll_number']
    readonly_fields = ['detection_time', 'face_image_display']
    
    fieldsets = (
        ('Detection Information', {
            'fields': ('camera_source', 'detection_time', 'confidence_score')
        }),
        ('Face Data', {
            'fields': ('face_embedding', 'face_image_display')
        }),
        ('Status', {
            'fields': ('status', 'processed_at')
        }),
        ('Suggestions', {
            'fields': ('suggested_name', 'suggested_roll_number')
        })
    )
    
    def face_image_display(self, obj):
        if obj.face_image:
            return f'<img src="data:image/jpeg;base64,{obj.face_image}" width="200" height="200" />'
        return "No image"
    face_image_display.short_description = 'Face Image'
    face_image_display.allow_tags = True


@admin.register(RecognitionSession)
class RecognitionSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'camera', 'started_at', 'ended_at', 'is_active', 'total_frames_processed', 'total_faces_detected', 'total_faces_recognized']
    list_filter = ['is_active', 'started_at', 'camera']
    search_fields = ['session_id', 'camera__name']
    readonly_fields = ['session_id', 'started_at', 'ended_at', 'average_processing_time']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_id', 'camera', 'started_at', 'ended_at', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_frames_processed', 'total_faces_detected', 'total_faces_recognized', 'average_processing_time')
        })
    )


@admin.register(RealTimeStats)
class RealTimeStatsAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'total_faces_detected', 'total_faces_recognized', 'total_unrecognized_faces', 'total_recognized_not_assessed', 'active_cameras', 'active_sessions']
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']
    
    fieldsets = (
        ('Statistics', {
            'fields': ('total_faces_detected', 'total_faces_recognized', 'total_unrecognized_faces', 'total_recognized_not_assessed')
        }),
        ('System Status', {
            'fields': ('active_cameras', 'active_sessions', 'average_processing_time')
        }),
        ('Timestamp', {
            'fields': ('timestamp',)
        })
    )

# Customize admin site
admin.site.site_header = "Face Attendance System Admin"
admin.site.site_title = "Face Attendance Admin"
admin.site.index_title = "Welcome to Face Attendance System Administration"
