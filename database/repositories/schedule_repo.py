"""
Daily Schedule Repository.

Collection: daily_schedule
"""

from typing import Dict, Any, List, Optional
from pymongo.database import Database
from database.connection import get_db


class ScheduleRepository:
    """Repository handling CRUD operations for the daily_schedule collection."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_db()
        self.collection = self.db["daily_schedule"]

    def insert_one(self, schedule_dict: Dict[str, Any]) -> str:
        res = self.collection.insert_one(schedule_dict)
        return str(res.inserted_id)

    def insert_many(self, schedules: List[Dict[str, Any]]) -> List[str]:
        if not schedules:
            return []
        res = self.collection.insert_many(schedules)
        return [str(i) for i in res.inserted_ids]

    def find_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        return list(self.collection.find({"patient_id": patient_id}, {"_id": 0}))

    def update_status(self, schedule_id: str, new_status: str) -> bool:
        res = self.collection.update_one(
            {"schedule_id": schedule_id},
            {"$set": {"status": new_status}}
        )
        return res.modified_count > 0

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self.collection.find({}, {"_id": 0}))

    def count(self) -> int:
        return self.collection.count_documents({})

    def clear(self) -> None:
        self.collection.delete_many({})


__all__ = ["ScheduleRepository"]
