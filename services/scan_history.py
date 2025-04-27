from fastapi import HTTPException
import pytz
from sqlalchemy.orm import Session
from db.models import ScanHistory
from datetime import datetime
from logger_manager import log_info, log_error

def record_scan(db: Session, user_id: int, product_id: int) -> ScanHistory:
    log_info("Recording scan")
    try:
        scan_entry = ScanHistory(
            user_id=user_id,
            product_id=product_id,
            scan_date=datetime.now(tz=pytz.timezone('Asia/Kolkata')),
        )
        db.add(scan_entry)
        db.commit()
        db.refresh(scan_entry)
        log_info("Scan recorded successfully")
        return scan_entry
    except Exception as e:
        log_error(f"Error recording scan: {str(e)}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")

def get_scan_history(db: Session, user_id: int) -> list[ScanHistory]:
    log_info("Getting scan history")
    try:
        scan_history = db.query(ScanHistory)\
            .filter(ScanHistory.user_id == user_id)\
            .order_by(ScanHistory.scan_date.desc())\
            .all()
        log_info("Scan history retrieved successfully")
        return scan_history
    except Exception as e:
        log_error(f"Error getting scan history: {str(e)}",e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
