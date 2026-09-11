"""
Clinical Compliance Decisions Repository.

Collection: clinical_decisions
"""

from typing import Dict, Any, List, Optional
from pymongo.database import Database
from database.connection import get_db


class ComplianceRepository:
    """Repository handling CRUD operations for the clinical_decisions collection."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_db()
        self.collection = self.db["clinical_decisions"]

    def insert_one(self, decision_dict: Dict[str, Any]) -> str:
        res = self.collection.insert_one(decision_dict)
        return str(res.inserted_id)

    def find_by_decision_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"decision_id": decision_id}, {"_id": 0})

    def list_by_patient_id(self, patient_id: str) -> List[Dict[str, Any]]:
        return list(self.collection.find({"patient_id": patient_id}, {"_id": 0}))

    def count(self) -> int:
        return self.collection.count_documents({})

    def clear(self) -> None:
        self.collection.delete_many({})


__all__ = ["ComplianceRepository"]
