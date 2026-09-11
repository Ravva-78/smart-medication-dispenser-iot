/**
 * TabletScan.jsx — Full AI Blister Strip Scanner
 *
 * Complete end-to-end workflow:
 *  1. Select device (auto-loads patient + prescription + schedule from backend)
 *  2. Upload or capture image → POST /api/v1/devices/{id}/inspection
 *  3. AI pipeline (Models A→B→C) runs on backend → real tablet count
 *  4. Clinical engine evaluates vs prescription + schedule window
 *  5. Results written to MongoDB: inspection_sessions, compliance_decisions, alerts, daily_schedule
 *  6. Frontend shows live results and dispatches a global refresh so Alerts,
 *     Schedules, Audit Logs, Dispense Queue all update simultaneously
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { API_BASE } from "../../services/api";
const API_URL = API_BASE.replace("localhost", window.location.hostname);

/* ── Outcome meta ────────────────────────────────────────────────────── */
const OUTCOME_META = {
  CORRECT_DOSE:     { color: "#22c55e", bg: "rgba(34,197,94,.13)",   icon: "✅", label: "Correct Dose Taken" },
  PENDING:          { color: "#f59e0b", bg: "rgba(245,158,11,.13)",  icon: "⏳", label: "Baseline Recorded — No Change" },
  EXTRA_DOSE:       { color: "#ef4444", bg: "rgba(239,68,68,.13)",   icon: "⚠️", label: "Overdose — Extra Tablets Removed" },
  DOSE_MISSED:      { color: "#ef4444", bg: "rgba(239,68,68,.13)",   icon: "❌", label: "Dose Missed" },
  WRONG_MEDICINE:   { color: "#a855f7", bg: "rgba(168,85,247,.13)",  icon: "💊", label: "Wrong Medicine Detected" },
  EXPIRED_MEDICINE: { color: "#f97316", bg: "rgba(249,115,22,.13)",  icon: "🚫", label: "Expired Medicine" },
};

/* ── Stat chip ───────────────────────────────────────────────────────── */
function Chip({ label, value, accent }) {
  return (
    <div style={{
      background: "var(--surface-2,#1e2a3a)",
      border: `1px solid ${accent || "var(--border-dim,#2a3a4a)"}`,
      borderRadius: 10, padding: "12px 18px", minWidth: 110, textAlign: "center",
    }}>
      <div style={{ fontSize: 11, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 700, color: accent || "var(--text-primary,#e8f0fe)" }}>{value}</div>
    </div>
  );
}

/* ── Alert card ──────────────────────────────────────────────────────── */
function AlertCard({ alert }) {
  const sev = alert.severity || "INFO";
  const c   = { CRITICAL: "#ef4444", WARNING: "#f59e0b", INFO: "#22c55e" }[sev] || "#64748b";
  return (
    <div style={{ border: `1px solid ${c}44`, borderLeft: `3px solid ${c}`, borderRadius: 8, padding: "10px 14px", marginBottom: 8, background: `${c}10`, fontSize: 13 }}>
      <span style={{ color: c, fontWeight: 700 }}>[{sev}]</span>{" "}
      <span style={{ color: "var(--text-primary,#e8f0fe)" }}>{alert.title}</span>
      {alert.recipient && <div style={{ color: "var(--text-muted,#8899aa)", fontSize: 11, marginTop: 3 }}>→ {alert.recipient}</div>}
    </div>
  );
}

/* ── Scan history row ────────────────────────────────────────────────── */
function ScanRow({ scan, index }) {
  const m = OUTCOME_META[scan.outcome] || OUTCOME_META.PENDING;
  return (
    <tr style={{ borderBottom: "1px solid var(--border-dim,#2a3a4a)" }}>
      <td style={{ padding: "8px 12px", color: "var(--text-muted,#8899aa)", fontFamily: "monospace", fontSize: 12 }}>#{index + 1}</td>
      <td style={{ padding: "8px 12px", fontSize: 12 }}>{scan.timestamp}</td>
      <td style={{ padding: "8px 12px" }}><strong>{scan.present}</strong> / {scan.total}</td>
      <td style={{ padding: "8px 12px", color: "var(--text-muted,#8899aa)", fontSize: 12 }}>{scan.delta >= 0 ? `+${scan.delta}` : scan.delta}</td>
      <td style={{ padding: "8px 12px" }}>
        <span style={{ background: m.bg, color: m.color, border: `1px solid ${m.color}44`, borderRadius: 20, padding: "2px 10px", fontSize: 11, fontWeight: 700 }}>
          {m.icon} {m.label}
        </span>
      </td>
    </tr>
  );
}

