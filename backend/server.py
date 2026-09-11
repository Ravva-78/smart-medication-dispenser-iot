"""
Backend API Service Facade (DispenserAPIService).

Purpose:
    Exposes unified facade methods for REST API routes and health checks.
"""

from typing import Dict, Any, Optional
import numpy as np

from inventory.manager import InventoryManager
from ocr.manager import OCRManager
from clinical.manager import ClinicalDecisionManager
from alerting.manager import AlertManager
from backend.models import APIResponse
from backend.controllers import InspectionController

from database.connection import verify_connection
from database.repositories import (
    DeviceRepository,
    PatientRepository,
    PrescriptionRepository,
    ScheduleRepository,
    AlertRepository,
)


class DispenserAPIService:
    """Primary Backend Service Facade delegating to API controllers and subsystem managers."""

    def __init__(
        self,
        inventory_mgr: Optional[InventoryManager] = None,
        ocr_mgr: Optional[OCRManager] = None,
        clinical_mgr: Optional[ClinicalDecisionManager] = None,
        alert_mgr: Optional[AlertManager] = None,
        db: Optional[Any] = None,
    ):
        self.inventory_mgr = inventory_mgr if inventory_mgr is not None else InventoryManager()
        self.ocr_mgr = ocr_mgr if ocr_mgr is not None else OCRManager()
        self.clinical_mgr = clinical_mgr if clinical_mgr is not None else ClinicalDecisionManager()
        self.alert_mgr = alert_mgr if alert_mgr is not None else AlertManager()

        self.inspection_controller = InspectionController(
            inventory_mgr=self.inventory_mgr,
            ocr_mgr=self.ocr_mgr,
            clinical_mgr=self.clinical_mgr,
            alert_mgr=self.alert_mgr,
            db=db,
        )

        self.pat_repo = PatientRepository(db)
        self.dev_repo = DeviceRepository(db)
        self.rx_repo = PrescriptionRepository(db)
        self.sched_repo = ScheduleRepository(db)
        self.alert_repo = AlertRepository(db)

    def health(self) -> APIResponse:
        """GET /api/v1/health endpoint."""
        db_ok = verify_connection()
        return APIResponse.ok({
            "status": "HEALTHY" if db_ok else "DEGRADED",
            "version": "1.0.0",
            "database": "CONNECTED" if db_ok else "OFFLINE",
            "services": {
                "inventory": "UP",
                "ocr": "UP",
                "clinical": "UP",
                "alerting": "UP",
            }
        })

    def inspect_device(
        self,
        device_id: str,
        image_array: Optional[np.ndarray] = None,
        raw_inspection: Optional[Dict[str, Any]] = None,
        simulated_ocr_text: Optional[str] = None,
    ) -> APIResponse:
        """POST /api/v1/devices/{device_id}/inspection endpoint."""
        return self.inspection_controller.inspect_device_session(
            device_id=device_id,
            image_array=image_array,
            raw_inspection=raw_inspection,
            simulated_ocr_text=simulated_ocr_text,
        )

    def process_inspection_and_evaluate(
        self,
        raw_inspection: Dict[str, Any],
        prescription: Dict[str, Any],
        strip_id: Optional[str] = None,
        image_array: Optional[np.ndarray] = None,
    ) -> APIResponse:
        """Backward-compatibility method for process_inspection_and_evaluate."""
        return self.inspection_controller.inspect_and_evaluate(
            raw_inspection=raw_inspection,
            prescription_dict=prescription,
            strip_id=strip_id,
            image_array=image_array,
        )

    def get_patient(self, patient_id: str) -> APIResponse:
        """GET /api/v1/patients/{patient_id} endpoint."""
        patient = self.pat_repo.find_by_id(patient_id)
        if not patient:
            return APIResponse.error(f"Patient '{patient_id}' not found.", status_code=404)
        return APIResponse.ok(patient)

    def get_patient_prescriptions(self, patient_id: str) -> APIResponse:
        """GET /api/v1/patients/{patient_id}/prescriptions endpoint."""
        prescriptions = self.rx_repo.find_by_patient_id(patient_id)
        return APIResponse.ok({"prescriptions": prescriptions})

    def get_patient_schedule(self, patient_id: str) -> APIResponse:
        """GET /api/v1/patients/{patient_id}/schedule endpoint."""
        schedules = self.sched_repo.find_by_patient_id(patient_id)
        return APIResponse.ok({"schedules": schedules})

    def get_patient_metrics(self, patient_id: str) -> APIResponse:
        """GET /api/v1/clinical/metrics/{patient_id} endpoint."""
        metrics = self.clinical_mgr.get_patient_metrics(patient_id)
        return APIResponse.ok(metrics)

    def get_alert_history(self, patient_id: str) -> APIResponse:
        """GET /api/v1/alerts/{patient_id} endpoint."""
        alerts = self.alert_repo.list_by_patient_id(patient_id)
        return APIResponse.ok({"alerts": alerts})


__all__ = ["DispenserAPIService"]
