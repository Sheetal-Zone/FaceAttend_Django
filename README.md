# Face Attendance System

A production-ready face recognition and liveness detection system for attendance marking, built with FastAPI (backend) and Django (frontend).

## 🏗️ System Architecture

### Backend (FastAPI - Port 8001)
- **AI/ML Processing**: Face detection (YOLOv8n), recognition (InsightFace ArcFace), and liveness detection
- **Database**: SQLAlchemy with SQLite/PostgreSQL support using strict `student_id` primary key structure
- **Authentication**: JWT-based security with admin tokens
- **API Endpoints**: RESTful APIs for all operations with comprehensive logging

### Frontend (Django - Port 8000)
- **Web Interface**: Student registration and attendance management
- **Admin Panel**: Django admin for system management
- **Templates**: HTML templates with JavaScript for camera integration
- **Static Files**: CSS, JavaScript, and media handling

## 🚀 Tech Stack

### Backend Technologies
- **FastAPI**: Modern Python web framework for APIs
- **SQLAlchemy**: Database ORM with Alembic migrations
- **YOLOv8n**: Face detection in video frames
- **InsightFace Buffalo_L**: Face recognition and embedding extraction
- **OpenCV**: Computer vision and image processing
- **JWT**: Secure authentication tokens

### Frontend Technologies
- **Django**: Web framework for frontend and admin
- **Bootstrap 5**: Responsive UI components
- **JavaScript**: Camera integration and API calls
- **WebRTC**: Real-time camera access

### AI/ML Models
- **YOLOv8n**: Face detection model (`models/yolov8n.pt`)
- **InsightFace Buffalo_L**: Face recognition and embedding extraction (ArcFace)
- **MediaPipe**: Optional head pose estimation for liveness detection

## 📊 Database Schema (Strict Key Structure)

### Core Tables
```sql
-- Students table (student_id as PRIMARY KEY)
students (
    student_id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    roll_no VARCHAR(50) UNIQUE NOT NULL,
    branch VARCHAR(50),
    year INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)

-- Face embeddings (one per student, 512D ArcFace vectors)
student_embeddings (
    student_id INTEGER PRIMARY KEY REFERENCES students(student_id),
    embedding BLOB NOT NULL,  -- 512D float32 array as binary
    model_version VARCHAR(50) DEFAULT 'buffalo_l',
    quality_score FLOAT DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)

-- Attendance logs (prevents duplicate daily attendance)
attendance_log (
    log_id INTEGER PRIMARY KEY,
    student_id INTEGER REFERENCES students(student_id),
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    confidence FLOAT NOT NULL,
    camera_source VARCHAR(100),
    UNIQUE(student_id, DATE(detected_at))
)
```

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.11+ (verified with Python 3.13.6)
- Webcam or camera device
- 4GB+ RAM recommended
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd face-attend
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### 3. Install Backend Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies
```bash
cd ../frontend
pip install -r requirements.txt
```

### 5. Model Requirements
The system requires the following AI models:

#### YOLOv8n (Face Detection)
- **File**: `models/yolov8n.pt`
- **Status**: ✅ Included and verified working
- **Purpose**: Face detection in video frames

#### InsightFace Buffalo_L (Face Recognition)
- **Model**: `buffalo_l` (ArcFace)
- **Status**: ✅ Auto-downloaded on first use
- **Purpose**: Face embedding extraction and recognition
- **Location**: `~/.insightface/models/buffalo_l/`

#### MediaPipe (Optional)
- **Status**: Optional - head pose estimation disabled if not available
- **Purpose**: Enhanced liveness detection

### 6. Database Setup

#### Backend (FastAPI)
```bash
cd backend
python -c "from app.database import create_tables; create_tables()"
```

#### Frontend (Django)
```bash
cd frontend
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

## 🚀 Running the System

### Option 1: Start Both Services (Recommended)
```bash
# Terminal 1: Start FastAPI Backend (Port 8001)
cd backend
python start_fastapi.py

# Terminal 2: Start Django Frontend (Port 8000)
cd frontend
python manage.py runserver 0.0.0.0:8000
```

### Option 2: Individual Services
```bash
# Start FastAPI Backend (Port 8001)
cd backend
python start_fastapi.py

