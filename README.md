# Face Attendance System with Liveness Detection

A comprehensive face recognition and liveness detection system for student attendance tracking, built with Django, FastAPI, and advanced AI models.

## 🚀 Features

### Core Features
- **Real-time Face Recognition**: Advanced face detection and recognition using YOLO v11
- **Liveness Detection**: Anti-spoofing protection with movement verification (Center → Left → Right)
- **Student Management**: Complete CRUD operations for student records
- **Attendance Tracking**: Automated attendance marking with confidence scores
- **Multi-Camera Support**: Support for CCTV cameras and webcams
- **Real-time Monitoring**: Live detection logs and statistics

### Liveness Detection System
- **Movement Verification**: Students must perform head movements (center, left, right)
- **Anti-Spoofing**: Prevents photo-based attacks and deepfake attempts
- **Real-time Processing**: Instant verification with live camera feed
- **Secure Storage**: Face embeddings stored instead of static images
- **Session Management**: Secure liveness detection sessions with expiration

## 🏗️ Architecture

### Backend Components
- **Django**: Web interface and admin panel
- **FastAPI**: High-performance API for real-time operations
- **SQLAlchemy**: Database ORM for FastAPI
- **YOLO v11**: Face detection and recognition
- **ArcFace**: Advanced face embedding extraction
- **InsightFace**: Liveness detection and verification

### Database Models
- **Student**: Student information with liveness verification status
- **Attendance**: Attendance records with confidence scores
- **LivenessDetectionSession**: Session tracking for liveness verification
- **CameraStream**: Camera configuration and management
- **DetectionLog**: Real-time detection logs and statistics

## 📋 Requirements

### System Requirements
- Python 3.8+
- Webcam or CCTV camera
- Good lighting conditions
- Modern web browser with camera access

### Python Dependencies
```
Django==5.0.2
fastapi==0.104.1
uvicorn[standard]==0.24.0
opencv-python==4.9.0.80
ultralytics==8.2.0
insightface==0.7.3
torch==2.1.1
numpy==1.26.4
sqlalchemy==2.0.23
```

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd face-attend
```

### 2. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Database Setup

#### For Django (Web Interface)
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

#### For FastAPI (Real-time API)
```bash
python scripts/init_db.py
```

### 4. Start the Servers

#### Start Django Server
```bash
python start_backend.py
# Access at: http://localhost:8000
```

#### Start FastAPI Server
```bash
python start_fastapi.py
# Access at: http://localhost:8000
# API docs at: http://localhost:8000/docs
```

## 🎯 Usage

### Student Registration with Liveness Detection

1. **Access Student Registration**
   - Navigate to the student registration page
   - Fill in student details (name, roll number, etc.)

2. **Start Liveness Detection**
   - Click "Start Liveness Detection" button
   - Grant camera permissions when prompted

3. **Complete Liveness Verification**
   - **Step 1**: Face the camera directly (Center position)
   - **Step 2**: Slowly turn your head to the left
   - **Step 3**: Slowly turn your head to the right
   - Follow the on-screen instructions and progress indicators

4. **Registration Completion**
   - System verifies movement patterns
   - Face embeddings are extracted and stored
   - Student is registered with liveness verification

### Liveness Detection Process

The system uses advanced AI models to verify liveness:

1. **Face Detection**: YOLO v11 detects faces in real-time
2. **Movement Tracking**: Monitors head movements across three positions
3. **Embedding Extraction**: ArcFace extracts face embeddings for each position
4. **Liveness Verification**: Compares embeddings to detect natural movement patterns
5. **Anti-Spoofing**: Prevents static image and video-based attacks

### API Endpoints

#### Liveness Detection API
```bash
# Create liveness session
POST /api/v1/liveness/session

# Process frame for liveness detection
POST /api/v1/liveness/detect

# Verify liveness completion
POST /api/v1/liveness/verify

# Register student with liveness
POST /api/v1/liveness/register-student
```

#### Student Management API
```bash
# Get all students
GET /api/v1/students

# Create student
POST /api/v1/students

# Update student
PUT /api/v1/students/{id}

# Delete student
DELETE /api/v1/students/{id}
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the backend directory:

```env
# Database Configuration
DATABASE_URL=sqlite:///./face_attendance.db

# AI Model Paths
YOLO_MODEL_PATH=models/yolov11n.pt
FACE_RECOGNITION_MODEL=arcface_r100_v1

# Security Settings
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=admin123

# Camera Settings
FACE_DETECTION_CONFIDENCE=0.8
FACE_RECOGNITION_THRESHOLD=0.7
```

### Camera Configuration
- **Webcam**: Automatic detection of built-in cameras
- **CCTV**: Configure RTSP/HTTP URLs for IP cameras
- **Resolution**: Supports up to 1920x1080
- **FPS**: Configurable frame rate (15-30 FPS)

## 📊 Monitoring and Analytics

### Real-time Statistics
- Total faces detected
- Students recognized
- Liveness verification success rate
- Processing time metrics
- Camera status monitoring

### Detection Logs
- Timestamp and location tracking
- Confidence scores
- Error logging and debugging
- Performance analytics

## 🔒 Security Features

### Liveness Detection Security
- **Movement Verification**: Ensures natural head movements
- **Anti-Spoofing**: Detects static images and videos
- **Session Management**: Secure session handling with expiration
- **Embedding Storage**: Secure storage of face embeddings

### API Security
- **Authentication**: JWT-based authentication
- **Authorization**: Role-based access control
- **Rate Limiting**: API rate limiting for abuse prevention
- **Input Validation**: Comprehensive input validation

## 🐛 Troubleshooting

### Common Issues

1. **Camera Not Detected**
   - Check camera permissions in browser
   - Ensure camera is not in use by other applications
   - Try refreshing the page

2. **Liveness Detection Fails**
   - Ensure good lighting conditions
   - Follow movement instructions precisely
   - Check for multiple faces in frame
   - Ensure smooth head movements

3. **AI Models Not Loading**
   - Check model file paths in configuration
   - Ensure sufficient disk space
   - Verify GPU drivers (if using GPU acceleration)

### Debug Mode
Enable debug logging by setting:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **YOLO v11**: For face detection capabilities
- **InsightFace**: For face recognition and liveness detection
- **FastAPI**: For high-performance API framework
- **Django**: For web interface framework

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review troubleshooting section

---

**Note**: This system requires proper lighting conditions and a clear view of the face for optimal performance. The liveness detection system is designed to prevent spoofing attacks while maintaining a smooth user experience.
