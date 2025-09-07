"""
URL Configuration for Face Attendance System
"""

from django.urls import path
from . import views

urlpatterns = [
    # Main pages
    path('', views.dashboard_view, name='dashboard'),
    path('registration/', views.registration_view, name='registration'),
    path('detection/', views.detection_view, name='detection'),
    
    # Health check
    path('health/', views.health_check, name='health'),
    
    # API proxy to FastAPI backend
    path('api/<path:path>', views.api_proxy, name='api_proxy'),
]
