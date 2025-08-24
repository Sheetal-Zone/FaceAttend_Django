import pytest
from fastapi.testclient import TestClient
from app.auth import create_access_token, verify_token
from main import app

client = TestClient(app)

def test_login_success():
    """Test successful admin login."""
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401

def test_protected_endpoint_with_token():
    """Test accessing protected endpoint with valid token."""
    # First login to get token
    login_response = client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]
    
    # Access protected endpoint
    response = client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True

def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token."""
    response = client.get("/api/v1/auth/me")
    
    assert response.status_code == 401

def test_token_verification():
    """Test JWT token verification."""
    # Create a valid token
    token = create_access_token(data={"sub": "admin"})
    
    # Verify the token
    username = verify_token(token)
    assert username == "admin"

def test_invalid_token_verification():
    """Test invalid token verification."""
    username = verify_token("invalid_token")
    assert username is None
