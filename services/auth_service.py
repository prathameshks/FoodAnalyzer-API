from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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



def verify_password(plain_password, hashed_password):
    log_info("Verifying password")
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        log_error(f"Error verifying password: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_password_hash(password):
    log_info("Hashing password")
    try:
        return pwd_context.hash(password)
    except Exception as e:
        log_error(f"Error hashing password: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_user(db, username: str):
    log_info(f"Getting user: {username}")
    try:
        return db.query(User).filter(User.username == username).first()
    except Exception as e:
        log_error(f"Error getting user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def authenticate_user(db, username: str, password: str):
    log_info(f"Authenticating user: {username}")
    try:
        user = get_user(db, username)
        if not user:
            return False
        if not verify_password(password, user.hashed_password):
            return False
        return user
    except Exception as e:
        log_error(f"Error authenticating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    log_info("Creating access token")
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        log_error(f"Error creating access token: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    log_info("Getting current user")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        log_error(f"JWT error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        log_error(f"Error decoding token: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    log_info("Getting current active user")
    try:
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return UserResponse.from_orm(current_user)
    except Exception as e:
        log_error(f"Error getting current active user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

def create_user(db: Session, username: str, email: str, password: str):
    log_info(f"Creating user: {username}")
    try:
        hashed_password = get_password_hash(password)
        db_user = User(username=username, email=email, hashed_password=hashed_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        log_error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
