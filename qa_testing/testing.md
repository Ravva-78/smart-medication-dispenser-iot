# Quality Assurance (QA) Testing & Demo Checklist

This document is designed to guide the manual QA process and serve as a script/checklist for the final project demo video.

## 1. MongoDB Administrator Knowledge Checks
*Before testing, ensure you can instantly answer these questions by querying MongoDB:*
- [ ] **`patients`**: Who is the patient (e.g., Ravi Kumar)? Age? Caregiver info? Assigned device?
- [ ] **`devices`**: Which ESP32 belongs to PAT-001? Which camera? Device status?
- [ ] **`prescriptions`**: What medicines are assigned? Strength? Frequency? Start/End dates?
- [ ] **`daily_schedule`**: What are the exact schedule times (e.g., 08:00, 14:00, 21:00)?
- [ ] **`inspection_sessions`**: Can you trace an inspection's timestamp, image, latency, and final status?
- [ ] **`inventory_events`**: Can you verify if a tablet was removed, added, or unchanged?
- [ ] **`clinical_decisions`**: Can you see `CORRECT_DOSE`, `WRONG_MEDICINE`, `EXPIRED`, `MISSED_DOSE`?
- [ ] **`alerts`**: Are SMS, LOG, BUZZER, or CAREGIVER alerts triggering correctly?

---

## 2. Feature Manual Testing (Clinical Scenarios)

### Scenario 1: Correct Medicine
- [ ] **Action**: Upload image of prescribed medicine (e.g., Paracetamol).
- [ ] **Expected Flow**: OCR -> Paracetamol -> Inventory -> 1 tablet removed -> `CORRECT_DOSE` -> INFO alert.

### Scenario 2: Wrong Medicine
- [ ] **Action**: Upload image of an unprescribed medicine (e.g., Ibuprofen).
- [ ] **Expected Flow**: `WRONG_MEDICINE` -> Critical alert -> MongoDB alert created.

### Scenario 3: Expired Medicine
- [ ] **Action**: Upload image of a medicine with an expiry date in the past (e.g., 2022).
- [ ] **Expected Flow**: `EXPIRED_MEDICINE`.

### Scenario 4: No Tablet Removed
- [ ] **Action**: Upload an image with the exact same inventory state as the previous inspection.
- [ ] **Expected Flow**: `PENDING` (no inventory change detected).

### Scenario 5: Extra Dose
- [ ] **Action**: Upload an image showing 2 missing tablets simultaneously.
- [ ] **Expected Flow**: `EXTRA_DOSE`.

### Scenario 6: Wrong Time
- [ ] **Action**: Remove a tablet outside of the scheduled window.
- [ ] **Expected Flow**: `LATE_DOSE` or `EARLY_DOSE` (depending on current time vs. schedule).

### Scenario 7: Unknown Medicine (OCR Failure)
- [ ] **Action**: Provide an image with unreadable/scrambled text (e.g., "ABCXYZ").
- [ ] **Expected Flow**: `UNKNOWN` -> Triggers Wrong Medicine flow.

### Scenario 8: Wrong Patient
- [ ] **Action**: Use device `DEV-001` (PAT-001) but upload medicine prescribed only for `PAT-002`.
- [ ] **Expected Flow**: `WRONG_MEDICINE`.

---

## 3. Timing & Edge Cases Walkthrough
*(Assuming `daily_schedule` = 08:00 for Paracetamol)*
- [ ] **Current Time 08:05**: Validate clinical engine outputs `ON_TIME`.
- [ ] **Current Time 07:30**: Validate clinical engine outputs `EARLY_DOSE`.
- [ ] **Current Time 09:15**: Validate clinical engine outputs `LATE_DOSE`.
- [ ] **Current Time 13:00** (with no morning tablet taken): Validate clinical engine outputs `MISSED_DOSE`.

---

## 4. Patient Onboarding Flow
*Verify understanding of the end-to-end data creation pipeline (future Admin Dashboard logic):*
- [ ] Insert document into `patients` collection.
- [ ] Assign device mapping in `devices` collection.
- [ ] Add medicine to `prescriptions` collection.
- [ ] Generate schedule in `daily_schedule` collection.

---

## 5. Demo Video Script (5–6 Minutes)
*Do not start recording until every scenario above has been manually tested and verified.*

- [ ] **Part 1 (0:30) - Problem Statement**: Explain the problem of medication non-adherence.
- [ ] **Part 2 (0:45) - Architecture**: Briefly show the pipeline flow: `Camera -> Vision -> Inventory -> OCR -> Clinical -> MongoDB`.
- [ ] **Part 3 - MongoDB Tour**: Show the raw database collections (`patients`, `devices`, `prescriptions`, `alerts`) and explain each in one sentence.
- [ ] **Part 4 - Live Demo (Success)**: Open the Caregiver Dashboard. Use the webcam/upload to show Paracetamol detection. Show Correct Dose and the corresponding MongoDB update.
- [ ] **Part 5 - Live Demo (Failure)**: Use the webcam/upload to show Ibuprofen. Show Wrong Medicine, Critical Alert generation, and the corresponding MongoDB update.
- [ ] **Part 6 - Developer Dashboard**: Open the System Inspector. Show the processing latency, intermediate images (Perspective Warp, YOLO crops), raw JSON output, and session audit logs.
- [ ] **Part 7 - Analytics Dashboard**: Open the Hospital Analytics Dashboard. Show today's inspections, alert aggregates, and patient compliance rates. Finish the presentation.
