"""
Backend API Inspection Controller & Orchestration Engine.

Purpose:
    Orchestrates the entire production inspection session flow:
    Device ID -> Patient & Prescription Lookup -> Vision -> Inventory -> OCR -> Clinical -> Alerting -> MongoDB Persistence.

FULL WORKFLOW per scan:
    1.  Resolve device -> patient -> prescriptions -> today's schedules
    2.  Run AI pipeline (Models A→B→C) on the uploaded image
    3.  Reload last scan count from MongoDB (survives server restarts)
    4.  Compare present count vs previous: compute delta
    5.  Evaluate clinical rules: CORRECT_DOSE / DOSE_MISSED / EXTRA_DOSE / WRONG_MEDICINE / EXPIRED_MEDICINE
    6.  If CORRECT_DOSE → mark closest PENDING schedule as COMPLETED in MongoDB
    7.  If DOSE_MISSED / EXTRA_DOSE → mark schedule as MISSED
    8.  Persist: inspection_session, inspection_result (with strip_id), compliance_decision, alerts
    9.  Alerts include: patient, device, ward, type, status fields for Alerts page
    10. Return full payload so frontend updates all panels simultaneously
"""

import uuid
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
import numpy as np

from pipeline.inspection_result import InspectionResult, PocketResult
from inventory.manager import InventoryManager
from ocr.manager import OCRManager
from clinical.manager import ClinicalDecisionManager
from clinical.models import Prescription, DoseSchedule
from alerting.manager import AlertManager
from backend.models import APIResponse

from database.repositories import (
    DeviceRepository,
    PatientRepository,
    PrescriptionRepository,
    ScheduleRepository,
    InspectionRepository,
    ComplianceRepository,
    AlertRepository,
    MedicineCatalogueRepository,
)

logger = logging.getLogger(__name__)


