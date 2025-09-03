#!/usr/bin/env python3
"""
FastAPI Startup Script
Initializes database and starts the FastAPI server
"""

import sys
import os
from pathlib import Path

# Add the current directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Start FastAPI server"""
    try:
        print("🚀 Starting FastAPI Face Attendance System...")
        
        # Initialize database
        print("🗄️  Initializing database...")
        from scripts.init_db import init_database
        if not init_database():
            print("❌ Database initialization failed!")
            sys.exit(1)
        
        print("✅ Database initialized successfully!")
        
        # Start FastAPI server
        print("🌐 Starting FastAPI server on port 8001...")
        print("📚 API Documentation: http://localhost:8001/docs")
        print("🔑 Admin Login: admin / admin123")
        print("⏹️  Press Ctrl+C to stop the server")
        
        import uvicorn
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8001,
            reload=True,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
