#!/usr/bin/env python3
"""
Test script for laptop camera functionality
"""

import cv2
import time

def test_laptop_camera():
    """Test if laptop camera can be accessed"""
    print("Testing laptop camera access...")
    
    # Try to open camera index 0 (default laptop camera)
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Failed to open laptop camera")
        return False
    
    print("✅ Laptop camera opened successfully")
    
    # Try to read a frame
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read frame from laptop camera")
        cap.release()
        return False
    
    print(f"✅ Frame read successfully: {frame.shape}")
    
    # Release camera
    cap.release()
    print("✅ Camera released successfully")
    
    return True

if __name__ == "__main__":
    test_laptop_camera()
