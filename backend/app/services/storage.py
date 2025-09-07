"""
Storage Service - Photo and File Management
"""

import os
import logging
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

class StorageService:
    """Service for managing photo storage and file operations"""
    
    def __init__(self, base_media_path: str = "media"):
        self.base_media_path = Path(base_media_path)
        self.students_path = self.base_media_path / "students"
        self.detections_path = self.base_media_path / "detections"
        
        # Create directories if they don't exist
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories"""
        try:
            self.students_path.mkdir(parents=True, exist_ok=True)
            self.detections_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Storage directories created at {self.base_media_path}")
        except Exception as e:
            logger.error(f"Failed to create storage directories: {e}")
            raise
    
    def save_registration_photo(self, student_id: int, image: np.ndarray) -> Optional[str]:
        """
        Save student registration photo
        
        Args:
            student_id: Student ID
            image: Image as numpy array
            
        Returns:
            Path to saved image or None if failed
        """
        try:
            # Create student directory
            student_dir = self.students_path / str(student_id)
            student_dir.mkdir(parents=True, exist_ok=True)
            
            # Save image
            photo_path = student_dir / "registration.jpg"
            success = cv2.imwrite(str(photo_path), image)
            
            if success:
                logger.info(f"Registration photo saved: {photo_path}")
                return str(photo_path)
            else:
                logger.error(f"Failed to save registration photo for student {student_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving registration photo: {e}")
            return None
    
    def save_detection_photo(self, student_id: int, image: np.ndarray, 
                           timestamp: Optional[datetime] = None) -> Optional[str]:
        """
        Save detection snapshot
        
        Args:
            student_id: Student ID
            image: Image as numpy array
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Path to saved image or None if failed
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Create student detection directory
            student_dir = self.detections_path / str(student_id)
            student_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            photo_path = student_dir / filename
            
            # Save image
            success = cv2.imwrite(str(photo_path), image)
            
            if success:
                logger.info(f"Detection photo saved: {photo_path}")
                return str(photo_path)
            else:
                logger.error(f"Failed to save detection photo for student {student_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving detection photo: {e}")
            return None
    
    def get_registration_photo_path(self, student_id: int) -> Optional[str]:
        """
        Get path to student's registration photo
        
        Args:
            student_id: Student ID
            
        Returns:
            Path to photo or None if not found
        """
        photo_path = self.students_path / str(student_id) / "registration.jpg"
        if photo_path.exists():
            return str(photo_path)
        return None
    
    def delete_student_photos(self, student_id: int) -> bool:
        """
        Delete all photos for a student
        
        Args:
            student_id: Student ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete registration photo
            student_dir = self.students_path / str(student_id)
            if student_dir.exists():
                import shutil
                shutil.rmtree(student_dir)
                logger.info(f"Deleted registration photos for student {student_id}")
            
            # Delete detection photos
            detection_dir = self.detections_path / str(student_id)
            if detection_dir.exists():
                import shutil
                shutil.rmtree(detection_dir)
                logger.info(f"Deleted detection photos for student {student_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting photos for student {student_id}: {e}")
            return False
    
    def get_storage_stats(self) -> dict:
        """
        Get storage statistics
        
        Returns:
            Dictionary with storage statistics
        """
        try:
            stats = {
                "total_students": 0,
                "total_detections": 0,
                "total_size_mb": 0
            }
            
            # Count students with photos
            if self.students_path.exists():
                student_dirs = [d for d in self.students_path.iterdir() if d.is_dir()]
                stats["total_students"] = len(student_dirs)
            
            # Count detection photos
            if self.detections_path.exists():
                detection_dirs = [d for d in self.detections_path.iterdir() if d.is_dir()]
                total_detections = 0
                for detection_dir in detection_dirs:
                    if detection_dir.is_dir():
                        photos = list(detection_dir.glob("*.jpg"))
                        total_detections += len(photos)
                stats["total_detections"] = total_detections
            
            # Calculate total size
            total_size = 0
            for path in [self.students_path, self.detections_path]:
                if path.exists():
                    for file_path in path.rglob("*"):
                        if file_path.is_file():
                            total_size += file_path.stat().st_size
            
            stats["total_size_mb"] = round(total_size / (1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}

# Global storage service instance
storage_service = StorageService()
