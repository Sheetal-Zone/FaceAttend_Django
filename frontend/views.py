"""
Django Views for Face Attendance System
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
import logging

logger = logging.getLogger(__name__)

# FastAPI Backend Configuration
FASTAPI_BASE_URL = 'http://localhost:8001/api/v1'
AUTH_TOKEN = 'admin_token_placeholder'  # In production, get from session

def registration_view(request):
    """Student registration page with liveness detection"""
    return render(request, 'registration.html')

def detection_view(request):
    """Live detection page for attendance marking"""
    return render(request, 'detection.html')

def dashboard_view(request):
    """Main dashboard"""
    return render(request, 'dashboard.html')

@csrf_exempt
def health_check(request):
    """Health check endpoint"""
    try:
        # Check FastAPI backend
        response = requests.get(f'{FASTAPI_BASE_URL.replace("/api/v1", "")}/health', timeout=5)
        if response.status_code == 200:
            return JsonResponse({
                'status': 'healthy',
                'backend': 'connected',
                'message': 'All systems operational'
            })
        else:
            return JsonResponse({
                'status': 'unhealthy',
                'backend': 'disconnected',
                'message': 'Backend not responding'
            }, status=503)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'backend': 'error',
            'message': f'Backend error: {str(e)}'
        }, status=503)

@csrf_exempt
def api_proxy(request, path):
    """Proxy requests to FastAPI backend"""
    try:
        # Get the full path
        full_path = f'{FASTAPI_BASE_URL}/{path}'
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {AUTH_TOKEN}'
        }
        
        # Forward the request
        if request.method == 'GET':
            response = requests.get(full_path, headers=headers, timeout=30)
        elif request.method == 'POST':
            response = requests.post(full_path, headers=headers, json=request.json, timeout=30)
        elif request.method == 'PUT':
            response = requests.put(full_path, headers=headers, json=request.json, timeout=30)
        elif request.method == 'DELETE':
            response = requests.delete(full_path, headers=headers, timeout=30)
        else:
            return JsonResponse({'error': 'Method not allowed'}, status=405)
        
        # Return the response
        return JsonResponse(response.json(), status=response.status_code)
        
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to FastAPI backend")
        return JsonResponse({
            'error': 'Backend service unavailable',
            'message': 'Please check if FastAPI server is running on port 8001'
        }, status=503)
    except Exception as e:
        logger.error(f"API proxy error: {e}")
        return JsonResponse({
            'error': 'Internal server error',
            'message': str(e)
        }, status=500)
