# Face Attendance System

## Overview
End-to-end face attendance solution combining Django (frontend/admin) and FastAPI (AI backend). Supports student registration with liveness detection (embeddings only) and live detection for attendance marking from USB/RTSP cameras.

## Tech Stack
- Backend: FastAPI (Python)
- Frontend/Admin: Django
- AI: InsightFace (embeddings), YOLO/OpenCV (detection fallback), NumPy, OpenCV
- Realtime: WebSocket (status/logs)
- DB: SQLAlchemy to SQLite (default) or PostgreSQL

## Features
- Liveness detection with head pose (center/left/right) gating
- Store embeddings in `students.face_embedding` (binary)
- Live camera detection; cosine similarity matching; attendance logging
- Auto-reconnect for cameras; robust error logs

## Database Schema
```
students
  id (int, pk)
  name (str)
  roll_number (str, unique)
  face_embedding (bytes, nullable)
  embedding_vector (json string, legacy)

attendance_log
  id (int, pk)
  student_id (fk -> students.id)
  timestamp (datetime, default now)
  status (str, default "Present")
```

## Running the Project

1) Create/activate a Python 3.11 env (venv311 included)

2) Install requirements (if needed)
```
cd backend
..\venv311\Scripts\python.exe -m pip install -r requirements.txt
```

3) Start FastAPI (port 8001)
```
cd backend
..\venv311\Scripts\python.exe start_fastapi.py
```

4) Start Django (port 8000)
```
cd backend
..\venv311\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

## Workflow

### Registration (Liveness Detection)
1. Get FastAPI token (UI button on student form)
2. Click “Start Liveness Detection”
3. Complete steps: center (±5°), left (< -15°), right (> +15°)
4. Backend extracts embeddings with InsightFace and saves to `students.face_embedding`
5. UI shows: “Student embeddings captured and saved successfully” and stops camera

Note: Attendance is NOT marked during registration.

### Live Detection (Attendance)
1. Start detection from UI (USB/RTSP)
2. Backend extracts embeddings from frames and compares to DB
3. If similarity > 0.7, mark attendance in `attendance_log`
4. UI shows success banner and logs reflect recognition/attendance

## API
- Auth: `POST /api/v1/auth/login`
- Liveness:
  - `POST /api/v1/liveness/session`
  - `POST /api/v1/liveness/detect`
- Detection:
  - `POST /api/v1/detection/start`
  - `POST /api/v1/detection/stop`
  - `POST /api/v1/detection/laptop-camera/start|stop`

FastAPI runs at `http://localhost:8001` with CORS enabled for `*`.

## Logs & Debugging
- Backend logs print: camera start/stop, step detections, embeddings saved, recognition matches, attendance commits, and errors with stack traces.

## Future Enhancements
- Improve multi-face handling and region-of-interest tracking
- Persist tokens and RBAC for multi-user admins
- GPU acceleration when available

## System Overview

A comprehensive face attendance system with liveness detection and real-time face recognition capabilities.

## Data Flow: Liveness Detection → Embedding Storage → Recognition

### 1. Liveness Detection Process

**Frontend Flow:**
1. User clicks "Start Liveness Detection" 
2. Creates liveness session via `POST /api/v1/liveness/session`
3. Camera captures frames for 3 positions: center → left → right
4. Each frame sent to `POST /api/v1/liveness/detect` with position and base64 image data
5. Backend processes each frame and extracts embeddings
6. After all 3 positions completed, backend automatically finalizes session
7. Frontend receives `session_completed=true` response and closes modal

**Backend Processing (per frame):**
1. Decode base64 image data to numpy array
2. Run liveness detection using AI models (InsightFace/OpenCV)
3. Extract face embedding using face recognition system
4. Store frame data and embedding in session table
5. When all 3 positions completed:
   - Verify movement using embedding comparison
   - Mark session as "COMPLETED"
   - Save final embedding to student record
   - Reload known faces in recognition system

### 2. Embedding Storage

**Database Storage:**
- **students.embedding_vector**: Final face embedding as JSON string (primary storage)
- **liveness_detection_sessions**: Temporary storage during liveness process
  - center_embedding, left_embedding, right_embedding: Individual position embeddings
  - final_embedding: Chosen embedding (usually center position)

**Storage Location:**
```
Database: face_attendance.db
Table: students
Column: embedding_vector (TEXT)
Format: JSON array of float values (e.g., "[0.123, -0.456, ...]")
```

**Logging:**
Backend logs confirm storage:
```
INFO: Embeddings saved for Student {id} in database table 'students.embedding_vector'
INFO: Reloaded {count} known faces in recognition system
```

### 3. Model Training/Recognition Pipeline