/* ═══════════════════════════════════════════════════════════════════════ */
export default function TabletScan() {
  /* ── Core state ──────────────────────────────────────────────────── */
  const [devices,   setDevices]   = useState([]);
  const [devId,     setDevId]     = useState("");
  const [patient,   setPatient]   = useState(null);
  const [rx,        setRx]        = useState(null);        // prescription
  const [schedules, setSchedules] = useState([]);          // today's schedule

  const [mode,     setMode]     = useState("upload");      // "upload" | "camera"
  const [imgFile,  setImgFile]  = useState(null);
  const [preview,  setPreview]  = useState(null);
  const [stream,   setStream]   = useState(null);
  const [scanNo,   setScanNo]   = useState(0);

  const [scanning, setScanning] = useState(false);
  const [result,   setResult]   = useState(null);
  const [history,  setHistory]  = useState([]);
  const [error,    setError]    = useState(null);
  const [scheduleRequired, setScheduleRequired] = useState(false);

  const [esp32Ip, setEsp32Ip] = useState("10.196.64.228");
  const [esp32Status, setEsp32Status] = useState("Ready");
  const [isLivePreview, setIsLivePreview] = useState(true);
  const latestBlobRef = useRef(null);

  const videoRef  = useRef(null);
  const canvasRef = useRef(null);
  const linkedDevices = devices.filter(d => d.patientId);

  const loadSchedulesForPatient = useCallback(async (pid) => {
    if (!pid) return [];
    const [patientScheduleRes, allSchedulesRes] = await Promise.all([
      fetch(`${API_URL}/api/v1/patients/${pid}/schedule`).then(r => r.json()).catch(() => ({})),
      fetch(`${API_URL}/schedules`).then(r => r.json()).catch(() => []),
    ]);
    const patientRows = patientScheduleRes.data?.schedules || patientScheduleRes.schedules || [];
    const allRows = Array.isArray(allSchedulesRes) ? allSchedulesRes.filter(s => s.patientId === pid || s.patient_id === pid) : [];
    const byId = new Map();
    [...patientRows, ...allRows].forEach(s => {
      const id = s.schedule_id || s.id || `${pid}-${s.target_time || s.time || Math.random()}`;
      byId.set(id, {
        ...s,
        schedule_id: s.schedule_id || s.id,
        target_time: s.target_time || s.time || s.scheduled_time,
      });
    });
    return Array.from(byId.values());
  }, []);

  /* ── Load device list on mount ───────────────────────────────────── */
  useEffect(() => {
    fetch(`${API_URL}/devices`)
      .then(r => r.json()).then(d => setDevices(Array.isArray(d) ? d : []))
      .catch(() => {});
  }, []);

  /* ── When device selected → load patient + prescription + schedule ── */
  useEffect(() => {
    if (!devId) { setPatient(null); setRx(null); setSchedules([]); return; }
    const dev = devices.find(d => d.id === devId);
    const pid = dev?.patientId;
    if (!pid) return;

    // Reset session when device changes
    setResult(null); setHistory([]); setScanNo(0);
    setImgFile(null); setPreview(null); setError(null); setScheduleRequired(false);

    // Load patient
    fetch(`${API_URL}/api/v1/patients/${pid}`)
      .then(r => {
        if (!r.ok) throw new Error("Patient record no longer exists for this device.");
        return r.json();
      })
      .then(d => setPatient(d.data || d))
      .catch(err => {
        setPatient(null);
        setRx(null);
        setSchedules([]);
        setDevId("");
        setError(err.message);
      });

    // Load prescriptions
    fetch(`${API_URL}/api/v1/patients/${pid}/prescriptions`)
      .then(r => r.json())
      .then(d => {
        const rxList = d.data?.prescriptions || d.prescriptions || [];
        setRx(rxList[0] || null);
      }).catch(() => {});

    loadSchedulesForPatient(pid).then(setSchedules).catch(() => setSchedules([]));
  }, [devId, devices, loadSchedulesForPatient]);

  /* ── ESP32 Camera Polling Loop & Actions ──────────────────────────── */
  useEffect(() => {
    if (mode !== "camera" || !isLivePreview) return;

    let active = true;
    let timerId = null;

    const poll = async () => {
      try {
        const res = await fetch(`http://${esp32Ip}/capture`);
        if (!res.ok) throw new Error();
        const blob = await res.blob();
        if (active) {
          const url = URL.createObjectURL(blob);
          setPreview(prev => {
            if (prev && prev.startsWith("blob:")) {
              URL.revokeObjectURL(prev); // Revoke older object url to prevent memory leak
            }
            return url;
          });
          latestBlobRef.current = blob;
          setEsp32Status("Ready");
        }
      } catch (err) {
        if (active) {
          setEsp32Status("Camera unavailable");
        }
      } finally {
        if (active) {
          timerId = setTimeout(poll, 1200); // Trigger next frame in 1.2 seconds
        }
      }
    };

    poll();

    return () => {
      active = false;
      if (timerId) clearTimeout(timerId);
    };
  }, [mode, isLivePreview, esp32Ip]);

  const handleEsp32Action = async () => {
    if (isLivePreview) {
      // Freeze frame and set as final scan image
      if (latestBlobRef.current) {
        const file = new File([latestBlobRef.current], "esp_capture.jpg", { type: "image/jpeg" });
        setImgFile(file);
        setIsLivePreview(false);
        setEsp32Status("Capture successful");
      } else {
        // Fallback capture if loop has not run yet
        setEsp32Status("Capturing...");
        try {
          const res = await fetch(`http://${esp32Ip}/capture`);
          if (!res.ok) throw new Error();
          const blob = await res.blob();
          const file = new File([blob], "esp_capture.jpg", { type: "image/jpeg" });
          setImgFile(file);
          setPreview(URL.createObjectURL(blob));
          setIsLivePreview(false);
          setEsp32Status("Capture successful");
        } catch (err) {
          setEsp32Status("Camera unavailable");
          setError("ESP32 camera unavailable. Check that the camera is powered on and connected to the same Wi-Fi network.");
        }
      }
    } else {
      // Resume active polling feed
      setImgFile(null);
      setIsLivePreview(true);
      setEsp32Status("Ready");
    }
  };

  /* ── File upload ─────────────────────────────────────────────────── */
  const onFileChange = e => {
    const f = e.target.files[0]; if (!f) return;
    setImgFile(f); setPreview(URL.createObjectURL(f));
    setResult(null); setError(null); setScheduleRequired(false);
  };

  /* ── Run Scan ────────────────────────────────────────────────────── */
  const runScan = async () => {
    if (!devId)    { setError("Select a device first."); return; }
    
    // In camera mode, automatically use the latest live frame if user didn't freeze first
    let fileToScan = imgFile;
    if (!fileToScan && mode === "camera" && latestBlobRef.current) {
      fileToScan = new File([latestBlobRef.current], "esp_capture.jpg", { type: "image/jpeg" });
      setImgFile(fileToScan);
    }
    if (!fileToScan)  { setError("Upload or capture an image first."); return; }
    const dev = devices.find(d => d.id === devId);
    const pid = dev?.patientId;
    if (!pid) {
      setError("Selected device is not linked to a patient. Register or repair the patient-device link first.");
      return;
    }
    const freshSchedules = await loadSchedulesForPatient(pid);
    if (freshSchedules.length > 0) setSchedules(freshSchedules);
    const schedulePool = freshSchedules.length > 0 ? freshSchedules : schedules;
    const hasActionableSchedule = schedulePool.some(s =>
      ["PENDING", "MISSED"].includes(String(s.status || "").toUpperCase())
    );
    if (!hasActionableSchedule) {
      setScheduleRequired(true);
      setError("No active image-scan schedule found for this patient. Add a schedule 2-5 minutes in the future, then run Scan #1 before it is due.");
      return;
    }

    setScanning(true); setError(null); setResult(null); setScheduleRequired(false);

    try {
      const fd = new FormData();
      fd.append("file", fileToScan);


      const res = await fetch(
        `${API_URL}/api/v1/devices/${devId}/inspection`,
        { method: "POST", body: fd }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const message = err.detail || `Server error ${res.status}`;
        if (res.status === 409) setScheduleRequired(true);
        throw new Error(message);
      }

      const data = await res.json();
      const payload = data.data || data;

      const newScanNo = scanNo + 1;
      setScanNo(newScanNo);

      // Extract tablet counts from the new top-level tablet_counts field
      const counts   = payload.tablet_counts   || {};
      const comp     = payload.compliance_decision || payload.decision || {};
      const alerts   = payload.dispatched_alerts   || [];
      const ocrRes   = payload.ocr_result          || {};
      const schedInfo = payload.schedule            || {};

      const present = counts.present ?? 0;
      const total   = counts.total   ?? 10;
      const missing = counts.missing ?? 0;
      const delta   = counts.delta   ?? 0;

      const outcome = comp.outcome || "PENDING";

      const scanRecord = {
        scanNo: newScanNo,
        timestamp: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        present, total, missing, delta, outcome,
        reason:    comp.reason || "",
        alerts,
        ocrRes,
        schedInfo,
        sessionId: payload.session_id || "",
      };

      setResult(scanRecord);
      setHistory(prev => [...prev, scanRecord]);

      // ── Global refresh: tell other pages to reload data ──────────
      // Dispatch a custom browser event that App.jsx or pages can listen to
      window.dispatchEvent(new CustomEvent("medidispense:scan_complete", {
        detail: {
          deviceId:  devId,
          patientId: payload.patient?.patient_id,
          outcome,
          sessionId: payload.session_id,
        }
      }));

    } catch (e) {
      setError(e.message || "Scan failed.");
    } finally {
      setScanning(false);
    }
  };

  const resetSession = () => {
    setResult(null); setHistory([]); setScanNo(0);
    setImgFile(null); setPreview(null); setError(null); setScheduleRequired(false);
  };

  /* ── Current outcome display ─────────────────────────────────────── */
  const meta = result ? (OUTCOME_META[result.outcome] || OUTCOME_META.PENDING) : null;

  /* ── Next PENDING schedule entry ─────────────────────────────────── */
  const nextPending = schedules.find(s => s.status === "PENDING");

  /* ═══════════════════════════════════════════════════════════════════ */
  return (
    <main style={{ padding: "24px 28px", maxWidth: 1100, margin: "0 auto" }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary,#e8f0fe)", margin: 0 }}>
          💊 Blister Strip AI Scanner
        </h1>
        <p style={{ color: "var(--text-muted,#8899aa)", margin: "4px 0 0", fontSize: 13 }}>
          Image → AI Pipeline (Model A→B→C) → Tablet Count → Clinical Evaluation → MongoDB Update → Alerts
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, alignItems: "start" }}>

        {/* ─── LEFT: Controls ─────────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Device / Patient selector */}
          <div style={{ background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em", display: "block", marginBottom: 8 }}>
              Select Patient / Device
            </label>
            <select
              value={devId}
              onChange={e => setDevId(e.target.value)}
              style={{ width: "100%", background: "var(--surface-2,#1e2a3a)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 8, color: "var(--text-primary,#e8f0fe)", padding: "10px 12px", fontSize: 13, fontWeight: 500 }}
            >
              <option value="">-- Select Patient to Scan --</option>
              {linkedDevices.map(d => {
                const pName = d.patientName && d.patientName !== "Unassigned" ? d.patientName : (d.patientId || "Unassigned");
                const med = d.medication ? ` · ${d.medication}` : "";
                const loc = d.ward ? ` (${d.ward})` : "";
                return (
                  <option key={d.id} value={d.id}>
                    👤 {pName}{med} — {d.id}{loc}
                  </option>
                );
              })}
            </select>

            {/* Patient context card */}
            {patient && (
              <div style={{ marginTop: 12, padding: "12px 14px", background: "var(--surface-2,#1e2a3a)", borderRadius: 8, fontSize: 13 }}>
                <div style={{ fontWeight: 700, color: "#00d4ff", marginBottom: 6, fontSize: 15 }}>
                  👤 {patient.name}
                </div>
                <div style={{ color: "var(--text-muted,#8899aa)", marginBottom: 4 }}>
                  ID: {patient.patient_id} · Age: {patient.age} ({patient.gender})
                </div>
                {rx && (
                  <div style={{ color: "var(--text-primary,#e8f0fe)", marginBottom: 4 }}>
                    💊 Rx: <strong>{rx.medicine_name}</strong> {rx.strength} — {rx.dosage_form}
                  </div>
                )}
                {/* Schedule */}
                {schedules.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 10, color: "var(--text-muted,#8899aa)", fontWeight: 700, textTransform: "uppercase", marginBottom: 4 }}>Today's Schedule</div>
                    {schedules.map(s => (
                      <div key={s.schedule_id} style={{
                        display: "flex", justifyContent: "space-between", alignItems: "center",
                        padding: "4px 0", fontSize: 12, borderBottom: "1px solid var(--border-dim,#2a3a4a)",
                      }}>
                        <span style={{ color: "var(--text-primary,#e8f0fe)" }}>🕐 {s.target_time || "—"}</span>
                        <span style={{
                          color: s.status === "COMPLETED" ? "#22c55e" : s.status === "MISSED" ? "#ef4444" : "#f59e0b",
                          fontWeight: 700, fontSize: 11,
                        }}>{s.status}</span>
                      </div>
                    ))}
                  </div>
                )}
                {nextPending && (
                  <div style={{ marginTop: 8, padding: "6px 10px", background: "rgba(245,158,11,.1)", border: "1px solid #f59e0b44", borderRadius: 6, fontSize: 11, color: "#f59e0b" }}>
                    ⏰ Next due: <strong>{nextPending.target_time}</strong> IST — {nextPending.medicine_name} {nextPending.strength}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Input mode toggle */}
          <div style={{ background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 }}>
            <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
              {["upload", "camera"].map(m => (
                <button key={m} onClick={() => setMode(m)} style={{
                  flex: 1, padding: "8px 0", borderRadius: 8, border: "none", cursor: "pointer",
                  fontWeight: 600, fontSize: 13, transition: "all .2s",
                  background: mode === m ? "#0080ff" : "var(--surface-2,#1e2a3a)",
                  color: mode === m ? "#fff" : "var(--text-muted,#8899aa)",
                }}>
                  {m === "upload" ? "📂 Upload Image" : "📷 Live Camera"}
                </button>
              ))}
            </div>

            {/* Upload */}
            {mode === "upload" && (
              <label style={{
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                border: "2px dashed var(--border-dim,#2a3a4a)", borderRadius: 10, padding: 28, cursor: "pointer",
                background: "var(--surface-2,#1e2a3a)",
              }}
                onDragOver={e => e.preventDefault()}
                onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) { setImgFile(f); setPreview(URL.createObjectURL(f)); setScheduleRequired(false); } }}
              >
                <input type="file" accept="image/*" style={{ display: "none" }} onChange={onFileChange} />
                {preview
                  ? <img src={preview} alt="Preview" style={{ maxWidth: "100%", maxHeight: 200, borderRadius: 8, objectFit: "contain" }} />
                  : <>
                    <span style={{ fontSize: 36, marginBottom: 8 }}>🖼️</span>
                    <span style={{ color: "var(--text-muted,#8899aa)", fontSize: 13 }}>Click to upload or drag & drop</span>
                    <span style={{ color: "var(--text-muted,#8899aa)", fontSize: 11, marginTop: 4 }}>JPG · PNG · WEBP</span>
                  </>
                }
              </label>
            )}

            {/* ESP32 Camera Integration */}
            {mode === "camera" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <label style={{ fontSize: 12, color: "var(--text-muted,#8899aa)", fontWeight: 600 }}>ESP32 Camera IP Address:</label>
                  <input 
                    type="text" 
                    value={esp32Ip} 
                    onChange={e => setEsp32Ip(e.target.value)}
                    placeholder="e.g. 10.196.64.228"
                    style={{
                      padding: 8, borderRadius: 8, border: "1px solid var(--border-dim,#2a3a4a)",
                      background: "var(--surface-2,#1e2a3a)", color: "#fff", outline: "none", fontSize: 13
                    }}
                  />
                </div>
                
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: 12 }}>
                  <span style={{ color: "var(--text-muted,#8899aa)" }}>Status:</span>
                  <strong style={{ 
                    color: esp32Status === "Capture successful" ? "#10b981" : 
                           esp32Status === "Camera unavailable" ? "#ef4444" : 
                           isLivePreview ? "#00d4ff" : "var(--text-muted,#8899aa)"
                  }}>
                    {isLivePreview ? "🟢 Live Preview Active" : esp32Status}
                  </strong>
                </div>

                <button 
                  onClick={handleEsp32Action} 
                  style={{ 
                    padding: 10, borderRadius: 8, border: "none", 
                    background: isLivePreview ? "#0080ff" : "#f59e0b", 
                    color: "#fff", fontWeight: 700, cursor: "pointer" 
                  }}
                >
                  {isLivePreview ? "📸 Capture from ESP32" : "🔄 Resume Live Feed"}
                </button>

                {preview && (
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, color: "var(--text-muted,#8899aa)", marginBottom: 4, textAlign: "center" }}>Captured Frame Preview:</div>
                    <img src={preview} alt="Captured" style={{ width: "100%", borderRadius: 8, maxHeight: 180, objectFit: "contain", border: "1px solid var(--border-dim,#2a3a4a)" }} />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Scan button */}
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={runScan}
              disabled={scanning || !devId || !imgFile}
              style={{
                flex: 1, padding: "13px 0", borderRadius: 10, border: "none", fontWeight: 700, fontSize: 15,
                cursor: scanning ? "wait" : "pointer", transition: "all .2s",
                background: (scanning || !devId || !imgFile) ? "#2a3a4a" : "linear-gradient(135deg,#0080ff,#00d4ff)",
                color: "#fff",
              }}
            >
              {scanning ? "⏳ AI Pipeline Running…" : scanNo === 0 ? "🔍 Scan #1 — Establish Baseline" : `🔍 Run Scan #${scanNo + 1}`}
            </button>
            {history.length > 0 && (
              <button onClick={resetSession} style={{ padding: "13px 18px", borderRadius: 10, border: "1px solid var(--border-dim,#2a3a4a)", background: "transparent", color: "var(--text-muted,#8899aa)", cursor: "pointer", fontSize: 13 }}>
                ↺ Reset
              </button>
            )}
          </div>

          {/* Error */}
          {error && (
            <div style={{ padding: "12px 16px", background: "rgba(239,68,68,.12)", border: "1px solid #ef4444", borderRadius: 8, color: "#ef4444", fontSize: 13 }}>
              <div>⚠️ {error}</div>
              {scheduleRequired && (
                <button
                  type="button"
                  onClick={() => { window.location.href = "/schedules"; }}
                  style={{
                    marginTop: 10, padding: "8px 12px", borderRadius: 8, border: "1px solid #ef4444",
                    background: "rgba(239,68,68,.1)", color: "#ef4444", cursor: "pointer", fontWeight: 700,
                  }}
                >
                  Open Schedules
                </button>
              )}
            </div>
          )}
        </div>

        {/* ─── RIGHT: Results ──────────────────────────────────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Placeholder */}
          {!result && !scanning && (
            <div style={{ background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 40, textAlign: "center" }}>
              <div style={{ fontSize: 48, marginBottom: 12 }}>🔬</div>
              <div style={{ color: "var(--text-muted,#8899aa)", fontSize: 14 }}>Select a device, upload a blister strip image, then run a scan.</div>
              <div style={{ color: "var(--text-muted,#8899aa)", fontSize: 12, marginTop: 8 }}>Scan #1 → baseline. Scan #2 → compliance check vs prescription schedule.</div>
            </div>
          )}

          {/* Scanning animation */}
          {scanning && (
            <div style={{ background: "var(--surface-1,#162032)", border: "1px solid #0080ff44", borderRadius: 12, padding: 40, textAlign: "center" }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>⏳</div>
              <div style={{ color: "#00d4ff", fontSize: 15, fontWeight: 700 }}>AI Pipeline Running…</div>
              <div style={{ color: "var(--text-muted,#8899aa)", fontSize: 12, marginTop: 6 }}>
                Model A → Perspective → Model B → Model C → Inventory → Clinical → Alerts
              </div>
            </div>
          )}

          {/* Outcome banner */}
          {result && meta && (
            <div style={{ background: meta.bg, border: `1px solid ${meta.color}44`, borderRadius: 12, padding: "16px 20px" }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: meta.color, marginBottom: 6 }}>
                {meta.icon} {meta.label}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted,#8899aa)" }}>
                Scan #{result.scanNo} — {result.reason}
              </div>
              {result.schedInfo?.target_time && (
                <div style={{ fontSize: 12, color: "var(--text-muted,#8899aa)", marginTop: 4 }}>
                  Schedule: {result.schedInfo.target_time} IST — now marked <strong style={{ color: meta.color }}>{result.schedInfo.status}</strong>
                </div>
              )}
            </div>
          )}

          {/* Tablet counts */}
          {result && (
            <div style={{ background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 14 }}>
                Tablet Inventory (AI Result)
              </div>
              <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                <Chip label="Total Slots" value={result.total} />
                <Chip label="Present" value={result.present} accent="#22c55e" />
                <Chip label="Missing" value={result.missing} accent={result.missing > 0 ? "#ef4444" : "#22c55e"} />
                <Chip
                  label="Δ Change"
                  value={result.delta >= 0 ? `+${result.delta}` : `${result.delta}`}
                  accent={result.delta < 0 ? "#f59e0b" : "#64748b"}
                />
              </div>
            </div>
          )}

          {/* OCR result */}
          {result?.ocrRes && Object.keys(result.ocrRes).length > 0 && result.ocrRes.identity && (
            <div style={{ background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 10 }}>
                OCR Medicine Identity
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 13 }}>
                {[
                  ["Medicine", result.ocrRes.identity?.medicine_name],
                  ["Strength", result.ocrRes.identity?.strength],
                  ["Batch", result.ocrRes.identity?.batch_number],
                  ["Expiry", result.ocrRes.identity?.expiry_date],
                  ["Confidence", result.ocrRes.identity?.confidence != null ? `${Math.round(result.ocrRes.identity.confidence * 100)}%` : null],
                ].filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} style={{ background: "var(--surface-2,#1e2a3a)", borderRadius: 8, padding: "8px 12px" }}>
                    <div style={{ fontSize: 10, color: "var(--text-muted,#8899aa)", marginBottom: 2 }}>{k}</div>
                    <div style={{ color: "var(--text-primary,#e8f0fe)", fontWeight: 600 }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Alerts dispatched */}
          {result?.alerts?.length > 0 && (
            <div style={{ background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 10 }}>
                🚨 Alerts Dispatched to MongoDB
              </div>
              {result.alerts.map((a, i) => <AlertCard key={i} alert={a} />)}
              <div style={{ fontSize: 11, color: "var(--text-muted,#8899aa)", marginTop: 8 }}>
                ↳ Check the <strong>Alerts</strong> sidebar tab to see these in the dashboard
              </div>
            </div>
          )}

          {/* Session history */}
          {history.length > 0 && (
            <div style={{ background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 10 }}>
                📋 Session Scan History
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--border-dim,#2a3a4a)" }}>
                      {["#", "Time", "Present/Total", "Δ", "Clinical Decision"].map(h => (
                        <th key={h} style={{ padding: "6px 12px", textAlign: "left", color: "var(--text-muted,#8899aa)", fontSize: 10, fontWeight: 700, textTransform: "uppercase" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((s, i) => <ScanRow key={i} scan={s} index={i} />)}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* Workflow guide */}
      <div style={{ marginTop: 24, background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 12 }}>
          📖 Compliance Rules (Applied by Clinical Engine on Backend)
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 10, fontSize: 12 }}>
          {[
            ["⏳ Scan #1", "Baseline recorded. No clinical decision yet."],
            ["✅ Scan #2 — 1 removed", "CORRECT_DOSE → Schedule marked COMPLETED in DB."],
            ["❌ Scan #2 — 0 removed", "PENDING → If past grace window: DOSE_MISSED alert sent."],
            ["⚠️ Scan #2 — 2+ removed", "EXTRA_DOSE → Critical overdose alert sent to caregiver."],
            ["💊 Wrong medicine", "WRONG_MEDICINE → Buzzer + caregiver emergency alert."],
            ["🚫 Expired", "EXPIRED_MEDICINE → Alert + stop dispensing."],
          ].map(([t, d]) => (
            <div key={t} style={{ background: "var(--surface-2,#1e2a3a)", borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ fontWeight: 700, color: "var(--text-primary,#e8f0fe)", marginBottom: 4 }}>{t}</div>
              <div style={{ color: "var(--text-muted,#8899aa)" }}>{d}</div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