# Start Django Frontend (Port 8000)
cd frontend
python manage.py runserver 0.0.0.0:8000
```

### Access URLs
- **Frontend Dashboard**: http://localhost:8000
- **Student Registration**: http://localhost:8000/registration/
- **Live Detection**: http://localhost:8000/detection/
- **Admin Panel**: http://localhost:8000/admin/
- **FastAPI Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## 🔐 Default Credentials

- Username: `admin`
- Password: `admin123`

On backend startup, a default admin user is auto-created if missing. Passwords are stored hashed (bcrypt). Change credentials via environment variables or update `backend/app/config.py` and restart the backend.

## 📱 Usage Workflow

### 1. Student Registration (Liveness Detection)
1. Navigate to http://localhost:8000/registration/
2. Fill in student details (Name, Roll No, Branch, Year)
3. Click "Start Liveness Detection"
4. Follow prompts: Center → Left → Right head movements
5. System saves face embeddings automatically to `student_embeddings` table
6. Click "Complete Registration"

**Note**: Registration does NOT mark attendance - it only saves embeddings.

### 2. Live Detection (Attendance Marking)
1. Navigate to http://localhost:8000/detection/
2. Click "Start Detection"
3. System recognizes faces and marks attendance
4. **Green boxes** show recognized students with details (Name, Roll No, Branch, Year)
5. **Red boxes** show unknown faces
6. Attendance is logged automatically to `attendance_log` table (once per day per student)

### 3. System Monitoring
- **Health Check**: http://localhost:8001/health
- **Readiness Check**: http://localhost:8001/ready
- **Metrics**: http://localhost:8001/metrics
- **API Docs**: http://localhost:8001/docs

## 🔧 Configuration

### Environment Variables
Create `backend/.env`:
```env
DATABASE_URL=sqlite:///./face_attendance.db
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_ALGORITHM=HS256
API_HOST=0.0.0.0
API_PORT=8001
CORS_ORIGINS=["http://localhost:8000", "http://127.0.0.1:8000"]
RECOGNITION_THRESHOLD=0.7
EMBEDDING_MODEL_VERSION=buffalo_l
```

### Model Configuration
- **Face Detection**: YOLOv8n (`models/yolov8n.pt`)
- **Face Recognition**: InsightFace Buffalo_L (ArcFace)
- **Liveness Detection**: MediaPipe head pose estimation (optional)
- **Recognition Threshold**: 0.7 (configurable)
- **Embedding Dimension**: 512D vectors

## 📋 API Reference

### Authentication
All API endpoints require JWT authentication:
```bash
# Get token (form-encoded)
curl -X POST "http://localhost:8001/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin123"

# Or JSON
curl -X POST "http://localhost:8001/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'

# Use token
curl -H "Authorization: Bearer your_token_here" \
     http://localhost:8001/api/v1/students/
