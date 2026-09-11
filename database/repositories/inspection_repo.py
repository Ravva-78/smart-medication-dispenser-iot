"""
Inspection Session & Inspection Results Repository.

Collections: inspection_sessions, inspection_results, inventory_events, ocr_results
"""

from typing import Dict, Any, List, Optional
from pymongo.database import Database
from database.connection import get_db


class InspectionRepository:
    """Repository handling CRUD operations for inspection sessions and vision/inventory/ocr results."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_db()
        self.sessions = self.db["inspection_sessions"]
        self.inspection_results = self.db["inspection_results"]
        self.inventory_events = self.db["inventory_events"]
        self.ocr_results = self.db["ocr_results"]

    def insert_session(
        self,
        session_dict: Dict[str, Any],
        inspection_result: Optional[Dict[str, Any]] = None,
        inventory_event: Optional[Dict[str, Any]] = None,
        ocr_result: Optional[Dict[str, Any]] = None,
    ) -> str:
        res = self.sessions.insert_one(session_dict)
        session_id = session_dict.get("session_id")

        if session_id:
            if inspection_result:
                inspection_result["session_id"] = session_id
                self.inspection_results.insert_one(inspection_result)
            if inventory_event:
                inventory_event["session_id"] = session_id
                self.inventory_events.insert_one(inventory_event)
            if ocr_result:
                ocr_result["session_id"] = session_id
                self.ocr_results.insert_one(ocr_result)

        return str(res.inserted_id)

    def find_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.find_one({"session_id": session_id}, {"_id": 0})

    def find_last_by_strip_id(self, strip_id: str) -> Optional[Dict[str, Any]]:
        """Return the most recent inspection_result doc for a given strip_id."""
        doc = self.inspection_results.find_one(
            {"strip_id": strip_id},
            {"_id": 0},
            sort=[("session_id", -1)],
        )
        return doc

    def find_last_present_count(self, strip_id: str) -> Optional[int]:
        """Return the present_count from the most recent scan for this strip_id, or None."""
        doc = self.inspection_results.find_one(
            {"strip_id": strip_id},
            {"_id": 0, "present": 1},
            sort=[("session_id", -1)],
        )
        if doc:
            return doc.get("present")
        return None

    def list_sessions_by_patient(self, patient_id: str) -> List[Dict[str, Any]]:
        return list(self.sessions.find({"patient_id": patient_id}, {"_id": 0}))

    def count_sessions(self) -> int:
        return self.sessions.count_documents({})

    def clear(self) -> None:
        self.sessions.delete_many({})
        self.inspection_results.delete_many({})
        self.inventory_events.delete_many({})
        self.ocr_results.delete_many({})



__all__ = ["InspectionRepository"]
