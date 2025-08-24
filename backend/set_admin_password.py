#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'face_attendance.settings')
django.setup()

from django.contrib.auth.models import User

# Set admin password
try:
    admin_user = User.objects.get(username='admin')
    admin_user.set_password('admin123')
    admin_user.save()
    print("Admin password set successfully!")
    print("Username: admin")
    print("Password: admin123")
except User.DoesNotExist:
    print("Admin user not found. Creating one...")
    admin_user = User.objects.create_superuser('admin', 'admin@faceattendance.local', 'admin123')
    print("Admin user created successfully!")
    print("Username: admin")
    print("Password: admin123")
except Exception as e:
    print(f"Error: {e}")
