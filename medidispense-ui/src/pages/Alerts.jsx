/**
 * Alerts.jsx — Sprint 2
 *
 * Full backend integration:
 *   GET    /alerts          — initial load + refresh
 *   PATCH  /alerts/:id/resolve — resolve action
 *   DELETE /alerts/:id     — ignore/delete action
 *
 * UX:
 *   - Loading state  (CSS spinner from Sprint 1)
 *   - Error state    (network / server errors)
 *   - ConfirmDialog  before Resolve and before Delete
 *   - Refresh list   after every successful mutation
 *   - ViewAlertModal on ModalShell (Escape key via S6)
 */
import { useState, useEffect, useCallback } from "react";
import { apiClient }      from "../services/apiClient";
import ActionBtn         from "../components/ActionBtn";    /* S3 */
import { ModalShell }    from "../components/ModalShell";   /* S5 + S6 */
import ConfirmDialog     from "../components/ConfirmDialog"; /* Sprint 2 */
import SortableHeader from "../components/SortableHeader";
import FilterPills from "../components/FilterPills";
import { useTableControls } from "../hooks/useTableControls";

/* ─── Status colour map ────────────────────────────────────────── */
const STATUS_MAP = {
  Active:   { color: "var(--cyan)",   bg: "rgba(58,141,255,0.08)",  border: "rgba(58,141,255,0.20)"  },
  Warning:  { color: "var(--orange)", bg: "rgba(230,126,34,0.08)",  border: "rgba(230,126,34,0.20)"  },
  Critical: { color: "#E74C3C",       bg: "rgba(231,76,60,0.07)",   border: "rgba(231,76,60,0.18)"   },
  Resolved: { color: "var(--green)",  bg: "rgba(39,174,96,0.08)",   border: "rgba(39,174,96,0.20)"   },
};

/* ─── Type colour map ──────────────────────────────────────────── */
const TYPE_MAP = {
  Medication: { color: "var(--violet)", bg: "rgba(142,140,255,0.08)", border: "rgba(142,140,255,0.20)" },
  Device:     { color: "var(--teal)",   bg: "rgba(74,163,162,0.08)",  border: "rgba(74,163,162,0.20)"  },
};

/* ─── Alert type icon ──────────────────────────────────────────── */
function TypeIcon({ type }) {
  if (type === "Medication") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
        width="13" height="13" style={{ flexShrink: 0 }}>
        <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2v-4M9 21H5a2 2 0 0 1-2-2v-4m0 0h18" />
        <circle cx="12" cy="12" r="2" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6"
      width="13" height="13" style={{ flexShrink: 0 }}>
      <rect x="2" y="3" width="20" height="14" rx="2" />
      <path d="M8 21h8M12 17v4" />
      <circle cx="12" cy="10" r="2" />
    </svg>
  );
}

/* ─── View Alert Modal ───────────────────────────────────────────
   S5 — ModalShell handles backdrop + Escape (S6)                 */
