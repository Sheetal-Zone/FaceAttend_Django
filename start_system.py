#!/usr/bin/env python3
"""
Complete System Startup Script
Starts both Django frontend and FastAPI backend
"""

import subprocess
import time
import requests
import sys
import os
from pathlib import Path

def check_port(port):
    """Check if a port is available"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def wait_for_service(url, timeout=30):
    """Wait for a service to become available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def start_fastapi():
    """Start FastAPI backend"""
    print("🚀 Starting FastAPI backend...")
    
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ Backend directory not found!")
        return None
    
    # Change to backend directory
    os.chdir(backend_dir)
    
    # Start FastAPI
    process = subprocess.Popen([
        sys.executable, "start_fastapi.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for FastAPI to start
    print("⏳ Waiting for FastAPI to start...")
    if wait_for_service("http://localhost:8001/health"):
        print("✅ FastAPI backend started successfully on port 8001")
        return process
    else:
        print("❌ Failed to start FastAPI backend")
        process.terminate()
        return None

def start_django():
    """Start Django frontend"""
    print("🚀 Starting Django frontend...")
    
    # Change back to root directory
    os.chdir(Path(__file__).parent)
    
    # Start Django
    process = subprocess.Popen([
        sys.executable, "manage.py", "runserver", "8000"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for Django to start
    print("⏳ Waiting for Django to start...")
    if wait_for_service("http://localhost:8000"):
        print("✅ Django frontend started successfully on port 8000")
        return process
    else:
        print("❌ Failed to start Django frontend")
        process.terminate()
        return None

def run_tests():
    """Run end-to-end tests"""
    print("🧪 Running end-to-end tests...")
    
    backend_dir = Path("backend")
    os.chdir(backend_dir)
    
    try:
        result = subprocess.run([
            sys.executable, "test_end_to_end.py"
        ], capture_output=True, text=True, timeout=60)
        
        print("Test Output:")
        print(result.stdout)
        
        if result.stderr:
            print("Test Errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
            return True
        else:
            print("❌ Some tests failed!")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out!")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    finally:
        os.chdir(Path(__file__).parent)

def main():
    """Main startup function"""
    print("🎯 Face Attendance System - Complete Startup")
    print("=" * 50)
    
    # Check if ports are available
    if not check_port(8001):
        print("❌ Port 8001 is already in use. Please stop the FastAPI server first.")
        return False
    
    if not check_port(8000):
        print("❌ Port 8000 is already in use. Please stop the Django server first.")
        return False
    
    processes = []
    
    try:
        # Start FastAPI backend
        fastapi_process = start_fastapi()
        if not fastapi_process:
            return False
        processes.append(("FastAPI", fastapi_process))
        
        # Start Django frontend
        django_process = start_django()
        if not django_process:
            return False
        processes.append(("Django", django_process))
        
        # Wait a bit for both services to stabilize
        print("⏳ Waiting for services to stabilize...")
        time.sleep(5)
        
        # Run tests
        if run_tests():
            print("\n🎉 System is fully operational!")
            print("\n📋 Access URLs:")
            print("  • Frontend Dashboard: http://localhost:8000")
            print("  • Student Registration: http://localhost:8000/registration/")
            print("  • Live Detection: http://localhost:8000/detection/")
            print("  • FastAPI Docs: http://localhost:8001/docs")
            print("  • Health Check: http://localhost:8001/health")
            print("  • Metrics: http://localhost:8001/metrics")
            
            print("\n⌨️  Press Ctrl+C to stop all services")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Shutting down services...")
        else:
            print("\n❌ System tests failed. Please check the logs.")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    finally:
        # Clean up processes
        for name, process in processes:
            print(f"🛑 Stopping {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        print("✅ All services stopped")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
