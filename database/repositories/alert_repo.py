"""
Alerts Repository.

Collection: alerts
"""

from typing import Dict, Any, List, Optional
from pymongo.database import Database
from database.connection import get_db


class AlertRepository:
    """Repository handling CRUD operations for the alerts collection."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_db()
        self.collection = self.db["alerts"]

    def insert_one(self, alert_dict: Dict[str, Any]) -> str:
        res = self.collection.insert_one(alert_dict)
        return str(res.inserted_id)

    def insert_many(self, alert_dicts: List[Dict[str, Any]]) -> List[str]:
        if not alert_dicts:
            return []
        res = self.collection.insert_many(alert_dicts)
        return [str(i) for i in res.inserted_ids]

    def find_by_alert_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"alert_id": alert_id}, {"_id": 0})

    def list_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        return list(self.collection.find({"patient_id": patient_id}, {"_id": 0}))

    def count(self) -> int:
        return self.collection.count_documents({})

    def clear(self) -> None:
        self.collection.delete_many({})


__all__ = ["AlertRepository"]