**No Retraining Required:**
- System uses direct embedding comparison (cosine similarity)
- New students add embeddings to database without model retraining
- Recognition compares live embeddings against stored embeddings

**Recognition Process:**
1. Camera captures frame
2. Detect faces using YOLO/OpenCV
3. Extract embedding from each detected face
4. Compare against all known student embeddings
5. If similarity > 0.7 threshold, mark attendance
6. Attendance logged with confidence score

**Live Recognition Flow:**
```
Camera Frame → Face Detection → Embedding Extraction → 
Compare with Stored Embeddings → Match Found → Mark Attendance
```

**Face Recognition System:**
- **Initialization**: Load all student embeddings from database
- **Recognition**: Compare live embeddings using cosine similarity
- **Threshold**: 0.7 similarity required for positive match
- **Attendance**: Automatic marking when recognized (once per day per student)

### 4. System Architecture

**AI Models:**
- **YOLO**: Face detection in frames
- **InsightFace**: Face embedding extraction and liveness detection
- **OpenCV**: Fallback for face detection when YOLO unavailable

**Data Pipeline:**
```
Registration: Image Capture → Liveness Detection → Embedding Extraction → Database Storage
Recognition: Live Camera → Face Detection → Embedding Extraction → Similarity Comparison → Attendance Marking
```

**Key Components:**
- `app/ai_models.py`: Face recognition and liveness detection systems
- `app/liveness_detection.py`: Liveness detection engine
- `app/camera_processor.py`: Real-time camera processing and attendance marking
- `app/routers/liveness.py`: Liveness detection API endpoints
- `app/models.py`: Database models for students and sessions

### 5. Attendance Recognition

**Automatic Attendance:**
- Camera streams continuously process frames
- Face recognition runs on each frame
- When student recognized with confidence > 0.7:
  - Check if attendance already marked today
  - If not, create new attendance record
  - Log recognition with confidence score and camera location

**Database Tables:**
- **students**: Student info + face embeddings
- **attendance**: Attendance records with timestamps and confidence
- **detection_logs**: Performance logs of face detection

**Recognition Threshold:**
- Similarity > 0.7 required for positive identification
- Prevents false positives while maintaining accuracy

## Installation and Setup

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

#### Start Both (Django + FastAPI) Together
```bash
python start_complete_system.py
# Django at: http://localhost:8000
# FastAPI at: http://localhost:8001 (docs at /docs)
```

## 🎯 Usage

### Student Registration with Liveness Detection

1. **Access Student Registration**
   - Navigate to the student registration page
   - Fill in student details (name, roll number, etc.)

2. **Start Liveness Detection**
   - Click "Start Liveness Detection" button
   - Grant camera permissions when prompted
   - Camera lifecycle: MediaStream remains active until you cancel; auto-reconnect on loss

3. **Complete Liveness Verification**
   - **Step 1**: Face the camera directly (Center position)
   - **Step 2**: Slowly turn your head to the left
   - **Step 3**: Slowly turn your head to the right
   - Follow the on-screen instructions and progress indicators

4. **Registration Completion**
   - System verifies movement patterns
   - Face embeddings are extracted and stored to the Student
   - Student is registered with liveness verification
   - When editing a student, successful liveness automatically marks attendance once per session

### Liveness Detection Process

The system uses advanced AI models to verify liveness:

1. **Face Detection**: YOLO (v8n/v9n/v10n) detects faces in real-time
2. **Movement Tracking**: Monitors head movements across three positions
3. **Embedding Extraction**: ArcFace extracts face embeddings for each position
4. **Liveness Verification**: Compares embeddings to detect natural movement patterns
5. **Anti-Spoofing**: Prevents static image and video-based attacks

### Logs and Observability
- Backend logs:
  - Camera feed started
  - Frames received
  - Embedding generated
  - Match found
  - Attendance logged or deduplicated
- Frontend logs:
  - Camera started/running/stopped
  - Reconnect attempts on track end
  - Liveness step transitions and results

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

### Authentication and Using the Liveness API

Most FastAPI endpoints under `/api/v1` require a JWT Bearer token.

1) Obtain a token (FastAPI)

POST `{FASTAPI_BASE}/api/v1/auth/login`

Body:

```json
{
  "username": "admin",
  "password": "admin123"
}
```

Response:

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer"
}
```

Store the token in `localStorage` as `fastapi_access_token` for the frontend.

2) Call liveness endpoints with headers

- `Content-Type: application/json`
- `Accept: application/json`
- `Authorization: Bearer <JWT>`

3) Base URL selection

- If started via `start_complete_system.py`: `FASTAPI_BASE = http://localhost:8001`