"""
Workflow tests for scheduled blister scan verification.
"""
import unittest
import importlib
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from backend.controllers import InspectionController


class _InsertResult:
    inserted_id = "fake_inserted_id"
    inserted_ids = ["fake_inserted_id"]


class _UpdateResult:
    modified_count = 1


class _FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def _matches(self, row, query):
        for key, expected in (query or {}).items():
            actual = row.get(key)
            if isinstance(expected, dict) and "$in" in expected:
                if actual not in expected["$in"]:
                    return False
            elif actual != expected:
                return False
        return True

    def find_one(self, query=None, projection=None, sort=None):
        for row in self.rows:
            if self._matches(row, query):
                return dict(row)
        return None

    def find(self, query=None, projection=None):
        return [dict(row) for row in self.rows if self._matches(row, query)]

    def insert_one(self, row):
        self.rows.append(dict(row))
        return _InsertResult()

    def insert_many(self, rows):
        self.rows.extend(dict(row) for row in rows)
        return _InsertResult()

    def update_one(self, query, update, upsert=False):
        for row in self.rows:
            if self._matches(row, query):
                row.update(update.get("$set", {}))
                return _UpdateResult()
        if upsert:
            created = dict(query)
            created.update(update.get("$set", {}))
            self.rows.append(created)
        return _UpdateResult()

    def update_many(self, query, update):
        for row in self.rows:
            if self._matches(row, query):
                row.update(update.get("$set", {}))
        return _UpdateResult()

    def count_documents(self, query=None):
        return len(self.find(query))

    def delete_many(self, query=None):
        self.rows = [row for row in self.rows if not self._matches(row, query)]

    def delete_one(self, query=None):
        for index, row in enumerate(self.rows):
            if self._matches(row, query):
                del self.rows[index]
                break


class _FakeDB(dict):
    def __getitem__(self, name):
        if name not in self:
            self[name] = _FakeCollection()
        return dict.__getitem__(self, name)


def _inspection(total, present):
    missing = total - present
    return {
        "total": total,
        "present": present,
        "missing": missing,
        "missing_indices": list(range(present + 1, total + 1)),
    }


