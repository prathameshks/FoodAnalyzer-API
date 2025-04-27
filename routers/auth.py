from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from db.database import get_db
from services.auth_service import authenticate_user, create_access_token, create_user, get_current_active_user
from datetime import timedelta
from db.models import User
from logger_manager import log_info, log_error
from interfaces.authModels import UserCreate,UserResponse,Token

router = APIRouter()


@router.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    log_info("Register endpoint called")
    try:
        db_user = create_user(db, user.name, user.email, user.password)
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        log_info("User registered successfully")
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        log_error(f"Error in register endpoint: {str(e)}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    log_info("Login endpoint called")
    try:
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
    except Exception as e:
        log_error(f"Error in login endpoint: {str(e)}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/user", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    log_info("Read users/me endpoint called")
    try:
        return current_user
    except Exception as e:
        log_error(f"Error in read_users_me endpoint: {str(e)}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
        
@router.get("/user/email", response_model=UserResponse)
def read_user_by_email(email: str, db: Session = Depends(get_db)):
    log_info("Read user by email endpoint called")
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            log_error("User not found")
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except Exception as e:
        log_error(f"Error in read_user_by_email endpoint: {str(e)}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
