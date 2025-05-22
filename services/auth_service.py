from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session,Mapped
from db.database import get_db
from db.models import User
from interfaces.authModels import UserResponse,TokenData
from logger_manager import log_info, log_error

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d8f7a6b5c4e3d2f1a0b9c8d7e6f5a4"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Create an optional OAuth2 scheme that doesn't auto-error
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def verify_password(plain_password, hashed_password):
    log_info("Verifying password")
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        log_error(f"Error verifying password: {str(e)}",e)
        raise HTTPException(status_code=500, detail=str(e))

def get_password_hash(password):
    log_info("Hashing password")
    try:
        return pwd_context.hash(password)
    except Exception as e:
        log_error(f"Error hashing password: {str(e)}",e)
        raise HTTPException(status_code=500, detail=str(e))

def get_user(db, email: str):
    log_info(f"Getting user: {email}")
    try:
        return db.query(User).filter(func.lower(User.email) == email.lower()).first()
    except Exception as e:
        log_error(f"Error getting user: {str(e)}",e)
        raise HTTPException(status_code=500, detail=str(e))

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(func.lower(User.email) == username.lower()).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# New flexible token extractor
async def get_token_from_request(request: Request = None, oauth_token: str = None):
    """Extract token from various sources, prioritizing standard formats but 
    supporting Hugging Face Spaces custom headers"""
    
    # First try the standard OAuth2 token if provided
    if oauth_token:
        return oauth_token
        
    if request is None:
        return None
    
    # Try standard Authorization header (works in local development)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    # Try Hugging Face's custom header
    hf_token = request.headers.get("x-ip-token")
    if hf_token:
        log_info(f"Using token from Hugging Face x-ip-token header")
        return hf_token
    
    # Final fallback: check query parameters
    token_param = request.query_params.get("token")
    if token_param:
        log_info(f"Using token from query parameter")
        return token_param
        
    return None

# Replace or add this function
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    oauth_token: str = Depends(oauth2_scheme_optional)
):
    """Enhanced user authentication that supports both standard OAuth2
    and Hugging Face Spaces deployments"""
    
    log_info("Getting current user with flexible auth")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get token from any available source
    token = await get_token_from_request(request, oauth_token)
    
    if not token:
        log_error("No authentication token found")
        raise credentials_exception
    
    try:
        # Try to decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            log_error("Token missing 'sub' claim")
            raise credentials_exception
            
        token_data = TokenData(email=email)
        
    except JWTError as e:
        log_error(f"JWT verification failed: {str(e)}", e)
        raise credentials_exception
        
    except Exception as e:
        log_error(f"Token processing error: {str(e)}", e)
        raise HTTPException(status_code=500, detail=str(e))
    
    # Find the user
    user = get_user(db, email=token_data.email)
    if user is None:
        log_error(f"User not found: {token_data.email}")
        raise credentials_exception
        
    return user

# Add this function for active users with flexible auth
async def get_current_active_user(
    request: Request,
    db: Session = Depends(get_db),
    oauth_token: str = Depends(oauth2_scheme_optional)
):
    """Get active user with flexible authentication"""
    current_user = await get_current_user(request, db, oauth_token)
    
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return UserResponse.from_orm(current_user)

async def get_current_user_old(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    log_info("Getting current user")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError as e:
        log_error(f"JWT error: {str(e)}",e)
        raise credentials_exception
    except Exception as e:
        log_error(f"Error decoding token: {str(e)}",e)
        raise HTTPException(status_code=500, detail=str(e))
    user = get_user(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user_old(current_user: User = Depends(get_current_user_old)):
    log_info("Getting current active user")
    try:
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return UserResponse.from_orm(current_user)
    except Exception as e:
        log_error(f"Error getting current active user: {str(e)}",e)
        raise HTTPException(status_code=500, detail=str(e))

def create_user(db: Session, name: str, email: str, password: str):
    log_info(f"Creating user: {name}")
    try:
        hashed_password = get_password_hash(password)
        db_user = User(name=name, email=email.lower(), hashed_password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        log_error(f"Error creating user: {str(e)}",e)
        raise HTTPException(status_code=500, detail=str(e))