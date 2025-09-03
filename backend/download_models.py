#!/usr/bin/env python3
"""
Download required AI models for face recognition and liveness detection
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_yolo_model():
    """Download YOLO model for face detection"""
    try:
        from ultralytics import YOLO
        import urllib.request
        
        models_dir = Path("models")
        models_dir.mkdir(exist_ok=True)
        
        # Try a list of potential YOLO model filenames/aliases
        candidate_names = [
            "yolov11n.pt",  # preferred if available
            "yolov10n.pt",
            "yolov9n.pt",
            "yolov8n.pt",  # widely available
        ]
        download_urls = {
            "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
        }
        
        # If any already exists, return it
        for name in candidate_names:
            existing = models_dir / name
            if existing.exists():
                logger.info(f"YOLO model already exists at {existing}")
                return str(existing)
        
        last_error = None
        logger.info("Downloading YOLO model (trying multiple candidates)...")
        
        # Try to load via Ultralytics registry first
        for name in candidate_names:
            try:
                logger.info(f"Trying to load '{name}' via Ultralytics...")
                model = YOLO(name)
                target_path = models_dir / name
                # Some versions of ultralytics expose model.ckpt or export/save; fall back to direct save if present
                try:
                    model.save(str(target_path))
                except Exception:
                    # If save is not supported, export to ONNX as a fallback (still places weights in cache)
                    try:
                        model.export(format="onnx")
                    except Exception:
                        pass
                    # Copy from cache if available
                    if not target_path.exists():
                        # Ultralytics caches under ~/.cache or appdirs; if not accessible, skip
                        pass
                if target_path.exists():
                    logger.info(f"YOLO model downloaded and saved to {target_path}")
                    return str(target_path)
            except Exception as e:
                last_error = e
                logger.warning(f"Ultralytics load failed for {name}: {e}")
        
        # Fallback: direct HTTP download for known public asset
        for name, url in download_urls.items():
            try:
                logger.info(f"Attempting direct download from {url}...")
                target_path = models_dir / name
                urllib.request.urlretrieve(url, str(target_path))
                logger.info(f"YOLO model downloaded directly to {target_path}")
                return str(target_path)
            except Exception as e:
                last_error = e
                logger.warning(f"Direct download failed for {name}: {e}")
        
        raise RuntimeError(last_error or "Unable to download YOLO model")
        
    except Exception as e:
        logger.error(f"Failed to download YOLO model: {e}")
        return None

def download_insightface_models():
    """Download InsightFace models for face recognition and liveness detection"""
    try:
        import insightface
        from insightface.app import FaceAnalysis
        
        logger.info("Downloading InsightFace models...")
        
        # This will automatically download the required models
        app = FaceAnalysis(name='buffalo_l')
        app.prepare(ctx_id=0, det_size=(640, 640))
        
        logger.info("InsightFace models downloaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download InsightFace models: {e}")
        return False

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        'ultralytics',
        'insightface',
        'opencv-python',
        'numpy',
        'torch'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
            elif package == 'torch':
                import torch
            else:
                __import__(package)
            logger.info(f"✓ {package} is available")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"✗ {package} is missing")
    
    if missing_packages:
        logger.error(f"Missing packages: {missing_packages}")
        logger.info("Please install missing packages using: pip install " + " ".join(missing_packages))
        return False
    
    return True

def main():
    """Main function to download all required models"""
    logger.info("🚀 Starting AI model download...")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Dependencies check failed. Please install missing packages first.")
        sys.exit(1)
    
    # Download YOLO model
    yolo_path = download_yolo_model()
    if not yolo_path:
        logger.error("Failed to download YOLO model")
        sys.exit(1)
    
    # Download InsightFace models
    if not download_insightface_models():
        logger.error("Failed to download InsightFace models")
        sys.exit(1)
    
    logger.info("🎉 All AI models downloaded successfully!")
    logger.info(f"YOLO model: {yolo_path}")
    logger.info("InsightFace models: Downloaded and ready")
    
    # Test model loading
    logger.info("Testing model loading...")
    try:
        from app.ai_models import face_recognition_system, liveness_detection_system
        
        face_recognition_system.initialize_models()
        liveness_detection_system.initialize_models()
        
        logger.info("✓ All models loaded successfully!")
        
    except Exception as e:
        logger.error(f"✗ Model loading test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