```

### Key Endpoints

#### Health & Monitoring
- `GET /health` - System health check
- `GET /ready` - Database + model readiness
- `GET /metrics` - Performance metrics

#### Liveness Detection (Registration)
- `POST /api/v1/liveness/session` - Start liveness session
- `POST /api/v1/liveness/frames` - Process liveness frames
- `POST /api/v1/liveness/complete` - Complete and save embeddings

#### Live Detection (Attendance)
- `POST /api/v1/detection/start` - Start detection session
- `POST /api/v1/detection/frame` - Process detection frame
- `POST /api/v1/detection/stop` - Stop detection session

#### Student Management
- `GET /api/v1/students/` - List all students
- `POST /api/v1/students/` - Create new student
- `GET /api/v1/students/{id}` - Get student details
- `PUT /api/v1/students/{id}` - Update student
- `DELETE /api/v1/students/{id}` - Delete student

#### Attendance
- `GET /api/v1/attendance/` - List attendance records
- `POST /api/v1/attendance/mark` - Mark attendance manually
- `GET /api/v1/attendance/summary` - Get attendance summary

## 🧪 Testing

### Model Verification
```bash
# Test model loading
cd backend
python -c "from app.services.models import model_service; model_service.initialize_models(); print('✅ All models loaded successfully')"
```

### Backend Startup Test
```bash
cd backend
python -c "from main import app; from app.services.models import model_service; model_service.initialize_models(); print('✅ Backend startup test successful')"
```

### Expected Model Loading Logs
```
✅ YOLO model loaded: v8n from ../models/yolov8n.pt
✅ InsightFace loaded: ArcFace buffalo_l
MediaPipe not available - head pose estimation disabled
All models initialized successfully
```

## 🔒 Security Features

- **JWT Authentication**: All API endpoints require valid tokens
- **CORS Protection**: Restricted to frontend origins
- **Input Validation**: Pydantic schemas for all requests
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Rate Limiting**: Built-in request throttling

## 📊 Monitoring & Observability

### Health Endpoints
- `GET /health` - Basic process health
- `GET /ready` - Database + model readiness
- `GET /metrics` - Performance metrics

### Logging
- Structured JSON logs
- Request/response tracking
- Error monitoring
- Performance metrics

### Metrics Tracked
- Total students registered
- Face embeddings stored
- Attendance records created
- Recognition success rate
- Average processing time
- FPS (frames per second)

## 🚨 Troubleshooting

### Common Issues

1. **"Failed to fetch" errors**
   - Check if FastAPI is running on port 8001
   - Verify CORS configuration
   - Check browser console for detailed errors

2. **Camera not working**
   - Ensure camera permissions are granted
   - Check if camera is being used by another application
   - Try refreshing the page

3. **Models not loading**
   - Check if YOLOv8n model exists at `models/yolov8n.pt`
   - Verify InsightFace models are downloaded (auto-download on first use)
   - Check logs for model loading errors

4. **Database errors**
   - Ensure SQLite database file is writable
   - Check database schema migrations
   - Verify foreign key constraints

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python backend/start_fastapi.py
```

### Reset Database
```bash
cd backend
rm face_attendance.db
python -c "from app.database import create_tables; create_tables()"
```

## 🚀 Production Deployment

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Setup
1. Set production environment variables
2. Use PostgreSQL instead of SQLite
3. Configure proper JWT secrets
4. Set up reverse proxy (Nginx)
5. Enable HTTPS
6. Configure monitoring and alerting

### Performance Optimization
- Use GPU acceleration for AI models
- Implement Redis for session storage
- Add database connection pooling
- Configure CDN for static assets
- Set up horizontal scaling

## 📁 Project Structure

```
face-attend/
├── backend/                 # FastAPI backend
│   ├── app/                # Main application code
│   │   ├── routers/        # API route handlers
│   │   ├── models.py       # Database models (strict student_id PK)
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── ai_models.py    # AI model integration
│   │   ├── services/       # Model and storage services
│   │   └── database.py     # Database configuration
│   ├── alembic/            # Database migrations
│   ├── requirements.txt    # Backend dependencies
│   ├── start_fastapi.py    # FastAPI startup script
│   └── main.py             # FastAPI application
├── frontend/               # Django frontend
│   ├── attendance/         # Django app
│   │   ├── models.py       # Django models
│   │   ├── views.py        # Django views
│   │   ├── urls.py         # URL routing
│   │   └── templates/      # HTML templates
│   ├── face_attendance/    # Django project settings
│   ├── templates/          # Global templates
│   ├── static/             # Static files
│   ├── media/              # Media files
│   ├── requirements.txt    # Frontend dependencies
│   └── manage.py           # Django management script
├── models/                 # AI model files
│   └── yolov8n.pt         # YOLOv8n face detection model
├── venv/                   # Python virtual environment (3.13.6)
├── docker-compose.prod.yml # Production deployment
└── README.md               # This file
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation
3. Check system logs
4. Create an issue with detailed information

---

**System Status**: ✅ Production Ready  
**Last Updated**: December 2024  
**Version**: 1.0.0

## ✅ Verification Checklist

- [x] **Virtual Environment**: Single venv with Python 3.13.6
- [x] **YOLO Model**: YOLOv8n verified working (YOLOv10n removed due to compatibility issues)
- [x] **InsightFace**: Buffalo_L model verified working with clear startup logs
- [x] **Database Schema**: Strict `student_id` primary key structure across all tables
- [x] **Backend Startup**: Models load successfully with clear logging
- [x] **Project Structure**: Clean structure with only necessary files
- [x] **Documentation**: Single comprehensive README.md with all instructions