function ViewAlertModal({ alert, onClose }) {
  if (!alert) return null;

  const Row = ({ label, value }) => (
    <div style={{
      display: "flex", alignItems: "flex-start",
      padding: "12px 0", borderBottom: "1px solid var(--border-dim)",
      gap: 16,
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

  const st = STATUS_MAP[alert.status] || STATUS_MAP.Active;
  const tp = TYPE_MAP[alert.type]     || TYPE_MAP.Device;

  return (
    <ModalShell onClose={onClose} maxWidth={440}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <div style={{
            fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 800,
            color: "var(--text-primary)", letterSpacing: "-0.02em",
          }}>Alert Details</div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>
            Read-only record · MEDI-DISPENSE
          </div>
        </div>
        <button onClick={onClose} style={{
          background: "var(--bg-overlay)", border: "1px solid var(--border-soft)",
          borderRadius: "var(--radius-sm)", width: 32, height: 32, cursor: "pointer",
          color: "var(--text-muted)", display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: 14, fontWeight: 600, flexShrink: 0,
        }}>×</button>
      </div>

      <div style={{ height: 1, background: "var(--border-dim)", marginBottom: 4 }} />

      <Row label="Alert ID"   value={alert.id} />
      <Row label="Type"       value={(
        <span style={{
          display: "inline-flex", alignItems: "center", gap: 5,
          color: tp.color,
        }}>
          <TypeIcon type={alert.type} /> {alert.type}
        </span>
      )} />
      <Row label="Message"    value={alert.desc} />
      <Row label="Patient"    value={alert.patient} />
      <Row label="Device"     value={alert.device} />
      <Row label="Ward"       value={alert.ward} />
      <Row label="Timestamp"  value={alert.time} />
      <Row label="Status"     value={(
        <span className="page-status-chip" style={{
          color: st.color, background: st.bg, border: `1px solid ${st.border}`,
        }}>
          {alert.status}
        </span>
      )} />

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

/* ─── Page ─────────────────────────────────────────────────────── */
export default function Alerts() {
  const [alerts,       setAlerts]       = useState([]);
  const [loading,      setLoading]      = useState(true);
  const [fetchError,   setFetchError]   = useState(null);
  const [actionError,  setActionError]  = useState(null);

  /* Selected alert for view modal */
  const [selectedAlert,  setSelectedAlert]  = useState(null);

  /* Pending confirmation — { type: "resolve" | "delete", alert } */
  const [pending, setPending] = useState(null);

  /* ── Fetch alerts from backend ──────────────────────────────── */
  const loadAlerts = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const data = await apiClient.get('/alerts');
      setAlerts(Array.isArray(data) ? data : []);
    } catch (err) {
      setFetchError(err.message || "Could not load alerts.");
      setAlerts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAlerts(); }, [loadAlerts]);

  /* ── Derived counts ─────────────────────────────────────────── */
  const active     = alerts.filter(a => a.status !== "Resolved").length;
  const critical   = alerts.filter(a => a.status === "Critical").length;
  const deviceAlts = alerts.filter(a => a.type === "Device"     && a.status !== "Resolved").length;
  const medAlts    = alerts.filter(a => a.type === "Medication"  && a.status !== "Resolved").length;

  const countActive   = alerts.filter(a => a.status === "Active").length;
  const countWarning  = alerts.filter(a => a.status === "Warning").length;
  const countCritical = alerts.filter(a => a.status === "Critical").length;
  const countResolved = alerts.filter(a => a.status === "Resolved").length;

  const {
    search, setSearch,
    activeFilter, setFilter,
    sort, toggleSort,
    filtered
  } = useTableControls(alerts, {
    searchFields: ["patient", "device", "type", "desc", "ward"],
    filterField: "status",
    sortDefault: { field: "time", dir: "desc" },
    storageKey: "alerts"
  });

  /* ── Confirm helpers ────────────────────────────────────────── */
  const askResolve = (alert) => setPending({ type: "resolve", alert });
  const askDelete  = (alert) => setPending({ type: "delete",  alert });
  const cancelPending = () => setPending(null);

  const commitAction = async () => {
    if (!pending) return;
    const { type, alert } = pending;
    setPending(null);
    setActionError(null);

    try {
      if (type === "resolve") {
        await apiClient.patch(`/alerts/${alert.id}/resolve`, {});
      } else {
        await apiClient.delete(`/alerts/${alert.id}`);
      }
      await loadAlerts(); // refresh
    } catch (err) {
      setActionError(err.message || "Action failed. Please try again.");
    }
  };

  /* ── Render ─────────────────────────────────────────────────── */
  return (
    <>
      {/* ConfirmDialog — Resolve */}
      {pending?.type === "resolve" && (
        <ConfirmDialog
          title="Resolve Alert"
          message={`Mark "${pending.alert.desc}" as Resolved? This cannot be undone.`}
          confirmLabel="Resolve"
          confirmVariant="primary"
          onConfirm={commitAction}
          onCancel={cancelPending}
        />
      )}

      {/* ConfirmDialog — Delete */}
      {pending?.type === "delete" && (
        <ConfirmDialog
          title="Delete Alert"
          message={`Permanently remove "${pending.alert.desc}"? This cannot be undone.`}
          confirmLabel="Delete"
          confirmVariant="danger"
          onConfirm={commitAction}
          onCancel={cancelPending}
        />
      )}

      {/* ViewAlertModal */}
      {selectedAlert && (
        <ViewAlertModal
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
        />
      )}

      <main className="main-content page-main">

        {/* ── Header ────────────────────────────────────────────── */}
        <header className="dash-header">
          <div className="dash-header-left">
            <span className="breadcrumb">MEDI-DISPENSE</span>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-active">Alerts</span>
          </div>
          <div className="dash-header-right">
            <div className="status-pill" style={{
              color:      critical > 0 ? "#E74C3C" : "var(--green)",
              background: critical > 0 ? "rgba(231,76,60,0.08)" : "rgba(39,174,96,0.08)",
              border:     `1px solid ${critical > 0 ? "rgba(231,76,60,0.20)" : "rgba(39,174,96,0.20)"}`,
            }}>
              <span className="pulse-dot" style={{ background: critical > 0 ? "#E74C3C" : "var(--green)" }} />
              {critical > 0 ? `${critical} Critical` : "All Clear"}
            </div>
            <button className="page-add-btn">+ Create Alert</button>
          </div>
        </header>

        {/* ── Hero ──────────────────────────────────────────────── */}
        <section className="dash-hero">
          <div className="hero-line" style={{
            background: `linear-gradient(to bottom, ${critical > 0 ? "#E74C3C" : "var(--cyan)"}, transparent)`,
          }} />
          <div className="hero-text">
            <h1 className="hero-title">System Alerts</h1>
            <p className="hero-sub">
              Medication warnings · Device issues · Patient safety monitoring
            </p>
          </div>
          <div className="hero-badge" style={critical > 0 ? {
            color: "#E74C3C", background: "rgba(231,76,60,0.08)",
            border: "1px solid rgba(231,76,60,0.20)",
          } : {}}>
            {loading ? "…" : active > 0 ? `${active} ACTIVE` : "ALL CLEAR"}
          </div>
        </section>

        {/* ── Summary chips ─────────────────────────────────────── */}
        <div className="page-summary-row">
          <div className="page-summary-chip page-summary-chip--blue">
            <span className="page-summary-val">{active}</span>
            <span className="page-summary-lbl">ACTIVE</span>
          </div>
          <div className="page-summary-chip" style={{ borderColor: "rgba(231,76,60,0.20)" }}>
            <span className="page-summary-val" style={{ color: "#E74C3C" }}>{critical}</span>
            <span className="page-summary-lbl">CRITICAL</span>
          </div>
          <div className="page-summary-chip" style={{ borderColor: "rgba(74,163,162,0.20)" }}>
            <span className="page-summary-val" style={{ color: "var(--teal)" }}>{deviceAlts}</span>
            <span className="page-summary-lbl">DEVICE</span>
          </div>
          <div className="page-summary-chip" style={{ borderColor: "rgba(142,140,255,0.20)" }}>
            <span className="page-summary-val" style={{ color: "var(--violet)" }}>{medAlts}</span>
            <span className="page-summary-lbl">MEDICATION</span>
          </div>
        </div>

        {/* ── Action error banner ────────────────────────────────── */}
        {actionError && (
          <div style={{
            margin: "0 0 12px", padding: "10px 16px",
            borderRadius: "var(--radius-sm)",
            background: "rgba(231,76,60,0.08)", border: "1px solid rgba(231,76,60,0.20)",
            fontFamily: "var(--font-body)", fontSize: 13, color: "#E74C3C",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <span>{actionError}</span>
            <button
              onClick={() => setActionError(null)}
              style={{
                background: "none", border: "none", cursor: "pointer",
                color: "#E74C3C", fontSize: 16, lineHeight: 1, padding: "0 4px",
              }}
            >×</button>
          </div>
        )}

        {/* ── Filters & Search ──────────────────────────────────── */}
        <div style={{ marginBottom: 16 }}>
          <FilterPills
            options={["Active", "Warning", "Critical", "Resolved"]}
            active={activeFilter}
            onChange={setFilter}
            counts={{ "Active": countActive, "Warning": countWarning, "Critical": countCritical, "Resolved": countResolved }}
          />
        </div>

        {/* ── Search ────────────────────────────────────────────── */}
        <div className="page-search-bar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" width="16" height="16">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            className="page-search-input"
            type="text"
            placeholder="Search alerts by patient, device or alert type…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button className="page-search-clear" onClick={() => setSearch("")}>✕</button>
          )}
        </div>

        {/* ── Table card ────────────────────────────────────────── */}
        <div className="page-table-card">
          <table className="page-table">
            <thead>
              <tr>
                <SortableHeader field="id" label="Alert ID" sort={sort} onSort={toggleSort} />
                <SortableHeader field="type" label="Type" sort={sort} onSort={toggleSort} />
                <SortableHeader field="patient" label="Patient" sort={sort} onSort={toggleSort} />
                <SortableHeader field="device" label="Device" sort={sort} onSort={toggleSort} />
                <SortableHeader field="ward" label="Ward" sort={sort} onSort={toggleSort} />
                <SortableHeader field="desc" label="Description" sort={sort} onSort={toggleSort} />
                <SortableHeader field="time" label="Time" sort={sort} onSort={toggleSort} />
                <SortableHeader field="status" label="Status" sort={sort} onSort={toggleSort} />
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {/* Loading state — S10 CSS spinner */}
              {loading && (
                <tr>
                  <td colSpan="9" className="page-table-loading">
                    <span className="spinner" />{" "}Loading alerts…
                  </td>
                </tr>
              )}

              {/* Error state */}
              {!loading && fetchError && (
                <tr>
                  <td colSpan="9" className="page-table-empty" style={{ color: "#E74C3C" }}>
                    {fetchError}{" "}
                    <button
                      onClick={loadAlerts}
                      style={{
                        background: "none", border: "none", cursor: "pointer",
                        color: "var(--cyan)", fontSize: 13, fontFamily: "var(--font-body)",
                        textDecoration: "underline", padding: 0,
                      }}
                    >
                      Retry
                    </button>
                  </td>
                </tr>
              )}

              {/* Empty state (no data, no error) */}
              {!loading && !fetchError && alerts.length === 0 && (
                <tr>
                  <td colSpan="9" className="page-table-empty">
                    No alerts in the system.
                  </td>
                </tr>
              )}

              {/* No search results */}
              {!loading && !fetchError && alerts.length > 0 && filtered.length === 0 && (
                <tr>
                  <td colSpan="9" className="page-table-empty">
                    No alerts match your search.
                  </td>
                </tr>
              )}

              {/* Data rows */}
              {!loading && !fetchError && filtered.map(a => {
                const st         = STATUS_MAP[a.status] || STATUS_MAP.Active;
                const tp         = TYPE_MAP[a.type]     || TYPE_MAP.Device;
                const isResolved = a.status === "Resolved";
                return (
                  <tr key={a.id} className="page-table-row" style={{ opacity: isResolved ? 0.55 : 1 }}>
                    <td className="page-table-id">{a.id}</td>
                    <td>
                      <span className="page-status-chip" style={{
                        color: tp.color, background: tp.bg, border: `1px solid ${tp.border}`,
                        display: "inline-flex", alignItems: "center", gap: 5,
                      }}>
                        <TypeIcon type={a.type} />
                        {a.type}
                      </span>
                    </td>
                    <td className="page-table-name"
                      style={{ color: a.patient === "—" ? "var(--text-muted)" : undefined }}>
                      {a.patient}
                    </td>
                    <td className="page-table-id">{a.device}</td>
                    <td><span className="page-ward-chip">{a.ward}</span></td>
                    <td className="page-table-mono" style={{
                      fontSize: 12, color: "var(--text-secondary)",
                      maxWidth: 220, whiteSpace: "nowrap",
                      overflow: "hidden", textOverflow: "ellipsis",
                    }}>
                      {a.desc}
                    </td>
                    <td className="page-table-mono">{a.time}</td>
                    <td>
                      <span className="page-status-chip" style={{
                        color: st.color, background: st.bg, border: `1px solid ${st.border}`,
                      }}>
                        {a.status}
                      </span>
                    </td>
                    {/* S3 — shared ActionBtn */}
                    <td>
                      <div className="page-action-group">
                        <ActionBtn label="View"   variant="view"    onClick={() => setSelectedAlert(a)} aria-label={`View alert ${a.id}`} />
                        {!isResolved && (
                          <ActionBtn label="Resolve" variant="resolve" onClick={() => askResolve(a)} aria-label={`Resolve alert ${a.id}`} />
                        )}
                        <ActionBtn label="Delete" variant="delete"   onClick={() => askDelete(a)} aria-label={`Delete alert ${a.id}`} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* ── Footer — S7 ───────────────────────────────────────── */}
        <footer className="dash-footer">
          <span>MEDI-DISPENSE v1.1</span>
          <span className="footer-sep">·</span>
          <span>AI-Powered Medication Monitoring</span>
          <span className="footer-sep">·</span>
          <span>© 2026</span>
        </footer>

      </main>
    </>
  );
}
