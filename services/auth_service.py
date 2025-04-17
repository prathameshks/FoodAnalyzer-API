from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
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



def verify_password(plain_password, hashed_password):
    log_info("Verifying password")
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        log_error(f"Error verifying password: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_password_hash(password):
    log_info("Hashing password")
    try:
        return pwd_context.hash(password)
    except Exception as e:
        log_error(f"Error hashing password: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def get_user(db, email: str):
    log_info(f"Getting user: {email}")
    try:
        return db.query(User).filter(func.lower(User.email) == email.lower()).first()
    except Exception as e:
        log_error(f"Error getting user: {str(e)}")
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

async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
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
        log_error(f"JWT error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        log_error(f"Error decoding token: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    user = get_user(db, email=token_data.email)
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
        log_error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))