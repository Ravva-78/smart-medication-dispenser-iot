/**
 * App.jsx — Sprint 4
 *
 * Sprint 4 changes:
 *  - Fetches medications alongside patients, devices, alerts
 *  - Fixes device status case bug: backend uses "Online" not "online"
 *  - 30-second live refresh interval for all dashboard data
 *  - Lifts alertCount to pass to Sidebar (eliminates duplicate /alerts fetch)
 *  - Passes live device/medication data to DeviceHealth / MedicationAlerts
 *  - Skeleton loaders for stat cards (CSS shimmer via .skel-card)
 *  - Error banner with Retry action on dashboard load failure
 *  - Proper Quick Stats section using real data
 *  - Recent Activity improved: empty state when no alerts
 */
import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import StatCard from "./components/StatCard";
import "./App.css";
import DispenseChart from "./components/DispenseChart";
import DeviceHealth from "./components/DeviceHealth";
import MedicationAlerts from "./components/MedicationAlerts";
import WardNurse from "./components/WardNurse";
import { Routes, Route } from "react-router-dom";
import { ModalShell, ModalHeader, ModalRow } from "./components/ModalShell";

import Patients from "./pages/Patients";
import Medications from "./pages/Medications";
import Devices from "./pages/Devices";
import Alerts from "./pages/Alerts";
import Prescriptions from "./pages/Prescriptions";
import Schedules from "./pages/Schedules";
import AuditLogs from "./pages/AuditLogs";
import VerificationQueue from "./pages/VerificationQueue";
import DispensingMonitor from "./pages/DispensingMonitor";
import Settings from "./pages/Settings";
import Reports from "./pages/Reports";
import TabletScan from "./pages/TabletIdentification/TabletScan";
import { useLocation } from "react-router-dom";
import { apiClient } from "./services/apiClient";
import Toast from "./components/Toast";
import { notifier } from "./services/NotificationService";

/* ─── SVG Icons ──────────────────────────────────────────────── */
const IconPatients = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconDevices = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="2" y="3" width="20" height="14" rx="2"/>
    <path d="M8 21h8M12 17v4"/>
    <circle cx="12" cy="10" r="2"/>
    <path d="M12 6v2M12 12v2M8 10h2M14 10h2"/>
  </svg>
);

const IconAlert = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
    <line x1="12" y1="9" x2="12" y2="13"/>
    <line x1="12" y1="17" x2="12.01" y2="17"/>
  </svg>
);

const IconMeds = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
    <path d="M12 5 9.04 7.96a2.17 2.17 0 0 0 0 3.08c.82.82 2.13.85 3 .07l2.07-1.9a2.82 2.82 0 0 1 3.79 0l2.96 2.66"/>
    <path d="m18 15-2-2m-3 3-2-2"/>
  </svg>
);

/* ─── Skeleton stat card — shown while dashboardReady is false ── */
function SkeletonCard({ index }) {
  return (
    <div className="skel-card" style={{ "--delay": `${index * 80}ms` }}>
      <div className="skel-card-tag skel-base" />
      <div className="skel-card-value skel-base" />
      <div className="skel-card-label skel-base" />
    </div>
  );
}

/* ─── ProfileModal ───────────────────────────────────────────── */
function ProfileModal({ onClose }) {
  const Row = ({ label, value }) => (
    <div style={{
      display: "flex", alignItems: "flex-start",
      padding: "12px 0", borderBottom: "1px solid var(--border-dim)", gap: 16,
    }}>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
        letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase",
        minWidth: 110, paddingTop: 2, flexShrink: 0,
      }}>{label}</span>
      <span style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-primary)", flex: 1 }}>
        {value}
      </span>
    </div>
  );

  return (
    <ModalShell onClose={onClose} maxWidth={440}>
      <ModalHeader title="Profile" sub="User details · MEDI-DISPENSE" onClose={onClose} />
      <Row label="Name"   value="Dr. System Admin" />
      <Row label="Role"   value="Ward Monitor"      />
      <Row label="Status" value="Online"            />
      <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{
          padding: "9px 28px", borderRadius: "var(--radius-sm)",
          border: "none", background: "var(--cyan)",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
          color: "#fff", cursor: "pointer",
          boxShadow: "0 2px 10px rgba(58,141,255,0.25)",
        }}>Close</button>
      </div>
    </ModalShell>
  );
}

