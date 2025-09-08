import json
import base64
import cv2
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import (
    CameraStream, Student, Attendance, DetectionLog, 
    UnrecognizedFace, RecognitionSession, RealTimeStats
)
from .face_recognition_engine import FaceRecognitionEngine
import asyncio
import logging

logger = logging.getLogger(__name__)

class DetectionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = "detection_room"
        self.room_group_name = "detection_group"
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Detection consumer connected: {self.channel_name}")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Detection consumer disconnected: {self.channel_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'start_detection':
                await self.start_detection(data)
            elif message_type == 'stop_detection':
                await self.stop_detection(data)
            elif message_type == 'frame_data':
                await self.process_frame(data)
            elif message_type == 'get_stats':
                await self.send_stats()
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def start_detection(self, data):
        camera_id = data.get('camera_id')
        grid_size = data.get('grid_size', 2)
        
        # Start detection session
        session = await self.create_detection_session(camera_id)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'detection_started',
                'session_id': session.session_id,
                'camera_id': camera_id,
                'grid_size': grid_size
            }
        )

    async def stop_detection(self, data):
        session_id = data.get('session_id')
        await self.end_detection_session(session_id)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'detection_stopped',
                'session_id': session_id
            }
        )

    async def process_frame(self, data):
        camera_id = data.get('camera_id')
        frame_data = data.get('frame_data')
        session_id = data.get('session_id')
        
        # Process frame with face detection and recognition
        results = await self.process_frame_async(camera_id, frame_data, session_id)
        
        # Send results back to the client
        await self.send(text_data=json.dumps({
            'type': 'frame_processed',
            'results': results
        }))

    async def send_stats(self):
        stats = await self.get_real_time_stats()
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': stats
        }))

    @database_sync_to_async
    def create_detection_session(self, camera_id):
        camera = CameraStream.objects.get(id=camera_id)
        session = RecognitionSession.objects.create(
            session_id=f"session_{camera_id}_{int(timezone.now().timestamp())}",
            camera=camera
        )
        return session

    @database_sync_to_async
    def end_detection_session(self, session_id):
        try:
            session = RecognitionSession.objects.get(session_id=session_id)
            session.is_active = False
            session.ended_at = timezone.now()
            session.save()
        except RecognitionSession.DoesNotExist:
            pass

    @database_sync_to_async
    def process_frame_async(self, camera_id, frame_data, session_id):
        try:
            camera = CameraStream.objects.get(id=camera_id)
            
            # Decode frame data
            frame_bytes = base64.b64decode(frame_data.split(',')[1])
            nparr = np.frombuffer(frame_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Initialize face recognition engine
            engine = FaceRecognitionEngine()
            
            # Process frame
            start_time = timezone.now()
            results = engine.process_frame(frame, camera)
            processing_time = (timezone.now() - start_time).total_seconds()
            
            # Update session stats
            session = RecognitionSession.objects.get(session_id=session_id)
            session.total_frames_processed += 1
            session.total_faces_detected += results.get('faces_detected', 0)
            session.total_faces_recognized += results.get('faces_recognized', 0)
            session.average_processing_time = (
                (session.average_processing_time * (session.total_frames_processed - 1) + processing_time) 
                / session.total_frames_processed
            )
            session.save()
            
            # Create detection log
            DetectionLog.objects.create(
                camera=camera,
                camera_type=camera.camera_type,
                faces_detected=results.get('faces_detected', 0),
                students_recognized=results.get('faces_recognized', 0),
                processing_time=processing_time,
                confidence_scores=results.get('confidence_scores', []),
                unrecognized_faces=results.get('unrecognized_faces', 0),
                recognition_accuracy=results.get('recognition_accuracy', 0.0),
                frame_data=frame_data,
                detection_metadata=results.get('metadata', {})
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            return {'error': str(e)}

    @database_sync_to_async
    def get_real_time_stats(self):
        # Get latest stats or create new ones
        stats, created = RealTimeStats.objects.get_or_create(
            timestamp__date=timezone.now().date(),
            defaults={
                'total_faces_detected': 0,
                'total_faces_recognized': 0,
                'total_unrecognized_faces': 0,
                'total_recognized_not_assessed': 0,
                'active_cameras': CameraStream.objects.filter(is_active=True).count(),
                'active_sessions': RecognitionSession.objects.filter(is_active=True).count(),
                'average_processing_time': 0.0
            }
        )
        
        # Update stats with current data
        stats.total_faces_detected = DetectionLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).aggregate(total=models.Sum('faces_detected'))['total'] or 0
        
        stats.total_faces_recognized = DetectionLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).aggregate(total=models.Sum('students_recognized'))['total'] or 0
        
        stats.total_unrecognized_faces = UnrecognizedFace.objects.filter(
            status='PENDING'
        ).count()
        
        stats.total_recognized_not_assessed = Student.objects.filter(
            assessment_status='Not Assessed'
        ).count()
        
        stats.active_cameras = CameraStream.objects.filter(is_active=True).count()
        stats.active_sessions = RecognitionSession.objects.filter(is_active=True).count()
        
        # Calculate average processing time
        avg_time = DetectionLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).aggregate(avg=models.Avg('processing_time'))['avg'] or 0.0
        stats.average_processing_time = avg_time
        
        stats.save()
        
        return {
            'total_faces_detected': stats.total_faces_detected,
            'total_faces_recognized': stats.total_faces_recognized,
            'total_unrecognized_faces': stats.total_unrecognized_faces,
            'total_recognized_not_assessed': stats.total_recognized_not_assessed,
            'active_cameras': stats.active_cameras,
            'active_sessions': stats.active_sessions,
            'average_processing_time': stats.average_processing_time
        }

    async def detection_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'detection_started',
            'session_id': event['session_id'],
            'camera_id': event['camera_id'],
            'grid_size': event['grid_size']
        }))

    async def detection_stopped(self, event):
        await self.send(text_data=json.dumps({
            'type': 'detection_stopped',
            'session_id': event['session_id']
        }))

    async def stats_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats']
        }))


class CameraConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.camera_id = self.scope['url_route']['kwargs']['camera_id']
        self.room_group_name = f"camera_{self.camera_id}"
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"Camera consumer connected for camera {self.camera_id}")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"Camera consumer disconnected for camera {self.camera_id}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'camera_status':
                await self.update_camera_status(data)
            elif message_type == 'frame_data':
                await self.broadcast_frame(data)
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        except Exception as e:
            logger.error(f"Error in camera consumer: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def update_camera_status(self, data):
        status = data.get('status')
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'camera_status_update',
                'status': status,
                'camera_id': self.camera_id
            }
        )

    async def broadcast_frame(self, data):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'frame_broadcast',
                'frame_data': data.get('frame_data'),
                'camera_id': self.camera_id
            }
        )

    async def camera_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'camera_status_update',
            'status': event['status'],
            'camera_id': event['camera_id']
        }))

    async def frame_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'frame_broadcast',
            'frame_data': event['frame_data'],
            'camera_id': event['camera_id']
        }))


class StatsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "stats_group"
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info("Stats consumer connected")

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info("Stats consumer disconnected")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'get_stats':
                stats = await self.get_stats()
                await self.send(text_data=json.dumps({
                    'type': 'stats_update',
                    'stats': stats
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        except Exception as e:
            logger.error(f"Error in stats consumer: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    @database_sync_to_async
    def get_stats(self):
        # Get real-time statistics
        stats, created = RealTimeStats.objects.get_or_create(
            timestamp__date=timezone.now().date(),
            defaults={
                'total_faces_detected': 0,
                'total_faces_recognized': 0,
                'total_unrecognized_faces': 0,
                'total_recognized_not_assessed': 0,
                'active_cameras': CameraStream.objects.filter(is_active=True).count(),
                'active_sessions': RecognitionSession.objects.filter(is_active=True).count(),
                'average_processing_time': 0.0
            }
        )
        
        return {
            'total_faces_detected': stats.total_faces_detected,
            'total_faces_recognized': stats.total_faces_recognized,
            'total_unrecognized_faces': stats.total_unrecognized_faces,
            'total_recognized_not_assessed': stats.total_recognized_not_assessed,
            'active_cameras': stats.active_cameras,
            'active_sessions': stats.active_sessions,
            'average_processing_time': stats.average_processing_time
        }

    async def stats_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'stats_update',
            'stats': event['stats']
        }))
