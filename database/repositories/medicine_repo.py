"""
Medicine Master Catalogue Repository.

Collection: medicine_catalogue
"""

from typing import Dict, Any, List, Optional
from pymongo.database import Database
from database.connection import get_db


class MedicineCatalogueRepository:
    """Repository handling CRUD operations for the medicine_catalogue collection."""

    def __init__(self, db: Optional[Database] = None):
        self.db = db if db is not None else get_db()
        self.collection = self.db["medicine_catalogue"]

    def insert_one(self, medicine_dict: Dict[str, Any]) -> str:
        res = self.collection.insert_one(medicine_dict)
        return str(res.inserted_id)

    def insert_many(self, medicines: List[Dict[str, Any]]) -> List[str]:
        if not medicines:
            return []
        res = self.collection.insert_many(medicines)
        return [str(i) for i in res.inserted_ids]

    def find_by_id(self, medicine_id: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one({"medicine_id": medicine_id}, {"_id": 0})

    def find_by_name(self, brand_name: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one(
            {"brand": {"$regex": f"^{brand_name}$", "$options": "i"}},
            {"_id": 0}
        )

    def find_by_alias(self, text_token: str) -> Optional[Dict[str, Any]]:
        return self.collection.find_one(
            {"ocr_aliases": {"$regex": f"^{text_token}$", "$options": "i"}},
            {"_id": 0}
        )

    def list_all(self) -> List[Dict[str, Any]]:
        return list(self.collection.find({}, {"_id": 0}))

    def count(self) -> int:
        return self.collection.count_documents({})

    def clear(self) -> None:
        self.collection.delete_many({})


__all__ = ["MedicineCatalogueRepository"]
