from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
import logging

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError as e:
        logging.getLogger(__name__).warning(f"JWT verification failed: {e}")
        return None


def authenticate_admin(username: str, password: str) -> bool:
    """Authenticate admin user"""
    # Compare directly against configured admin credentials.
    # Note: For production, store and compare a persistent password hash.
    return (username == settings.admin_username and password == settings.admin_password)


async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Get current authenticated admin user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    logger = logging.getLogger(__name__)
    if not token:
        logger.warning("401 Unauthorized: Missing Bearer token on protected endpoint access")
        raise credentials_exception
    username = verify_token(token)
    if username is None or username != settings.admin_username:
        logger.warning("401 Unauthorized: Invalid or unauthorized token used to access protected endpoint")
        raise credentials_exception
    
    return username


# Initialize admin password hash on startup
def init_admin_password():
    """Initialize admin password hash"""
    hashed_password = get_password_hash(settings.admin_password)
    return hashed_password


def create_admin_user():
    """Create admin user in the database if it doesn't exist"""
    try:
        from app.database import SessionLocal
        from app.models import AdminUser
        
        db = SessionLocal()
        try:
            # Check if admin user already exists
            admin_user = db.query(AdminUser).filter(AdminUser.username == settings.admin_username).first()
            
            if not admin_user:
                # Create new admin user
                admin_user = AdminUser(
                    username=settings.admin_username,
                    hashed_password=get_password_hash(settings.admin_password),
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                logging.getLogger(__name__).info("Admin user created successfully")
            else:
                logging.getLogger(__name__).info("Admin user already exists")
                
        finally:
            db.close()
            
    except Exception as e:
        logging.getLogger(__name__).warning(f"Admin user creation failed: {e}")
        # This is not critical, so we don't raise an exception
