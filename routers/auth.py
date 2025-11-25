from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordRequestForm
from db.database import get_db
from services.auth_service import authenticate_user, create_access_token, create_user, get_current_active_user, get_user
from datetime import timedelta
from db.models import User
from logger_manager import log_info, log_error
from interfaces.authModels import UserCreate,UserResponse,Token
from env import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user: UserCreate, db: Session = Depends(get_db)):
    log_info("Register endpoint called")
    # Check if user already exists
    existing_user = get_user(db, user.email)
    if existing_user:
        log_error(f"User with email {user.email} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        db_user = create_user(db, user.name, user.email, user.password)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        log_info("User registered successfully")
        return {"access_token": access_token, "token_type": "bearer"}
    except IntegrityError:
        log_error(f"Duplicate email: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Error in register endpoint: {str(e)}", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    log_info("Login endpoint called")
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        log_error("Incorrect username or password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(weeks=4)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    log_info("User logged in successfully")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/user", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    log_info("Read users/me endpoint called")
    return current_user
        
@router.get("/user/email", response_model=UserResponse)
def read_user_by_email(email: str, db: Session = Depends(get_db)):
    log_info("Read user by email endpoint called")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        log_error("User not found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
