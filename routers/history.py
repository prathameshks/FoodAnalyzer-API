from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from services.scan_history import record_scan, get_scan_history
from models.scan_history import ScanHistory

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
    scan_entry = record_scan(db, scan.user_id, scan.product_id)
    return scan_entry

@router.get("/history/{user_id}", response_model=list[ScanHistoryResponse])
def read_scan_history(user_id: int, db: Session = Depends(get_db)):
    scan_history = get_scan_history(db, user_id)
    if not scan_history:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan history not found")
    return scan_history
