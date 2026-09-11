"""
Device Repository.

Collection: devices
"""

from typing import Dict, Any, List, Optional
from pymongo.database import Database
from database.connection import get_db


class DeviceRepository:
    """Repository handling CRUD operations for the devices collection."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_db()
        self.collection = self.db["devices"]

    def insert_one(self, device_dict: Dict[str, Any]) -> str:
        res = self.collection.insert_one(device_dict)
        return str(res.inserted_id)

    def find_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"device_id": device_id}, {"_id": 0})

    def find_by_patient_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"patient_id": patient_id}, {"_id": 0})

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self.collection.find({}, {"_id": 0}))

    def count(self) -> int:
        return self.collection.count_documents({})

    def clear(self) -> None:
        self.collection.delete_many({})


__all__ = ["DeviceRepository"]
