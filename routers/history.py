from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from services.scan_history import record_scan, get_scan_history
from models.scan_history import ScanHistory
from services.logging_service import log_info, log_error

router = APIRouter()

class ScanHistoryCreate(BaseModel):
    user_id: int
    product_id: int

class ScanHistoryResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    scan_date: str

@router.post("/scan", response_model=ScanHistoryResponse)
def create_scan(scan: ScanHistoryCreate, db: Session = Depends(get_db)):
    log_info("Create scan endpoint called")
    try:
        scan_entry = record_scan(db, scan.user_id, scan.product_id)
        log_info("Scan recorded successfully")
        return scan_entry
    except Exception as e:
        log_error(f"Error in create_scan endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/scan/{user_id}", response_model=list[ScanHistoryResponse])
def read_scan_history(user_id: int, db: Session = Depends(get_db)):
    log_info("Read scan history endpoint called")
    try:
        scan_history = get_scan_history(db, user_id)
        if not scan_history:
            log_error("Scan history not found")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan history not found")
        log_info("Scan history retrieved successfully")
        return scan_history
    except Exception as e:
        log_error(f"Error in read_scan_history endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
