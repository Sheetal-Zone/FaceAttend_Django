import pytest
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.models import Student
from main import app

client = TestClient(app)

@pytest.fixture
def auth_token():
    """Get authentication token for tests."""
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return response.json()["access_token"]

@pytest.fixture
def db_session():
    """Get database session for tests."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_create_student(auth_token, db_session):
    """Test creating a new student."""
    student_data = {
        "name": "Test Student",
        "roll_number": "TEST001",
        "photo_url": "https://example.com/photo.jpg"
    }
    
    response = client.post(
        "/api/v1/students/",
        json=student_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "student_id" in data["data"]
    
    # Verify in database
    student = db_session.query(Student).filter_by(roll_number="TEST001").first()
    assert student is not None
    assert student.name == "Test Student"

def test_create_student_duplicate_roll_number(auth_token):
    """Test creating student with duplicate roll number."""
    student_data = {
        "name": "Test Student 2",
        "roll_number": "TEST001",  # Same roll number
        "photo_url": "https://example.com/photo2.jpg"
    }
    
    response = client.post(
        "/api/v1/students/",
        json=student_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_get_students(auth_token):
    """Test getting list of students."""
    response = client.get(
        "/api/v1/students/",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data

def test_get_student_by_id(auth_token, db_session):
    """Test getting a specific student by ID."""
    # First create a student
    student = Student(
        name="Test Student",
        roll_number="TEST002",
        photo_url="https://example.com/photo.jpg"
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    
    response = client.get(
        f"/api/v1/students/{student.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Student"
    assert data["roll_number"] == "TEST002"

def test_update_student(auth_token, db_session):
    """Test updating a student."""
    # First create a student
    student = Student(
        name="Test Student",
        roll_number="TEST003",
        photo_url="https://example.com/photo.jpg"
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    
    update_data = {
        "name": "Updated Student Name"
    }
    
    response = client.put(
        f"/api/v1/students/{student.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    
    # Verify in database
    updated_student = db_session.query(Student).filter_by(id=student.id).first()
    assert updated_student.name == "Updated Student Name"

def test_delete_student(auth_token, db_session):
    """Test deleting a student."""
    # First create a student
    student = Student(
        name="Test Student",
        roll_number="TEST004",
        photo_url="https://example.com/photo.jpg"
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    
    response = client.delete(
        f"/api/v1/students/{student.id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    
    # Verify deleted from database
    deleted_student = db_session.query(Student).filter_by(id=student.id).first()
    assert deleted_student is None

def test_search_students(auth_token):
    """Test searching students."""
    response = client.get(
        "/api/v1/students/?search=Test",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
