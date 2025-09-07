# Face Attendance System - Production Ready

A complete end-to-end face recognition and liveness detection system for attendance marking.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Webcam or camera device
- 4GB+ RAM recommended

### Installation & Setup

1. **Clone and setup environment:**
```bash
git clone <repository-url>
cd face-attend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

2. **Start the complete system:**
```bash
python start_system.py
```

This will:
- Start FastAPI backend on port 8001
- Start Django frontend on port 8000
- Run end-to-end tests
- Display access URLs

### Manual Setup (Alternative)

If you prefer to start services manually:

1. **Start FastAPI Backend:**
```bash
cd backend
python start_fastapi.py
```

2. **Start Django Frontend (in new terminal):**
```bash
python manage.py runserver 8000
```

## 🏗️ System Architecture

### Backend (FastAPI - Port 8001)
- **Health Endpoints**: `/health`, `/ready`, `/metrics`
- **Authentication**: JWT-based with admin tokens
- **Liveness Detection**: `/api/v1/liveness/*` (registration only)
- **Live Detection**: `/api/v1/detection/*` (attendance marking)
- **Student Management**: `/api/v1/students/*`
- **Attendance Logs**: `/api/v1/attendance/*`

### Frontend (Django - Port 8000)
- **Dashboard**: Main system overview
- **Registration**: Student enrollment with liveness detection
- **Live Detection**: Real-time attendance marking
- **Health Monitoring**: System status checks

### Database Schema (Strict Key Structure)
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
    model_version VARCHAR(50) DEFAULT 'antelopev2',
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

### Storage Structure
```
media/
├── students/
│   └── <student_id>/
│       └── registration.jpg          # Registration photo
└── detections/
    └── <student_id>/
        └── <timestamp>.jpg           # Detection snapshots
```

## 🔧 Configuration

### Environment Variables
Create `backend/env.production`:
```env
DATABASE_URL=sqlite:///./face_attendance.db
JWT_SECRET=your-super-secret-jwt-key-change-in-production
API_HOST=0.0.0.0
API_PORT=8001
CORS_ORIGINS=["http://localhost:8000", "http://127.0.0.1:8000"]
RECOGNITION_THRESHOLD=0.7
```

### Model Configuration
- **Face Detection**: YOLOv8n (`models/yolov8n-face.pt`)
- **Face Recognition**: InsightFace ArcFace (`antelopev2`)
- **Liveness Detection**: MediaPipe head pose estimation
- **Recognition Threshold**: 0.7 (configurable)
- **Embedding Dimension**: 512D vectors

## 📱 Usage

### 1. Student Registration (Liveness Detection)
1. Navigate to http://localhost:8000/registration/
2. Fill in student details (Name, Roll No, Branch, Year)
3. Click "Start Liveness Detection"
4. Follow prompts: Center → Left → Right head movements
5. System saves face embeddings automatically
6. Click "Complete Registration"

### 2. Live Detection (Attendance Marking)
1. Navigate to http://localhost:8000/detection/
2. Click "Start Detection"
3. System recognizes faces and marks attendance
4. Green boxes show recognized students
5. Red boxes show unknown faces
6. Attendance is logged automatically (once per day per student)

### 3. System Monitoring
- **Health Check**: http://localhost:8001/health
- **Readiness Check**: http://localhost:8001/ready
- **Metrics**: http://localhost:8001/metrics
- **API Docs**: http://localhost:8001/docs

## 🧪 Testing

### Run End-to-End Tests
```bash
cd backend
python test_end_to_end.py
```

### Test Individual Components
```bash
# Health check
curl http://localhost:8001/health

# Readiness check
curl http://localhost:8001/ready

# Metrics
curl http://localhost:8001/metrics

# API documentation
open http://localhost:8001/docs
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
   - Check if model files exist in `models/` directory
   - Verify sufficient RAM (4GB+ recommended)
   - Check logs for model loading errors

4. **Database errors**
   - Ensure SQLite database file is writable
   - Check database schema migrations
   - Verify foreign key constraints

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python start_system.py
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

## 📋 API Reference

### Authentication
All API endpoints require JWT authentication:
```bash
curl -H "Authorization: Bearer your_token_here" \
     http://localhost:8001/api/v1/students/
```

### Key Endpoints

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
**Last Updated**: September 2024
**Version**: 1.0.0