class InspectionController:
    """Controller orchestrating camera inspection, clinical pipeline evaluation, and session persistence."""

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

        from database.connection import get_db
        self.db = db if db is not None else get_db()

        # Database repositories
        self.dev_repo   = DeviceRepository(self.db)
        self.pat_repo   = PatientRepository(self.db)
        self.rx_repo    = PrescriptionRepository(self.db)
        self.sched_repo = ScheduleRepository(self.db)
        self.insp_repo  = InspectionRepository(self.db)
        self.comp_repo  = ComplianceRepository(self.db)
        self.alert_repo = AlertRepository(self.db)
        self.med_repo   = MedicineCatalogueRepository(self.db)

        # Preload and cache AI pipeline for instant inference
        self.pipe = None
        try:
            from app.pipeline import Pipeline
            self.pipe = Pipeline.from_defaults()
            logger.info("AI Pipeline preloaded successfully.")
        except Exception as e:
            logger.warning("Could not preload AI pipeline: %s", e)



    # ──────────────────────────────────────────────────────────────────────
    def inspect_device_session(
        self,
        device_id: str,
        image_array: Optional[np.ndarray] = None,
        raw_inspection: Optional[Dict[str, Any]] = None,
        simulated_ocr_text: Optional[str] = None,
        expected_layout: Optional[Tuple[int, int]] = None,
    ) -> APIResponse:
        """
        Execute end-to-end device inspection session with full trace persistence.

        Steps:
            1. Device → Patient → Prescription → Schedule lookup
            2. AI vision pipeline (or raw_inspection fallback)
            3. Reload previous scan from MongoDB (crash-safe history)
            4. Clinical evaluation including NOT_TAKEN / EXTRA_DOSE
            5. Update schedule status in MongoDB
            6. Persist session, compliance decision, alerts (with all frontend fields)
            7. Return unified payload
        """
        start_t  = time.time()
        session_id = f"sess_{uuid.uuid4().hex[:10]}"
        ist_tz   = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.now(ist_tz)

        # ── 1. Device Lookup ───────────────────────────────────────────────
        device = self.dev_repo.find_by_id(device_id)
        if not device:
            return APIResponse.error(f"Device '{device_id}' is not registered.", status_code=440)

        patient_id = device["patient_id"]
        ward       = device.get("ward", "")
        room       = device.get("room", "")

        # ── 2. Patient & Prescriptions Lookup ─────────────────────────────
        patient = self.pat_repo.find_by_id(patient_id)
        if not patient:
            return APIResponse.error(f"Patient '{patient_id}' not found.", status_code=404)

        prescriptions = self.rx_repo.find_by_patient_id(patient_id)
        if not prescriptions:
            return APIResponse.error(f"No active prescriptions for '{patient_id}'.", status_code=400)

        primary_rx_dict = prescriptions[0]
        rx = Prescription(
            prescription_id=primary_rx_dict["prescription_id"],
            patient_id=patient_id,
            medicine_name=primary_rx_dict["medicine_name"],
            strength=primary_rx_dict["strength"],
            dosage_form=primary_rx_dict.get("dosage_form", "Tablet"),
        )

        # ── 3. Resolve Closest Schedule & Grace Window ────────────────────
        patient_schedules = self.sched_repo.find_by_patient_id(patient_id)
        sched_time_obj    = timestamp
        sched_id          = f"sched_{uuid.uuid4().hex[:6]}"
        grace_mins        = 5  # 5-minute pre/post dose adherence window
        strip_id          = f"strip_{patient_id}_{device_id}"

        chosen_sched   = None
        best_score     = (99, float("inf"))

        if patient_schedules:
            local_now = timestamp.astimezone(ist_tz)
            today_key = local_now.date().isoformat()
            for ps in patient_schedules:
                status_upper = str(ps.get("status", "PENDING")).upper()
                if status_upper not in {"PENDING", "MISSED"}:
                    continue
                schedule_date = str(ps.get("date") or ps.get("schedule_date") or "")[:10]
                if schedule_date and schedule_date != today_key:
                    continue
                t_str = ps.get("target_time", "")
                if t_str and ":" in t_str:
                    try:
                        hh, mm = map(int, t_str.split(":"))
                        target_local = local_now.replace(hour=hh, minute=mm, second=0, microsecond=0)
                        target_utc   = target_local.astimezone(timezone.utc)
                        diff = abs((timestamp.astimezone(timezone.utc) - target_utc).total_seconds())
                        has_baseline = False
                        try:
                            has_baseline = bool(self.db["scan_baselines"].find_one({
                                "strip_id": strip_id,
                                "schedule_id": ps.get("schedule_id", ""),
                            }))
                        except Exception:
                            has_baseline = False

                        if status_upper == "MISSED" and not has_baseline:
                            continue

                        score = (0 if has_baseline else 1, diff)
                        if score < best_score:
                            best_score = score
                            sched_time_obj = target_utc
                            sched_id     = ps.get("schedule_id", sched_id)
                            chosen_sched = ps
                    except Exception as e:
                        logger.warning("Error parsing schedule time '%s': %s", t_str, e)

        if chosen_sched is None:
            return APIResponse.error(
                "No active image-scan schedule found for this patient. Add a schedule 2-5 minutes in the future, then run Scan #1 before the scheduled time.",
                status_code=409,
            )

        sched = DoseSchedule(
            schedule_id=sched_id,
            prescription_id=rx.prescription_id,
            scheduled_time=sched_time_obj,
            grace_period_minutes=grace_mins,
        )

        # ── 4. AI Vision Pipeline ─────────────────────────────────────────
        strip_id = f"strip_{patient_id}_{device_id}"
        baseline_doc = None
        try:
            baseline_doc = self.db["scan_baselines"].find_one({
                "strip_id": strip_id,
                "schedule_id": sched_id
            })
        except Exception:
            pass

        now_utc = timestamp.astimezone(timezone.utc)
        sched_utc = sched.scheduled_time.astimezone(timezone.utc) if sched.scheduled_time.tzinfo else sched.scheduled_time
        if baseline_doc is None and now_utc > sched_utc + timedelta(minutes=grace_mins):
            return APIResponse.error(
                "This schedule is already past its baseline window. Add a new schedule 2-5 minutes in the future and run Scan #1 before it is due.",
                status_code=409,
            )

        # Layout precedence: the confirmed layout stored with the baseline (so every later scan of this strip
        # must match the same geometry), else the operator's layout, else none (detection only, no expectation).
        baseline_layout = None
        if baseline_doc and baseline_doc.get("layout_rows") and baseline_doc.get("layout_cols"):
            baseline_layout = (int(baseline_doc["layout_rows"]), int(baseline_doc["layout_cols"]))
        layout_expected = baseline_layout or expected_layout
        layout_source = "baseline" if baseline_layout else ("operator" if expected_layout else "detected")

        if image_array is not None:
            try:
                pipe = self.pipe
                if pipe is None:
                    from app.pipeline import Pipeline
                    pipe = Pipeline.from_defaults()
                    self.pipe = pipe
                t_vision = time.perf_counter()
                insp_result = pipe.run(image_array, expected_layout=layout_expected) if layout_expected else pipe.run(image_array)
                logger.info(
                    "AI pipeline completed in %.0f ms: total=%d present=%d missing=%d",
                    (time.perf_counter() - t_vision) * 1000, insp_result.total, insp_result.present, insp_result.missing,
                )
            except Exception as err:
                logger.error("Vision pipeline failed: %s", err, exc_info=True)
                return APIResponse.error(f"Vision pipeline failed: {err}", status_code=500)

        elif raw_inspection:
            tot = max(1, raw_inspection.get("total", 10))
            pockets = [
                PocketResult(
                    index=i + 1,
                    class_name="missing" if (i + 1) in raw_inspection.get("missing_indices", []) else "present",
                    confidence=0.99,
                    bbox=(0, 0, 10, 10),
                )
                for i in range(tot)
            ]
            insp_result = InspectionResult(
                total=tot,
                present=raw_inspection.get("present", tot),
                missing=raw_inspection.get("missing", 0),
                avg_confidence=raw_inspection.get("avg_confidence", 0.99),
                pockets=pockets,
            )
        else:
            return APIResponse.error("No image or raw_inspection supplied; nothing to inspect.", status_code=400)

        # Grid geometry (rows x cols x pockets) is reported separately from tablet presence (tablet_counts).
        def _layout_info():
            return {
                "rows": insp_result.layout_rows, "cols": insp_result.layout_cols, "pockets": insp_result.total,
                "source": layout_source,  # baseline | operator | detected
                "expected": list(layout_expected) if layout_expected else None,
                "uncertain": insp_result.layout_uncertain, "verification": insp_result.verification,
            }

        # Never invent a count: a failed, empty, mismatched or low-confidence inspection is an error.
        if insp_result.error:
            return APIResponse.error(insp_result.status, status_code=500, data={"layout": _layout_info()})
        if insp_result.total <= 0:
            return APIResponse.error(
                "No blister pockets detected. Check camera position, lighting and that the strip is in view.",
                status_code=422, data={"layout": _layout_info()},
            )
        if insp_result.verification != "VERIFIED":
            msg = insp_result.status
            if insp_result.verification == "CONFIG_MISMATCH" and layout_source == "baseline":
                msg += (" The baseline for this strip used that layout; if the blister or camera position changed, "
                        "start a new baseline (new schedule).")
            elif insp_result.layout_uncertain:
                msg += " Retake the photo with the whole blister in view and scan again."
            return APIResponse.error(msg, status_code=422, data={"layout": _layout_info()})

        # ── 5. Inventory Subsystem — Schedule-Linked Baseline Tracking ─────
        strip_id = f"strip_{patient_id}_{device_id}"
        eff_total = max(1, insp_result.total)
        current_present = insp_result.present

        # Check if a baseline has already been established for this schedule/dose cycle
        baseline_doc = None
        try:
            baseline_doc = self.db["scan_baselines"].find_one({
                "strip_id": strip_id,
                "schedule_id": sched_id
            })
        except Exception:
            pass

        sched_to_evaluate = None

        if baseline_doc is None:
            now_utc = timestamp.astimezone(timezone.utc)
            sched_utc = sched.scheduled_time.astimezone(timezone.utc) if sched.scheduled_time.tzinfo else sched.scheduled_time
            if now_utc > sched_utc + timedelta(minutes=grace_mins):
                return APIResponse.error(
                    "This schedule is already past its baseline window. Add a new schedule 2-5 minutes in the future and run Scan #1 before it is due.",
                    status_code=409,
                )

            # THIS IS SCAN #1 (FIRST SCAN / PRE-DOSE BASELINE)
            # Record whatever tablet count is present on the strip (e.g. 10, 8, 7, etc.)
            logger.info("Scan #1 (Baseline) for strip=%s schedule=%s: initial present=%d", strip_id, sched_id, current_present)
            try:
                self.db["scan_baselines"].insert_one({
                    "strip_id": strip_id,
                    "schedule_id": sched_id,
                    "patient_id": patient_id,
                    "device_id": device_id,
                    "baseline_present": current_present,
                    "total_slots": eff_total,
                    "layout_rows": insp_result.layout_rows or None,  # geometry this strip's later scans must match
                    "layout_cols": insp_result.layout_cols or None,
                    "layout_source": layout_source,
                    "created_at": timestamp.isoformat(),
                })
            except Exception as e:
                logger.warning("Could not persist baseline: %s", e)

            # Establish initial reference in inventory manager
            self.inventory_mgr._histories.pop(strip_id, None)
            state, event = self.inventory_mgr.from_inspection(insp_result, strip_id=strip_id)
            # Scan #1 is baseline setup -> evaluated without schedule constraint to produce PENDING
            sched_to_evaluate = None
        else:
            # THIS IS SCAN #2 (POST-DOSE VERIFICATION)
            # Compare directly against the recorded initial baseline_present (e.g. 10 -> 9 or 8 -> 7)
            raw_baseline_present = baseline_doc.get("baseline_present", current_present)
            baseline_present = max(0, min(eff_total, raw_baseline_present))
            logger.info("Scan #2 (Verification) for strip=%s schedule=%s: baseline=%d (raw=%d), current=%d",
                        strip_id, sched_id, baseline_present, raw_baseline_present, current_present)

            base_pockets = [
                PocketResult(index=i, class_name="present" if i <= baseline_present else "missing",
                             confidence=0.99, bbox=(0, 0, 10, 10))
                for i in range(1, eff_total + 1)
            ]
            base_insp = InspectionResult(
                total=eff_total,
                present=baseline_present,
                missing=max(0, eff_total - baseline_present),
                avg_confidence=0.99,
                pockets=base_pockets,
            )
            self.inventory_mgr._histories.pop(strip_id, None)
            self.inventory_mgr.from_inspection(base_insp, strip_id=strip_id)
            state, event = self.inventory_mgr.from_inspection(insp_result, strip_id=strip_id)
            # Scan #2 is verification -> evaluate against scheduled time window
            sched_to_evaluate = sched

        # ── 6. OCR Subsystem ──────────────────────────────────────────────
        identity       = None
        ocr_result_dict = None

        if image_array is not None:
            try:
                t_ocr = time.perf_counter()
                ocr_res = self.ocr_mgr.process_image(image_array, preprocess=True)
                logger.info("front-image OCR completed in %.0f ms", (time.perf_counter() - t_ocr) * 1000)
                identity = ocr_res.identity
                ocr_result_dict = ocr_res.to_dict()
            except Exception as e:
                logger.warning("OCR failed: %s", e)

        elif simulated_ocr_text:
            from ocr.parser import OCREntityParser
            identity = OCREntityParser.parse(simulated_ocr_text)
            ocr_result_dict = {
                "raw_text": simulated_ocr_text,
                "identity": identity.to_dict(),
                "status": "VERIFIED",
            }

        if identity and identity.medicine_name and identity.medicine_name != "Unknown Medicine":
            try:
                cat = self.med_repo.find_by_name(identity.medicine_name) or \
                      self.med_repo.find_by_alias(identity.medicine_name)
                if cat:
                    from dataclasses import replace
                    identity = replace(identity, medicine_name=cat["brand"])
            except Exception:
                pass

        # ── 7. Clinical Decision Engine ───────────────────────────────────
        decision = self.clinical_mgr.evaluate_event(
            event=event,
            prescription=rx,
            identity=identity,
            schedule=sched_to_evaluate,
        )


        # ── 8. Alert Engine ───────────────────────────────────────────────
        messages = self.alert_mgr.process_decision(decision)

        # ── 9. Persist Session ────────────────────────────────────────────
        session_dict = {
            "session_id":          session_id,
            "device_id":           device_id,
            "patient_id":          patient_id,
            "patient_name":        patient.get("name", ""),
            "ward":                ward,
            "timestamp":           timestamp.isoformat(),
            "status":              decision.outcome.value,
            "processing_time_sec": round(time.time() - start_t, 3),
        }

        # Include strip_id in inspection_result dict so find_last_present_count works
        insp_result_dict = insp_result.to_dict()
        insp_result_dict["strip_id"] = strip_id
        insp_result_dict["present"]  = insp_result.present

        self.insp_repo.insert_session(
            session_dict=session_dict,
            inspection_result=insp_result_dict,
            inventory_event=event.to_dict(),
            ocr_result=ocr_result_dict,
        )

        # ── 10. Persist Compliance Decision ───────────────────────────────
        self.comp_repo.insert_one(decision.to_dict())

        # ── 11. Persist Alerts with ALL frontend-required fields ──────────
        if messages:
            alert_docs = []
            for m in messages:
                d = m.to_dict()
                sev_val = str(m.severity.value if hasattr(m.severity, "value") else m.severity).upper()
                st_val = "Critical" if sev_val == "CRITICAL" else ("Warning" if sev_val == "WARNING" else "Resolved")

                d["alert_id"]    = m.alert_id
                d["schedule_id"]  = chosen_sched.get("schedule_id", sched_id) if chosen_sched else sched_id
                d["patient_id"]  = patient_id
                d["patient"]     = f"{patient.get('name', patient_id)} ({patient_id})"
                d["device"]      = device_id
                d["device_id"]   = device_id
                d["ward"]        = ward or "Ward A"
                d["room"]        = room or "Room 1"
                d["type"]        = "Medication"
                d["desc"]        = m.message or m.title
                d["description"] = m.message or m.title
                d["title"]       = m.title
                d["message"]     = m.message
                d["time"]        = timestamp.strftime("%H:%M:%S")
                d["timestamp"]   = timestamp.isoformat()
                d["status"]      = st_val
                d["session_id"]  = session_id
                alert_docs.append(d)
            self.alert_repo.insert_many(alert_docs)


        # ── 12. Update Schedule Status in MongoDB ─────────────────────────
        from clinical.enums import DecisionOutcome
        schedule_update_status = None
        if decision.outcome == DecisionOutcome.CORRECT_DOSE:
            schedule_update_status = "COMPLETED"
        elif decision.outcome in (DecisionOutcome.DOSE_MISSED,):
            schedule_update_status = "MISSED"
        elif decision.outcome == DecisionOutcome.EXTRA_DOSE:
            schedule_update_status = "OVERDOSE"

        if schedule_update_status and chosen_sched:
            self.sched_repo.update_status(chosen_sched["schedule_id"], schedule_update_status)
            logger.info("Schedule %s → %s", chosen_sched["schedule_id"], schedule_update_status)

        if decision.outcome == DecisionOutcome.CORRECT_DOSE and chosen_sched:
            try:
                self.alert_repo.collection.update_many(
                    {
                        "schedule_id": chosen_sched["schedule_id"],
                        "patient_id": patient_id,
                        "status": {"$in": ["Active", "Warning", "Critical"]},
                    },
                    {
                        "$set": {
                            "status": "Resolved",
                            "acknowledged": True,
                            "resolved_at": timestamp.isoformat(),
                            "resolution": "Correct dose verified by follow-up scan.",
                        }
                    },
                )
            except Exception as e:
                logger.warning("Could not resolve prior dose alerts: %s", e)

        # Also update device last_scan timestamp and slots_used
        try:
            self.dev_repo.collection.update_one(
                {"device_id": device_id},
                {"$set": {
                    "last_scan":   timestamp.isoformat(),
                    "slots_used":  insp_result.missing,
                }},
            )
        except Exception as e:
            logger.warning("Could not update device last_scan: %s", e)

        # ── 13. Return Full Response Payload ──────────────────────────────
        return APIResponse.ok({
            "session_id":   session_id,
            "device_id":    device_id,
            "strip_id":     strip_id,
            "scan_time":    timestamp.isoformat(),
            "patient": {
                "patient_id": patient["patient_id"],
                "name":       patient["name"],
                "ward":       ward,
                "room":       room,
            },
            "prescription": rx.to_dict(),
            "schedule": {
                "schedule_id":  sched_id,
                "target_time":  chosen_sched.get("target_time", "") if chosen_sched else "",
                "status":       schedule_update_status or "PENDING",
                "medicine":     rx.medicine_name,
                "strength":     rx.strength,
            },
            "inventory_state": state.to_dict(),
            "inventory_event": event.to_dict(),
            # Top-level counts for easy frontend access
            "tablet_counts": {
                "total":   insp_result.total,
                "present": insp_result.present,
                "missing": insp_result.missing,
                "delta":   event.delta_present if hasattr(event, "delta_present") else 0,
            },
            "layout": _layout_info(),
            "medicine_identity": identity.to_dict() if identity else None,
            "decision": decision.to_dict(),
            "compliance_decision": decision.to_dict(),
            "dispatched_alerts":  [m.to_dict() for m in messages],
            "ocr_result":         ocr_result_dict,
        })

    # ──────────────────────────────────────────────────────────────────────
    def _load_last_present_count(self, strip_id: str) -> Optional[int]:
        """Load last known present tablet count for a strip from MongoDB."""
        try:
            return self.insp_repo.find_last_present_count(strip_id)
        except Exception as e:
            logger.warning("Could not load last present count from DB: %s", e)
            return None

    @staticmethod
    def _severity_to_type(severity: str) -> str:
        """Map alert severity to frontend type string."""
        mapping = {
            "CRITICAL": "Critical",
            "WARNING":  "Warning",
            "INFO":     "Medication",
        }
        return mapping.get(severity.upper(), "Medication")

    def inspect_and_evaluate(
        self,
        raw_inspection: Dict[str, Any],
        prescription_dict: Dict[str, Any],
        strip_id: Optional[str] = None,
        image_array: Optional[np.ndarray] = None,
    ) -> APIResponse:
        """
        Direct/legacy inspection evaluation for POST /api/v1/inspect endpoint.
        Processes raw inspection or image array against supplied prescription and strip ID.
        """
        if not strip_id:
            strip_id = f"strip_{prescription_dict.get('patient_id', 'unknown')}"

        # 1. Parse or construct inspection result
        if image_array is not None and not raw_inspection:
            try:
                pipe = self.pipe
                if pipe is None:
                    from app.pipeline import Pipeline
                    pipe = Pipeline.from_defaults()
                    self.pipe = pipe
                insp_result = pipe.run(image_array)
            except Exception as err:
                return APIResponse.error(f"Vision pipeline failed: {err}", status_code=500)
        elif raw_inspection:
            tot = max(1, raw_inspection.get("total", 10))
            pres = raw_inspection.get("present", tot)
            miss = raw_inspection.get("missing", tot - pres)
            miss_idx = raw_inspection.get("missing_indices", [])
            pockets = [
                PocketResult(
                    index=i + 1,
                    class_name="missing" if (i + 1) in miss_idx else "present",
                    confidence=raw_inspection.get("avg_confidence", 0.99),
                    bbox=(0, 0, 10, 10),
                )
                for i in range(tot)
            ]
            insp_result = InspectionResult(
                total=tot,
                present=pres,
                missing=miss,
                avg_confidence=raw_inspection.get("avg_confidence", 0.99),
                pockets=pockets,
            )
        else:
            return APIResponse.error("No inspection data or image provided.", status_code=400)

        # 2. Inventory tracking
        state, event = self.inventory_mgr.from_inspection(insp_result, strip_id=strip_id)

        # 3. OCR processing if image supplied
        identity = None
        if image_array is not None:
            try:
                ocr_res = self.ocr_mgr.process_image(image_array, preprocess=True)
                identity = ocr_res.identity
            except Exception as e:
                logger.warning("OCR processing error in inspect_and_evaluate: %s", e)

        # 4. Prescription object construction
        rx = Prescription(
            prescription_id=prescription_dict.get("prescription_id", "rx_default"),
            patient_id=prescription_dict.get("patient_id", "patient_default"),
            medicine_name=prescription_dict.get("medicine_name", "Paracetamol"),
            strength=prescription_dict.get("strength", "500mg"),
            dosage_form=prescription_dict.get("dosage_form", "Tablet"),
        )

        # 5. Clinical compliance decision
        decision = self.clinical_mgr.evaluate_event(
            event=event,
            prescription=rx,
            identity=identity,
        )

        # 6. Alert dispatch
        messages = self.alert_mgr.process_decision(decision)

        return APIResponse.ok({
            "strip_id": strip_id,
            "inventory_state": state.to_dict(),
            "inventory_event": event.to_dict(),
            "decision": decision.to_dict(),
            "medicine_identity": identity.to_dict() if identity else None,
            "dispatched_alerts": [m.to_dict() for m in messages],
        })


__all__ = ["InspectionController"]