/* ─── App ────────────────────────────────────────────────────── */
function App() {
  const location    = useLocation();
  const isDashboard = location.pathname === "/";

  const [time, setTime] = useState("");
  const [showProfileModal, setShowProfileModal] = useState(false);

  /* Live clock */
  useEffect(() => {
    const interval = setInterval(() => {
      setTime(new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  /* ── Dashboard data state ─────────────────────────────────── */
  const [stats, setStats] = useState({
    patients:    0,
    devices:     0,   /* online count */
    medications: 0,   /* total count  */
    activeAlerts: 0,  /* non-Resolved */
    lowStockMeds: 0,
    prescriptions: 0,
    verifications: 0,
    dispenseJobs: 0,
    audits: 0,
  });
  const [dashboardReady,  setDashboardReady]  = useState(false);
  const [dashboardError,  setDashboardError]  = useState(null);
  const [recentAlerts,    setRecentAlerts]    = useState([]);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const unsubscribe = notifier.subscribe((notification) => {
      setToast(notification);
    });
    return unsubscribe;
  }, []);

  /* Sprint 4 — lifted raw lists for right-panel components */
  const [deviceList,      setDeviceList]      = useState([]);
  const [medicationList,  setMedicationList]  = useState([]);

  /* Sprint 4 — alertCount for Sidebar badge (replaces Sidebar's own fetch) */
  const [alertCount, setAlertCount] = useState(null);

  /* ── loadDashboard — resilient fetch for all dashboard data ──── */
  const loadDashboard = useCallback(async () => {
    setDashboardError(null);
    try {
      const results = await Promise.allSettled([
        apiClient.get("/patients"),
        apiClient.get("/devices"),
        apiClient.get("/medications"),
        apiClient.get("/alerts"),
        apiClient.get("/prescriptions"),
        apiClient.get("/verifications"),
        apiClient.get("/dispense"),
        apiClient.get("/audits"),
      ]);

      const [patientsRes, devicesRes, medicationsRes, alertsRes, prescriptionsRes, verificationsRes, dispenseJobsRes, auditsRes] = results;

      const allRejected = results.every(r => r.status === "rejected");
      if (allRejected) {
        const firstErr = results[0]?.reason;
        throw new Error(firstErr?.message || "Could not connect to backend server");
      }

      const patientList    = patientsRes.status === "fulfilled" && Array.isArray(patientsRes.value) ? patientsRes.value : [];
      const devList        = devicesRes.status === "fulfilled" && Array.isArray(devicesRes.value) ? devicesRes.value : [];
      const medList        = medicationsRes.status === "fulfilled" && Array.isArray(medicationsRes.value) ? medicationsRes.value : [];
      const alertList      = alertsRes.status === "fulfilled" && Array.isArray(alertsRes.value) ? alertsRes.value : [];
      const rxList         = prescriptionsRes.status === "fulfilled" && Array.isArray(prescriptionsRes.value) ? prescriptionsRes.value : [];
      const vList          = verificationsRes.status === "fulfilled" && Array.isArray(verificationsRes.value) ? verificationsRes.value : [];
      const djList         = dispenseJobsRes.status === "fulfilled" && Array.isArray(dispenseJobsRes.value) ? dispenseJobsRes.value : [];
      const auList         = auditsRes.status === "fulfilled" && Array.isArray(auditsRes.value) ? auditsRes.value : [];

      /* Sprint 4 — fix: backend uses "Online" (capital O) */
      const onlineDevices  = devList.filter(d => d.status === "Online").length;
      const activeAlerts   = alertList.filter(a => a.status !== "Resolved").length;
      const lowStockMeds   = medList.filter(m => m.status === "Low Stock" || m.status === "Critical").length;

      setStats({
        patients:     patientList.length,
        devices:      onlineDevices,
        medications:  medList.length,
        activeAlerts,
        lowStockMeds,
        prescriptions: rxList.length,
        verifications: vList.filter(v => v.status === "Waiting").length,
        dispenseJobs: djList.filter(d => d.status === "Pending").length,
        audits: auList.length,
      });

      /* Raw lists for right-panel components */
      setDeviceList(devList);
      setMedicationList(medList);

      /* Recent Activity — 5 most recent alerts */
      setRecentAlerts(alertList.slice(0, 5));

      /* Sidebar badge — lifted here so no duplicate fetch */
      setAlertCount(activeAlerts);

    } catch (err) {
      setDashboardError(err.message || "Could not load dashboard data.");
    } finally {
      setDashboardReady(true);
    }
  }, []);

  /* Mount load */
  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  /* Sprint 4 — 30-second live refresh for the whole dashboard */
  useEffect(() => {
    if (!isDashboard) return; /* Only poll when dashboard is visible */
    const id = setInterval(loadDashboard, 30_000);
    return () => clearInterval(id);
  }, [isDashboard, loadDashboard]);

  /* ── Stat cards definition ────────────────────────────────── */
  const cards = [
    {
      label:  "Total Patients",
      value:  stats.patients,
      icon:   <IconPatients />,
      accent: "#00d4ff",
      glow:   "rgba(0,212,255,0.15)",
      tag:    "REGISTERED",
    },
    {
      label:  "Online Devices",
      value:  stats.devices,
      icon:   <IconDevices />,
      accent: "#00ff9d",
      glow:   "rgba(0,255,157,0.15)",
      tag:    "ONLINE",
    },
    {
      label:  "Total Medications",
      value:  stats.medications,
      icon:   <IconMeds />,
      accent: "#b06fff",
      glow:   "rgba(176,111,255,0.15)",
      tag:    stats.lowStockMeds > 0 ? `${stats.lowStockMeds} LOW` : "OK",
    },
    {
      label:  "Active Alerts",
      value:  stats.activeAlerts,
      icon:   <IconAlert />,
      accent: "#ff6b35",
      glow:   "rgba(255,107,53,0.15)",
      tag:    "CRITICAL",
    },
  ];

  /* ── Device counts for DeviceHealth panel ─────────────────── */
  const devOnline  = deviceList.filter(d => d.status === "Online").length;
  const devOffline = deviceList.filter(d => d.status === "Offline").length;
  const devLow     = deviceList.filter(d => d.status === "Battery Low").length;

  return (
    <div className="app-shell">
      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onDismiss={() => setToast(null)}
        />
      )}
      {showProfileModal && (
        <ProfileModal onClose={() => setShowProfileModal(false)} />
      )}

      {/* Sprint 4 — Sidebar now receives alertCount as a prop */}
      <Sidebar
        onProfileClick={() => setShowProfileModal(true)}
        alertCount={alertCount}
      />

      <Routes>
        <Route path="/"            element={null}          />
        <Route path="/patients"    element={<Patients />}    />
        <Route path="/medications" element={<Medications />} />
        <Route path="/devices"     element={<Devices />}     />
        <Route path="/alerts"      element={<Alerts />}      />
        <Route path="/prescriptions" element={<Prescriptions />} />
        <Route path="/schedules"   element={<Schedules />} />
        <Route path="/audits"      element={<AuditLogs />} />
        <Route path="/verifications" element={<VerificationQueue />} />
        <Route path="/dispense"    element={<DispensingMonitor />} />
        <Route path="/settings"    element={<Settings />} />
        <Route path="/reports"     element={<Reports />} />
        <Route path="/scan"        element={<TabletScan />} />
      </Routes>

      {isDashboard && (
      <main className="main-content">

        {/* Header */}
        <header className="dash-header">
          <div className="dash-header-left">
            <span className="breadcrumb">MEDI-DISPENSE</span>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-active">Dashboard</span>
          </div>
          <div className="dash-header-right">
            <div className="status-pill">
              <span className="pulse-dot" />
              {dashboardError ? "Offline" : "System Online"}
            </div>
            <div className="time-display">{time}</div>
          </div>
        </header>

        {/* Hero */}
        <section className="dash-hero">
          <div className="hero-line" />
          <div className="hero-text">
            <h1 className="hero-title">System Overview</h1>
            <p className="hero-sub">
              Real-time telemetry · Ward monitoring · Dispense analytics
            </p>
          </div>
          <div className="hero-badge">LIVE</div>
        </section>

        {/* Stat Cards — skeleton while loading, error banner on failure */}
        <section className="cards-grid">
          {!dashboardReady ? (
            /* Skeleton cards match the 4-column grid */
            [0, 1, 2, 3].map(i => <SkeletonCard key={i} index={i} />)
          ) : dashboardError ? (
            /* Error banner with Retry */
            <div className="dash-error">
              <span>⚠ {dashboardError}</span>
              <button className="dash-error-retry" onClick={loadDashboard}>
                Retry
              </button>
            </div>
          ) : (
            cards.map((card, i) => (
              <StatCard key={card.label} {...card} index={i} />
            ))
          )}
        </section>

        <DispenseChart />

        {/* Bottom row */}
        <div className="bottom-row">

          {/* Recent Activity — Sprint 4: improved empty state */}
          <section className="activity-strip">
            <div className="strip-header">
              <span className="strip-title">Recent Activity</span>
              <span className="strip-dot" />
              <span className="strip-live">Live Feed</span>
            </div>

            <div className="activity-rows">
              {recentAlerts.length > 0
                ? recentAlerts.map((a, i) => {
                    const rowType =
                      a.status === "Critical" ? "warn"
                      : a.status === "Warning" ? "warn"
                      : a.type   === "Medication" ? "ok"
                      : "info";
                    const badge =
                      a.status === "Resolved" ? "OK"
                      : a.status === "Critical" ? "CRIT"
                      : a.status === "Warning"  ? "WARN"
                      : "INFO";
                    return (
                      <div className="activity-row" key={a.id} style={{ "--row-i": i }}>
                        <span className={`row-indicator row-${rowType}`} />
                        <span className="row-time">{a.time}</span>
                        <span className="row-msg">{a.device} — {a.desc}</span>
                        <span className={`row-badge badge-${rowType}`}>{badge}</span>
                      </div>
                    );
                  })
                : /* Empty / loading state */
                  !dashboardReady
                  ? /* Still loading — show 5 skeleton rows */
                    [0, 1, 2, 3, 4].map(i => (
                      <div className="activity-row" key={i} style={{ "--row-i": i }}>
                        <span className="row-indicator" style={{ background: "var(--border-soft)" }} />
                        <span className="skel-line" style={{ width: 35, height: 10 }} />
                        <span className="skel-line" style={{ flex: 1, height: 10 }} />
                        <span className="skel-line" style={{ width: 36, height: 18, borderRadius: 6 }} />
                      </div>
                    ))
                  : /* Loaded but no alerts */
                    (
                      <div style={{
                        padding: "28px 0", textAlign: "center",
                        fontFamily: "var(--font-body)", fontSize: 13,
                        color: "var(--text-muted)",
                      }}>
                        No recent activity to display.
                      </div>
                    )
              }
            </div>
          </section>

          {/* Quick Stats — Sprint 4: real data */}
          <div className="quick-stats">
            <div className="qs-header">System Stats</div>

            <div className="qs-row">
              <span className="qs-label">Patients</span>
              <span className="qs-value">
                {dashboardReady ? stats.patients : "—"}
              </span>
            </div>

            <div className="qs-row">
              <span className="qs-label">Devices Online</span>
              <span className="qs-value">
                {dashboardReady ? stats.devices : "—"}
              </span>
            </div>

            <div className="qs-row">
              <span className="qs-label">Medications</span>
              <span className="qs-value">
                {dashboardReady ? stats.medications : "—"}
              </span>
            </div>

            <div className="qs-row">
              <span className="qs-label">Low Stock</span>
              <span className="qs-value" style={{
                color: dashboardReady && stats.lowStockMeds > 0 ? "var(--orange)" : undefined,
              }}>
                {dashboardReady ? stats.lowStockMeds : "—"}
              </span>
            </div>

            <div className="qs-row">
              <span className="qs-label">Active Alerts</span>
              <span className="qs-value" style={{
                color: dashboardReady && stats.activeAlerts > 0 ? "#E74C3C" : undefined,
              }}>
                {dashboardReady ? stats.activeAlerts : "—"}
              </span>
            </div>

            <div className="qs-row">
              <span className="qs-label">Prescriptions</span>
              <span className="qs-value">{dashboardReady ? stats.prescriptions : "—"}</span>
            </div>

            <div className="qs-row">
              <span className="qs-label">Pending Verifications</span>
              <span className="qs-value" style={{ color: dashboardReady && stats.verifications > 0 ? "var(--orange)" : undefined }}>
                {dashboardReady ? stats.verifications : "—"}
              </span>
            </div>

            <div className="qs-row">
              <span className="qs-label">Pending Dispenses</span>
              <span className="qs-value" style={{ color: dashboardReady && stats.dispenseJobs > 0 ? "var(--orange)" : undefined }}>
                {dashboardReady ? stats.dispenseJobs : "—"}
              </span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <footer className="dash-footer">
          <span>MEDI-DISPENSE v1.1</span>
          <span className="footer-sep">·</span>
          <span>AI-Powered Medication Monitoring</span>
          <span className="footer-sep">·</span>
          <span>© 2026</span>
        </footer>

      </main>
      )}

      {/* RIGHT PANEL — Sprint 4: live data injected */}
      {isDashboard && (
      <aside className="right-panel">
        <DeviceHealth
          online={devOnline}
          offline={devOffline}
          low={devLow}
          loading={!dashboardReady}
        />
        <MedicationAlerts
          medications={medicationList}
          loading={!dashboardReady}
        />
        <WardNurse />
      </aside>
      )}

    </div>
  );
}

export default App;
