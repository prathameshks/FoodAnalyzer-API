from sqlalchemy.orm import Session
from models.scan_history import ScanHistory
from datetime import datetime

def record_scan(db: Session, user_id: int, product_id: int):
    scan_entry = ScanHistory(user_id=user_id, product_id=product_id, scan_date=datetime.utcnow())
    db.add(scan_entry)
    db.commit()
    db.refresh(scan_entry)
    return scan_entry

def get_scan_history(db: Session, user_id: int):
    return db.query(ScanHistory).filter(ScanHistory.user_id == user_id).all()
