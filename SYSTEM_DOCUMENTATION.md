# Face Attendance System - Complete Documentation

## Overview

This is a comprehensive face attendance system with liveness detection, built using Django (frontend) and FastAPI (backend) with AI-powered face recognition and liveness detection capabilities.

## System Architecture

### Frontend (Django)
- **Port**: 8000
- **Purpose**: Web interface for student management and attendance
- **Location**: `frontend/` directory
- **Key Features**:
  - Student registration with face capture
  - Liveness detection interface
  - Attendance tracking
  - Admin interface

### Backend (FastAPI)
- **Port**: 8001 (when using `start_complete_system.py`)
- **Port**: 8000 (when using `backend/start_fastapi.py` directly)
- **Purpose**: API endpoints for AI processing and data management
- **Location**: `backend/` directory
- **Key Features**:
  - Face recognition API
  - Liveness detection API
  - Student management API
  - Authentication with JWT tokens

## AI Models Integration

### Models Used
1. **YOLO (YOLOv8n)**: Face detection
   - Location: `models/yolov8n.pt`
   - Purpose: Detect faces in images/video frames
   - Fallback: OpenCV Haar Cascades

2. **InsightFace (buffalo_l)**: Face recognition and liveness detection
   - Location: `~/.insightface/models/buffalo_l/`
   - Purpose: Extract face embeddings and detect liveness
   - Models included:
     - `det_10g.onnx`: Face detection
     - `w600k_r50.onnx`: Face recognition
     - `1k3d68.onnx`: 3D landmark detection
     - `2d106det.onnx`: 2D landmark detection
     - `genderage.onnx`: Gender and age estimation

### Model Download
Run the following command to download and prepare all AI models:
```bash
python download_models.py
```

This script will:
- Download YOLOv8n weights to `models/yolov8n.pt`
- Download and prepare InsightFace buffalo_l models
- Create marker files to indicate successful preparation

## API Endpoints

### Authentication
- **POST** `/api/v1/auth/login`
  - Body: `{"username": "admin", "password": "admin123"}`
  - Response: `{"access_token": "jwt_token", "token_type": "bearer"}`

### Liveness Detection
- **POST** `/api/v1/liveness/session`
  - Creates a new liveness detection session
  - Requires: Bearer token
  - Response: `{"session_id": "uuid", "expires_at": "timestamp"}`

- **POST** `/api/v1/liveness/detect`
  - Processes a frame for liveness detection
  - Body: `{"session_id": "uuid", "position": "center|left|right", "frame_data": "base64_image"}`
  - Response: `{"is_live": boolean, "confidence": float}`

- **POST** `/api/v1/liveness/verify`
  - Verifies liveness detection completion
  - Body: `{"session_id": "uuid"}`
  - Response: `{"is_completed": boolean, "liveness_score": float}`

### Face Recognition
- **POST** `/api/v1/face/detect`
  - Detects faces in an image
  - Body: `{"image_data": "base64_image"}`
  - Response: `{"faces": [{"bbox": [x1,y1,x2,y2], "confidence": float}]}`

- **POST** `/api/v1/face/recognize`
  - Recognizes faces against known students
  - Body: `{"image_data": "base64_image"}`
  - Response: `{"matches": [{"student_id": int, "confidence": float}]}`

## Student Registration Flow

### 1. Basic Information
- Fill in student details (name, ID, etc.)
- Choose verification method:
  - **Liveness Detection** (recommended): Multi-step verification with head movements
  - **Face Capture**: Simple photo capture

### 2. Liveness Detection Process
1. Click "Start Liveness Detection"
2. System creates a session and opens camera
3. Follow on-screen instructions:
   - Center: Look straight at camera
   - Left: Turn head left
   - Right: Turn head right
4. System processes each frame and determines liveness
5. Upon completion, face embedding is extracted and stored

### 3. Face Capture Process
1. Click "Capture Face Photo"
2. System opens camera interface
3. Position face in center of frame
4. Click "Capture Photo" to take picture
5. Review captured image and confirm
6. Face embedding is extracted and stored

### 4. Storage
- Face embeddings are stored in the database
- Images are stored as base64 in the database
- Student record is linked to face data for future recognition

