#!/usr/bin/env python3
"""
Django Startup Script
Runs migrations and starts the Django server
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Start Django server"""
    try:
        print("🚀 Starting Django Face Attendance System...")
        
        # Run Django migrations
        print("🗄️  Running Django migrations...")
        subprocess.run([sys.executable, "manage.py", "makemigrations", "attendance"], check=True)
        subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
        print("✅ Django migrations completed!")
        
        # Start Django server
        print("🌐 Starting Django server on port 8000...")
        print("📱 Web Interface: http://localhost:8000")
        print("🔑 Admin Login: admin / admin123")
        print("⏹️  Press Ctrl+C to stop the server")
        
        subprocess.run([sys.executable, "manage.py", "runserver", "0.0.0.0:8000"], check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Django command failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting Django server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
