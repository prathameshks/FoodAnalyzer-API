from sqlalchemy.orm import Session
from models.scan_history import ScanHistory
from datetime import datetime

def record_scan(db: Session, user_id: int, product_id: int) -> ScanHistory:
    scan_entry = ScanHistory(
        user_id=user_id,
        product_id=product_id,
        scan_date=datetime.utcnow()
    )
    db.add(scan_entry)
    db.commit()
    db.refresh(scan_entry)
    return scan_entry

def get_scan_history(db: Session, user_id: int) -> list[ScanHistory]:
    return db.query(ScanHistory)\
        .filter(ScanHistory.user_id == user_id)\
        .order_by(ScanHistory.scan_date.desc())\
        .all()