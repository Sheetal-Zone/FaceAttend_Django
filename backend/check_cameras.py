#!/usr/bin/env python3
"""
Check available camera devices
"""

import cv2

def check_cameras():
    """Check all available camera indices"""
    print("Checking available camera devices...")
    
    available_cameras = []
    
    # Check first 10 camera indices
    for i in range(10):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ Camera {i}: Available (Frame: {frame.shape})")
                available_cameras.append(i)
            else:
                print(f"⚠️  Camera {i}: Opened but can't read frames")
            cap.release()
        else:
            print(f"❌ Camera {i}: Not available")
    
    print(f"\n📊 Summary: {len(available_cameras)} camera(s) available")
    if available_cameras:
        print(f"Available indices: {available_cameras}")
    else:
        print("No cameras found. This might be a virtual environment or headless system.")
    
    return available_cameras

if __name__ == "__main__":
    check_cameras()