## Authentication Flow

### 1. Login Process
1. Access Django admin at `http://localhost:8000/admin/`
2. Login with admin credentials (admin/admin123)
3. For API access, obtain JWT token:
   ```bash
   curl -X POST "http://localhost:8001/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"username": "admin", "password": "admin123"}'
   ```

### 2. Using JWT Token
Store the token in localStorage as `fastapi_access_token`:
```javascript
localStorage.setItem('fastapi_access_token', 'your_jwt_token_here');
```

Include in API requests:
```javascript
headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
```

## Starting the System

### Option 1: Complete System (Recommended)
```bash
python start_complete_system.py
```
This starts both Django (8000) and FastAPI (8001) servers.

### Option 2: Individual Servers
```bash
# Terminal 1: Django
cd backend
python manage.py runserver 127.0.0.1:8000

# Terminal 2: FastAPI
cd backend
python start_fastapi.py
```

## Configuration

### Environment Variables
- `FASTAPI_BASE_URL`: Base URL for FastAPI (default: http://localhost:8001)
- `DJANGO_BASE_URL`: Base URL for Django (default: http://localhost:8000)

### AI Model Settings
- `yolo_model_path`: Path to YOLO model (default: models/yolov8n.pt)
- `face_detection_confidence`: Minimum confidence for face detection (default: 0.5)
- `allow_opencv_fallback`: Enable OpenCV fallback (default: True)

## Troubleshooting

### Common Issues

1. **"Unexpected token '<'" Error**
   - Cause: Frontend calling Django instead of FastAPI
   - Solution: Check API_BASE URL configuration
   - Ensure FastAPI is running on correct port

2. **Camera Access Denied**
   - Cause: Browser permissions
   - Solution: Allow camera access in browser settings
   - Use HTTPS for production deployment

3. **AI Models Not Loading**
   - Cause: Missing dependencies or models
   - Solution: Run `python download_models.py`
   - Check internet connection for model downloads

4. **Authentication Errors**
   - Cause: Missing or expired JWT token
   - Solution: Re-login and obtain new token
   - Check token storage in localStorage

### Performance Optimization

1. **Model Loading**
   - Models are loaded once at startup
   - Use GPU if available (automatically detected)
   - CPU fallback is available

2. **Image Processing**
   - Images are resized to 640x640 for processing
   - Base64 encoding/decoding is optimized
   - Face detection uses confidence thresholds

3. **Database**
   - Face embeddings are stored as JSON arrays
   - Indexes on student_id and session_id
   - Automatic cleanup of expired sessions

## Security Considerations

1. **Authentication**
   - JWT tokens with expiration
   - Admin-only access to sensitive endpoints
   - Session-based liveness detection

2. **Data Privacy**
   - Face images stored as base64 in database
   - Embeddings are mathematical representations
   - No raw image data in logs

3. **API Security**
   - CORS configuration for frontend access
   - Rate limiting on authentication endpoints
   - Input validation on all endpoints

## Development

### Adding New Features
1. Backend: Add endpoints in `backend/app/routers/`
2. Frontend: Update templates in `frontend/templates/`
3. Models: Update schemas in `backend/app/schemas.py`
4. Database: Create migrations for model changes

### Testing
```bash
# Test AI models
python -c "from backend.app.ai_models import face_recognition_system, liveness_detection_system; face_recognition_system.initialize_models(); liveness_detection_system.initialize_models(); print('Models loaded successfully')"

# Test API endpoints
curl -X GET "http://localhost:8001/health"
```

## Production Deployment

### Requirements
- Python 3.11+
- PostgreSQL (recommended) or SQLite
- GPU (optional, for better performance)
- HTTPS (required for camera access)

### Deployment Steps
1. Install dependencies: `pip install -r backend/requirements.txt`
2. Download models: `python download_models.py`
3. Configure environment variables
4. Set up reverse proxy (nginx)
5. Enable HTTPS for camera access
6. Configure database
7. Run migrations: `python manage.py migrate`

## Support

For issues or questions:
1. Check logs in `backend/logs/`
2. Verify model availability
3. Test API endpoints individually
4. Check browser console for frontend errors
5. Ensure proper authentication flow
