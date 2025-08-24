from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.auth import authenticate_admin, create_access_token, get_current_admin
from app.database import get_db
from app.schemas import Token, AdminLogin, APIResponse
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(form_data: AdminLogin, db: Session = Depends(get_db)):
    """Admin login endpoint"""
    try:
        # Authenticate admin
        if not authenticate_admin(form_data.username, form_data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create access token
        access_token = create_access_token(data={"sub": form_data.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.get("/me", response_model=APIResponse)
async def get_current_user_info(current_admin: str = Depends(get_current_admin)):
    """Get current admin user information"""
    return {
        "success": True,
        "message": "Admin user information retrieved successfully",
        "data": {
            "username": current_admin,
            "role": "admin"
        }
    }


@router.post("/logout", response_model=APIResponse)
async def logout(current_admin: str = Depends(get_current_admin)):
    """Admin logout endpoint (client-side token removal)"""
    return {
        "success": True,
        "message": "Logout successful"
    }
