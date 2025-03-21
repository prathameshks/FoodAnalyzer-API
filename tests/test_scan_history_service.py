import unittest
from unittest.mock import MagicMock
from datetime import datetime
from sqlalchemy.orm import Session
from models.scan_history import ScanHistory
from services.scan_history import record_scan, get_scan_history

class TestScanHistoryService(unittest.TestCase):

    def setUp(self):
        self.db = MagicMock(spec=Session)
        self.user_id = 1
        self.product_id = 123
        self.scan_date = datetime.utcnow()

    def test_record_scan(self):
        scan_entry = ScanHistory(user_id=self.user_id, product_id=self.product_id, scan_date=self.scan_date)
        self.db.add.return_value = None
        self.db.commit.return_value = None
        self.db.refresh.return_value = None

        result = record_scan(self.db, self.user_id, self.product_id)

        self.db.add.assert_called_once_with(scan_entry)
        self.db.commit.assert_called_once()
        self.db.refresh.assert_called_once_with(scan_entry)
        self.assertEqual(result.user_id, self.user_id)
        self.assertEqual(result.product_id, self.product_id)
        self.assertEqual(result.scan_date, self.scan_date)

    def test_get_scan_history(self):
        scan_entry = ScanHistory(user_id=self.user_id, product_id=self.product_id, scan_date=self.scan_date)
        self.db.query.return_value.filter.return_value.all.return_value = [scan_entry]

        result = get_scan_history(self.db, self.user_id)

        self.db.query.assert_called_once_with(ScanHistory)
        self.db.query.return_value.filter.assert_called_once_with(ScanHistory.user_id == self.user_id)
        self.db.query.return_value.filter.return_value.all.assert_called_once()
        self.assertEqual(result, [scan_entry])

if __name__ == '__main__':
    unittest.main()
