from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Dict
import json
import asyncio
from app.auth import get_current_admin
from app.database import get_db
from app.models import Student, DetectionLog
from app.schemas import FaceDetectionRequest, FaceDetectionResponse, APIResponse
from app.camera_processor import camera_manager
from app.ai_models import face_recognition_system
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detection", tags=["Face Detection"])


@router.post("/start", response_model=APIResponse)
async def start_face_detection(
    request: FaceDetectionRequest,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Start real-time face detection from camera stream"""
    try:
        # Initialize AI models if not already done
        if not face_recognition_system.initialized:
            face_recognition_system.initialize_models()
            
            # Load known faces
            students = db.query(Student).all()
            students_data = []
            for student in students:
                if student.embedding_vector:
                    students_data.append({
                        'id': student.id,
                        'embedding_vector': student.embedding_vector
                    })
            face_recognition_system.load_known_faces(students_data)
        
        # Start camera processing
        camera_manager.start_camera(
            camera_url=request.camera_url,
            camera_location=request.camera_location or "Unknown"
        )
        
        return {
            "success": True,
            "message": f"Face detection started for camera: {request.camera_url}",
            "data": {
                "camera_url": request.camera_url,
                "camera_location": request.camera_location
            }
        }
        
    except Exception as e:
        logger.error(f"Error starting face detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting face detection: {str(e)}"
        )


@router.post("/stop", response_model=APIResponse)
async def stop_face_detection(
    payload: Dict,
    current_admin: str = Depends(get_current_admin)
):
    """Stop face detection for a specific camera"""
    try:
        camera_url = payload.get('camera_url', '')
        if not camera_url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="camera_url is required")
        camera_manager.stop_camera(camera_url)
        
        return {
            "success": True,
            "message": f"Face detection stopped for camera: {camera_url}"
        }
        
    except Exception as e:
        logger.error(f"Error stopping face detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping face detection: {str(e)}"
        )


@router.post("/stop-all", response_model=APIResponse)
async def stop_all_face_detection(
    current_admin: str = Depends(get_current_admin)
):
    """Stop all face detection processes"""
    try:
        camera_manager.stop_all_cameras()
        
        return {
            "success": True,
            "message": "All face detection processes stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping all face detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping face detection: {str(e)}"
        )


@router.get("/status", response_model=APIResponse)
async def get_detection_status(
    current_admin: str = Depends(get_current_admin)
):
    """Get status of all camera detection processes"""
    try:
        status = camera_manager.get_camera_status()
        
        return {
            "success": True,
            "message": "Detection status retrieved successfully",
            "data": {
                "cameras": status,
                "total_cameras": len(status),
                "active_cameras": len([c for c in status.values() if c['is_running']])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting detection status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving detection status: {str(e)}"
        )


@router.get("/logs", response_model=APIResponse)
async def get_detection_logs(
    limit: int = 100,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get recent detection logs"""
    try:
        logs = db.query(DetectionLog).order_by(DetectionLog.timestamp.desc()).limit(limit).all()
        
        log_list = []
        for log in logs:
            log_dict = {
                "id": log.id,
                "timestamp": log.timestamp,
                "faces_detected": log.faces_detected,
                "students_recognized": log.students_recognized,
                "processing_time": log.processing_time,
                "camera_location": log.camera_location,
                "error_message": log.error_message
            }
            log_list.append(log_dict)
        
        return {
            "success": True,
            "message": "Detection logs retrieved successfully",
            "data": {
                "logs": log_list,
                "total": len(log_list)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting detection logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving detection logs: {str(e)}"
        )


# WebSocket for real-time detection updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)


manager = ConnectionManager()


# Laptop Camera Endpoints
@router.post("/laptop-camera/start", response_model=APIResponse)
async def start_laptop_camera_detection(
    camera_index: int = 0,
    current_admin: str = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Start real-time face detection from laptop camera"""
    try:
        # Initialize AI models if not already done
        if not face_recognition_system.initialized:
            face_recognition_system.initialize_models()
            
            # Load known faces
            students = db.query(Student).all()
            students_data = []
            for student in students:
                if student.embedding_vector:
                    students_data.append({
                        'id': student.id,
                        'embedding_vector': student.embedding_vector
                    })
            face_recognition_system.load_known_faces(students_data)
        
        # Import here to avoid circular imports
        from app.camera_processor import LaptopCameraProcessor
        
        # Create and start laptop camera processor
        laptop_processor = LaptopCameraProcessor(camera_index=camera_index)
        laptop_processor.start()
        
        # Store processor reference (you might want to add this to camera_manager)
        # For now, we'll store it in a simple way
        if not hasattr(router, 'laptop_processors'):
            router.laptop_processors = {}
        
        router.laptop_processors[camera_index] = laptop_processor
        
        return {
            "success": True,
            "message": f"Laptop camera detection started for camera index: {camera_index}",
            "data": {
                "camera_index": camera_index,
                "camera_location": "Laptop Camera",
                "available_cameras": laptop_processor.available_cameras
            }
        }
        
    except Exception as e:
        logger.error(f"Error starting laptop camera detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting laptop camera detection: {str(e)}"
        )


@router.post("/laptop-camera/stop", response_model=APIResponse)
async def stop_laptop_camera_detection(
    payload: Dict,
    current_admin: str = Depends(get_current_admin)
):
    """Stop laptop camera detection for a specific camera index"""
    try:
        camera_index = int(payload.get('camera_index', 0))
        if hasattr(router, 'laptop_processors') and camera_index in router.laptop_processors:
            processor = router.laptop_processors[camera_index]
            processor.stop()
            del router.laptop_processors[camera_index]
            
            return {
                "success": True,
                "message": f"Laptop camera detection stopped for camera index: {camera_index}"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No laptop camera processor found for index: {camera_index}"
            )
        
    except Exception as e:
        logger.error(f"Error stopping laptop camera detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error stopping laptop camera detection: {str(e)}"
        )


@router.get("/laptop-camera/info", response_model=APIResponse)
async def get_laptop_camera_info(
    current_admin: str = Depends(get_current_admin)
):
    """Get information about available laptop cameras"""
    try:
        from app.camera_processor import LaptopCameraProcessor
        
        # Create a temporary processor to get camera info
        temp_processor = LaptopCameraProcessor()
        camera_info = temp_processor.get_camera_info()
        
        return {
            "success": True,
            "message": "Laptop camera information retrieved",
            "data": camera_info
        }
        
    except Exception as e:
        logger.error(f"Error getting laptop camera info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting laptop camera info: {str(e)}"
        )


@router.post("/laptop-camera/switch", response_model=APIResponse)
async def switch_laptop_camera(
    payload: Dict,
    current_admin: str = Depends(get_current_admin)
):
    """Switch to a different laptop camera index"""
    try:
        if hasattr(router, 'laptop_processors'):
            camera_index = int(payload.get('camera_index'))
            # Find any running processor
            for idx, processor in router.laptop_processors.items():
                if processor.is_running:
                    if processor.switch_camera(camera_index):
                        # Update the stored processor
                        router.laptop_processors[camera_index] = processor
                        if idx != camera_index:
                            del router.laptop_processors[idx]
                        
                        return {
                            "success": True,
                            "message": f"Switched to laptop camera index: {camera_index}",
                            "data": {
                                "camera_index": camera_index,
                                "camera_location": "Laptop Camera"
                            }
                        }
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to switch to camera index: {camera_index}"
                        )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No running laptop camera processor found"
            )
        
    except Exception as e:
        logger.error(f"Error switching laptop camera: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error switching laptop camera: {str(e)}"
        )


@router.get("/laptop-camera/status", response_model=APIResponse)
async def get_laptop_camera_status(
    current_admin: str = Depends(get_current_admin)
):
    """Get status of all laptop camera processors"""
    try:
        status_data = {}
        
        if hasattr(router, 'laptop_processors'):
            for idx, processor in router.laptop_processors.items():
                status_data[idx] = {
                    "running": processor.is_running,
                    "camera_location": processor.camera_location,
                    "frame_count": processor.frame_count
                }
        
        return {
            "success": True,
            "message": "Laptop camera status retrieved",
            "data": status_data
        }
        
    except Exception as e:
        logger.error(f"Error getting laptop camera status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting laptop camera status: {str(e)}"
        )


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    """WebSocket endpoint for real-time detection updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic status updates
            status = camera_manager.get_camera_status()
            await manager.send_personal_message(
                json.dumps({
                    "type": "status_update",
                    "cameras": status,
                    "timestamp": asyncio.get_event_loop().time()
                }),
                websocket
            )
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket client {client_id} disconnected")


# Background task to send detection updates
async def send_detection_updates():
    """Background task to send detection updates to WebSocket clients"""
    while True:
        try:
            # Get latest detection logs
            db = next(get_db())
            latest_logs = db.query(DetectionLog).order_by(DetectionLog.timestamp.desc()).limit(10).all()
            
            # Prepare update message
            update_data = {
                "type": "detection_update",
                "logs": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "faces_detected": log.faces_detected,
                        "students_recognized": log.students_recognized,
                        "camera_location": log.camera_location
                    }
                    for log in latest_logs
                ]
            }
            
            # Broadcast to all connected clients
            await manager.broadcast(json.dumps(update_data))
            
        except Exception as e:
            logger.error(f"Error sending detection updates: {e}")
        
        await asyncio.sleep(10)  # Update every 10 seconds