class TestScheduledScanWorkflow(unittest.TestCase):
    def setUp(self):
        ist_now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
        target_time = ist_now.strftime("%H:%M")
        self.db = _FakeDB({
            "devices": _FakeCollection([{
                "device_id": "DEV-TEST-01",
                "patient_id": "PAT-TEST-01",
                "ward": "Ward T",
                "room": "Bed 1",
            }]),
            "patients": _FakeCollection([{
                "patient_id": "PAT-TEST-01",
                "name": "Test Patient",
                "ward": "Ward T",
            }]),
            "prescriptions": _FakeCollection([{
                "prescription_id": "RX-TEST-01",
                "patient_id": "PAT-TEST-01",
                "medicine_name": "Metformin",
                "strength": "500mg",
                "dosage_form": "Tablet",
                "active": True,
            }]),
            "daily_schedule": _FakeCollection([{
                "schedule_id": "SCHED-TEST-01",
                "patient_id": "PAT-TEST-01",
                "prescription_id": "RX-TEST-01",
                "medicine_name": "Metformin",
                "strength": "500mg",
                "device_id": "DEV-TEST-01",
                "target_time": target_time,
                "status": "PENDING",
                "date": ist_now.date().isoformat(),
            }]),
        })

    def _controller(self, db=None):
        with patch("app.pipeline.Pipeline.from_defaults", return_value=None):
            return InspectionController(db=db or self.db)

    def _main_module(self):
        from backend import server

        class _FakeService:
            pass

        with patch.object(server, "DispenserAPIService", _FakeService):
            sys.modules.pop("backend.main", None)
            return importlib.import_module("backend.main")

    def test_scan_requires_active_schedule(self):
        db = _FakeDB({
            "devices": self.db["devices"],
            "patients": self.db["patients"],
            "prescriptions": self.db["prescriptions"],
        })
        res = self._controller(db).inspect_device_session(
            "DEV-TEST-01",
            raw_inspection=_inspection(10, 10),
        )

        self.assertFalse(res.success)
        self.assertEqual(res.status_code, 409)
        self.assertIn("No active image-scan schedule", res.error_message)

    def test_baseline_then_one_removed_completes_schedule(self):
        controller = self._controller()

        baseline = controller.inspect_device_session(
            "DEV-TEST-01",
            raw_inspection=_inspection(10, 10),
        )
        self.assertTrue(baseline.success)
        self.assertEqual(baseline.data["decision"]["outcome"], "PENDING")

        verification = controller.inspect_device_session(
            "DEV-TEST-01",
            raw_inspection=_inspection(10, 9),
        )

        self.assertTrue(verification.success)
        self.assertEqual(verification.data["decision"]["outcome"], "CORRECT_DOSE")
        self.assertEqual(verification.data["schedule"]["status"], "COMPLETED")
        self.assertEqual(self.db["daily_schedule"].rows[0]["status"], "COMPLETED")
        self.assertTrue(all(a["status"] == "Resolved" for a in self.db["alerts"].rows))

    def test_add_schedule_route_creates_quick_pending_schedule(self):
        self.db["daily_schedule"].rows = []
        main = self._main_module()

        with patch.object(main, "_db", return_value=self.db):
            response = main.add_schedule({
                "patientId": "PAT-TEST-01",
                "minutesFromNow": "3",
            })

        self.assertEqual(response["message"], "Schedule created")
        self.assertEqual(response["data"]["patientId"], "PAT-TEST-01")
        self.assertEqual(response["data"]["status"], "PENDING")
        self.assertEqual(len(self.db["daily_schedule"].rows), 1)
        self.assertEqual(self.db["daily_schedule"].rows[0]["scan_type"], "IMAGE_BASELINE_THEN_VERIFY")

    def test_add_schedule_autocreates_rx_from_patient_medication(self):
        self.db["prescriptions"].rows = []
        self.db["daily_schedule"].rows = []
        self.db["patients"].rows[0]["medicine_name"] = "Paracetamol 650mg"
        main = self._main_module()

        with patch.object(main, "_db", return_value=self.db):
            response = main.add_schedule({
                "patientId": "PAT-TEST-01",
                "minutesFromNow": "3",
            })

        self.assertEqual(response["message"], "Schedule created")
        self.assertEqual(len(self.db["prescriptions"].rows), 1)
        self.assertEqual(self.db["prescriptions"].rows[0]["medicine_name"], "Paracetamol")
        self.assertEqual(self.db["prescriptions"].rows[0]["strength"], "650mg")
        self.assertEqual(self.db["daily_schedule"].rows[0]["prescription_id"], self.db["prescriptions"].rows[0]["prescription_id"])

    def test_patient_edit_syncs_prescription_and_pending_schedule(self):
        self.db["prescriptions"].rows = []
        self.db["daily_schedule"].rows = []
        main = self._main_module()

        with patch.object(main, "_db", return_value=self.db):
            response = main.update_patient("PAT-TEST-01", {
                "medication": "Paracetamol 650mg",
                "next": "23:45",
            })

        self.assertEqual(response["message"], "Patient updated")
        self.assertEqual(len(self.db["prescriptions"].rows), 1)
        self.assertEqual(len(self.db["daily_schedule"].rows), 1)
        self.assertEqual(self.db["prescriptions"].rows[0]["medicine_name"], "Paracetamol")
        self.assertEqual(self.db["daily_schedule"].rows[0]["medicine_name"], "Paracetamol")
        self.assertEqual(self.db["daily_schedule"].rows[0]["target_time"], "23:45")

    def test_legacy_patient_schedule_endpoint_reads_daily_schedule(self):
        main = self._main_module()

        class _EmptyScheduleService:
            def get_patient_schedule(self, patient_id):
                class _Response:
                    success = True

                    def to_dict(self):
                        return {"success": True, "data": {"schedules": []}}

                return _Response()

        with patch.object(main, "_db", return_value=self.db), patch.object(main, "_api_service", return_value=_EmptyScheduleService()):
            response = main.get_patient_schedule("PAT-TEST-01")

        self.assertEqual(response["success"], True)
        self.assertEqual(response["data"]["schedules"][0]["schedule_id"], "SCHED-TEST-01")

    def test_devices_endpoint_repairs_missing_patient_device_link(self):
        self.db["devices"].rows = []
        main = self._main_module()

        with patch.object(main, "_db", return_value=self.db):
            devices = main.list_devices()

        linked = [d for d in devices if d["patientId"] == "PAT-TEST-01"]
        self.assertEqual(len(linked), 1)
        self.assertTrue(linked[0]["id"].startswith("DEV-"))

    def test_add_patient_can_create_linked_device_rx_and_quick_schedule(self):
        db = _FakeDB({
            "patients": _FakeCollection(),
            "devices": _FakeCollection(),
            "prescriptions": _FakeCollection(),
            "daily_schedule": _FakeCollection(),
        })
        main = self._main_module()

        with patch.object(main, "_db", return_value=db):
            response = main.add_patient({
                "name": "Qwerty",
                "ward": "3B",
                "bedNumber": "Bed 2",
                "medication": "Paracetamol 500mg",
                "deviceId": "DEV-QWERTY-01",
                "minutesFromNow": "3",
            })

        self.assertIn("Patient added", response["message"])
        self.assertEqual(len(db["patients"].rows), 1)
        self.assertEqual(len(db["devices"].rows), 1)
        self.assertEqual(len(db["prescriptions"].rows), 1)
        self.assertEqual(len(db["daily_schedule"].rows), 1)
        self.assertEqual(db["devices"].rows[0]["patient_id"], db["patients"].rows[0]["patient_id"])
        self.assertEqual(db["daily_schedule"].rows[0]["device_id"], "DEV-QWERTY-01")

    def test_delete_patient_cascades_workflow_records(self):
        self.db["alerts"] = _FakeCollection([{"patient_id": "PAT-TEST-01", "device_id": "DEV-TEST-01"}])
        self.db["scan_baselines"] = _FakeCollection([{"patient_id": "PAT-TEST-01", "device_id": "DEV-TEST-01"}])
        self.db["inspection_sessions"] = _FakeCollection([{"patient_id": "PAT-TEST-01", "device_id": "DEV-TEST-01"}])
        self.db["clinical_decisions"] = _FakeCollection([{"patient_id": "PAT-TEST-01"}])
        main = self._main_module()

        with patch.object(main, "_db", return_value=self.db):
            response = main.delete_patient("PAT-TEST-01")

        self.assertEqual(response["message"], "Patient and linked workflow records deleted")
        for name in ["patients", "devices", "prescriptions", "daily_schedule", "alerts", "scan_baselines", "inspection_sessions", "clinical_decisions"]:
            self.assertEqual(self.db[name].rows, [], name)

    def test_missed_schedule_without_baseline_does_not_start_scan(self):
        self.db["daily_schedule"].rows[0]["status"] = "MISSED"
        controller = self._controller()

        result = controller.inspect_device_session(
            "DEV-TEST-01",
            raw_inspection=_inspection(10, 9),
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status_code, 409)
        self.assertIn("No active image-scan schedule", result.error_message)


if __name__ == "__main__":
    unittest.main()
