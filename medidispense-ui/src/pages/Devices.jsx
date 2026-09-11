import { useState, useEffect } from "react";
import { apiClient } from "../services/apiClient";
import SortableHeader from "../components/SortableHeader";
import FilterPills from "../components/FilterPills";
import { useTableControls } from "../hooks/useTableControls";
/* ─── Status colour map ────────────────────────────────────────── */
const STATUS_MAP = {
  "Online":       { color: "var(--green)",  bg: "rgba(39,174,96,0.08)",   border: "rgba(39,174,96,0.20)"   },
  "Offline":      { color: "#E74C3C",       bg: "rgba(231,76,60,0.07)",   border: "rgba(231,76,60,0.18)"   },
  "Battery Low":  { color: "var(--orange)", bg: "rgba(230,126,34,0.08)",  border: "rgba(230,126,34,0.20)"  },
  "Restarting":   { color: "var(--violet)", bg: "rgba(142,140,255,0.08)", border: "rgba(142,140,255,0.20)" },
};

/* ─── Shared modal backdrop + panel ───────────────────────────── */
/* S6 — Escape key support added to local Modal */
function Modal({ onClose, children, maxWidth = 460 }) {
  /* S6 — Escape key support */
  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 1100,
        background: "rgba(44,62,80,0.35)", backdropFilter: "blur(3px)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "var(--bg-surface)", border: "1px solid var(--border-soft)",
          borderRadius: "var(--radius-lg)", boxShadow: "0 24px 64px rgba(44,62,80,0.18)",
          padding: "32px 28px 28px", width: "100%", maxWidth,
          display: "flex", flexDirection: "column", gap: 20,
        }}
      >
        {children}
      </div>
    </div>
  );
}

/* ─── Reusable modal header row ────────────────────────────────── */
function ModalHeader({ title, sub, onClose }) {
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{
            fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 800,
            color: "var(--text-primary)", letterSpacing: "-0.02em",
          }}>{title}</div>
          {sub && (
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>
              {sub}
            </div>
          )}
        </div>
        <button onClick={onClose} style={{
          background: "var(--bg-overlay)", border: "1px solid var(--border-soft)",
          borderRadius: "var(--radius-sm)", width: 32, height: 32, cursor: "pointer",
          color: "var(--text-muted)", display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: 14, fontWeight: 600, flexShrink: 0,
        }}>✕</button>
      </div>
      <div style={{ height: 1, background: "var(--border-dim)" }} />
    </>
  );
}

/* ─── Detail row used in View / Health Check modals ───────────── */
function DetailRow({ label, children, last = false }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 16,
      padding: "11px 0",
      borderBottom: last ? "none" : "1px solid var(--border-dim)",
    }}>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
        letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase",
        minWidth: 120, paddingTop: 2, flexShrink: 0,
      }}>{label}</span>
      <span style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-primary)", flex: 1 }}>
        {children}
      </span>
    </div>
  );
}

/* ─── FormField — module-level for stable identity ────────────── */
function FormField({ label, value, onChange, placeholder, error, type = "text" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
        letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase",
      }}>
        {label}{error && <span style={{ color: "#E74C3C", marginLeft: 4 }}>*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          padding: "9px 12px", borderRadius: "var(--radius-sm)",
          border: `1px solid ${error ? "#E74C3C" : "var(--border-soft)"}`,
          background: "var(--bg-void)", fontFamily: "var(--font-body)",
          fontSize: 13, color: "var(--text-primary)", outline: "none",
          transition: "border-color 0.16s ease", width: "100%", boxSizing: "border-box",
        }}
        onFocus={e => { e.target.style.borderColor = "var(--cyan)"; }}
        onBlur={e  => { e.target.style.borderColor = error ? "#E74C3C" : "var(--border-soft)"; }}
      />
    </div>
  );
}

/* ─── Battery indicator ────────────────────────────────────────── */
function BatteryBar({ level }) {
  if (level === null) {
    return <span className="page-table-mono" style={{ color: "var(--text-muted)" }}>—</span>;
  }
  const isCrit = level <= 15;
  const isLow  = level <= 35;
  const fill   = isCrit ? "#E74C3C" : isLow ? "var(--orange)" : "var(--green)";
  const color  = isCrit ? "#E74C3C" : isLow ? "var(--orange)" : "var(--text-secondary)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 7, minWidth: 72 }}>
      <div style={{
        flex: 1, height: 5, borderRadius: 10,
        background: "var(--bg-overlay)", border: "1px solid var(--border-dim)", overflow: "hidden",
      }}>
        <div style={{ width: `${level}%`, height: "100%", borderRadius: 10, background: fill, transition: "width 0.4s ease" }} />
      </div>
      <span className="page-table-mono" style={{ minWidth: 30, textAlign: "right", color }}>{level}%</span>
    </div>
  );
}

/* ─── Slots fill indicator ─────────────────────────────────────── */
function SlotsIndicator({ slotsUsed, slotsTotal }) {
  const full = slotsUsed === slotsTotal;
  return (
    <span className="page-table-mono" style={{ color: full ? "var(--violet)" : "var(--text-secondary)" }}>
      {slotsUsed}/{slotsTotal}
    </span>
  );
}

/* ─── Online/offline dot ───────────────────────────────────────── */
function StatusDot({ status }) {
  const color =
    status === "Online"      ? "var(--green)"  :
    status === "Battery Low" ? "var(--orange)" :
    status === "Restarting"  ? "var(--violet)" : "#E74C3C";
  return (
    <span style={{
      display: "inline-block", width: 7, height: 7, borderRadius: "50%",
      background: color, marginRight: 6, flexShrink: 0,
      animation: status === "Online" ? "pulse 2.4s ease-in-out infinite" : "none",
    }} />
  );
}

/* ─── Action button ────────────────────────────────────────────── */
function ActionBtn({ label, variant, onClick, disabled, ...props }) {
  const styles = {
    view:    { color: "var(--cyan)",   bg: "rgba(58,141,255,0.08)", border: "rgba(58,141,255,0.20)" },
    restart: { color: "var(--teal)",   bg: "rgba(74,163,162,0.08)", border: "rgba(74,163,162,0.20)" },
    health:  { color: "var(--violet)", bg: "rgba(142,140,255,0.08)",border: "rgba(142,140,255,0.20)"},
    delete:  { color: "#E74C3C",       bg: "rgba(231,76,60,0.07)",  border: "rgba(231,76,60,0.18)" },
  };
  const s = styles[variant] || styles.view;
  return (
    <button
      className="page-action-btn"
      disabled={disabled}
      style={{
        color: s.color, background: s.bg, border: `1px solid ${s.border}`,
        opacity: disabled ? 0.45 : 1, cursor: disabled ? "not-allowed" : "pointer",
      }}
      onClick={onClick}
      {...props}
    >
      {label}
    </button>
  );
}

/* ══════════════════════════════════════════════════════════════════
   MODALS
═══════════════════════════════════════════════════════════════════ */

/* ── Register Device Modal ──────────────────────────────────────── */
function RegisterDeviceModal({ onClose, onRegister }) {
  const [devId,      setDevId]      = useState("");
  const [ward,       setWard]       = useState("");
  const [room,       setRoom]       = useState("");
  const [slotsTotal, setSlotsTotal] = useState("");
  const [battery,    setBattery]    = useState("");
  const [errors,     setErrors]     = useState({});

  const clearErr = f => setErrors(p => ({ ...p, [f]: false }));

  const validate = () => {
    const e = {};
    if (!devId.trim())               e.devId      = true;
    if (!ward.trim())                e.ward       = true;
    if (!room.trim())                e.room       = true;
    if (!slotsTotal || isNaN(Number(slotsTotal)) || Number(slotsTotal) < 1) e.slotsTotal = true;
    if (!battery    || isNaN(Number(battery))    || Number(battery) < 0 || Number(battery) > 100) e.battery = true;
    return e;
  };

  const handleSubmit = () => {
    const e = validate();
    if (Object.keys(e).length) { setErrors(e); return; }
    const now = new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    onRegister({
      id:            devId.trim().toUpperCase(),
      ward:          ward.trim(),
      room:          room.trim(),
      status:        "Online",
      battery:       Number(battery),
      slotsUsed:     0,
      slotsTotal:    Number(slotsTotal),
      lastHeartbeat: now,
    });
    onClose();
  };

  return (
    <Modal onClose={onClose} maxWidth={480}>
      <ModalHeader title="Register Device" sub="New IoT dispenser · MEDI-DISPENSE" onClose={onClose} />
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <FormField label="Device ID"    value={devId}      onChange={e => { setDevId(e.target.value);      clearErr("devId");      }} placeholder="e.g. DEV-7F3A"  error={errors.devId}      />
        <FormField label="Ward"         value={ward}       onChange={e => { setWard(e.target.value);       clearErr("ward");       }} placeholder="e.g. Ward 3B"   error={errors.ward}       />
        <FormField label="Room"         value={room}       onChange={e => { setRoom(e.target.value);       clearErr("room");       }} placeholder="e.g. Room 12"   error={errors.room}       />
        <FormField label="Total Slots"  value={slotsTotal} onChange={e => { setSlotsTotal(e.target.value); clearErr("slotsTotal"); }} placeholder="e.g. 6"         error={errors.slotsTotal} type="number" />
        <FormField label="Battery %"    value={battery}    onChange={e => { setBattery(e.target.value);    clearErr("battery");    }} placeholder="e.g. 87"        error={errors.battery}    type="number" />
      </div>
      <div style={{ height: 1, background: "var(--border-dim)" }} />
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{
          padding: "9px 20px", borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-soft)", background: "var(--bg-overlay)",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 500,
          color: "var(--text-secondary)", cursor: "pointer",
        }}>Cancel</button>
        <button onClick={handleSubmit} style={{
          padding: "9px 24px", borderRadius: "var(--radius-sm)",
          border: "none", background: "var(--cyan)",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
          color: "#fff", cursor: "pointer", boxShadow: "0 2px 10px rgba(58,141,255,0.25)",
        }}>Register</button>
      </div>
    </Modal>
  );
}

/* ── View Device Modal ──────────────────────────────────────────── */
function ViewDeviceModal({ device, onClose }) {
  const s = STATUS_MAP[device.status] || STATUS_MAP["Online"];
  return (
    <Modal onClose={onClose}>
      <ModalHeader title="Device Details" sub={`${device.id} · MEDI-DISPENSE`} onClose={onClose} />
      <div>
        <DetailRow label="Device ID">
          <span style={{ fontFamily: "var(--font-mono)", color: "var(--cyan)", fontSize: 12 }}>{device.id}</span>
        </DetailRow>
        <DetailRow label="Ward">
          <span className="page-ward-chip">{device.ward}</span>
        </DetailRow>
        <DetailRow label="Room">
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{device.room}</span>
        </DetailRow>
        <DetailRow label="Status">
          <span className="page-status-chip" style={{ color: s.color, background: s.bg, border: `1px solid ${s.border}`, display: "inline-flex", alignItems: "center" }}>
            <StatusDot status={device.status} />{device.status}
          </span>
        </DetailRow>
        <DetailRow label="Battery">
          {device.battery !== null
            ? <BatteryBar level={device.battery} />
            : <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>—</span>}
        </DetailRow>
        <DetailRow label="Slots Used">
          <SlotsIndicator slotsUsed={device.slotsUsed} slotsTotal={device.slotsTotal} />
        </DetailRow>
        <DetailRow label="Last Heartbeat" last>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{device.lastHeartbeat}</span>
        </DetailRow>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{
          padding: "9px 28px", borderRadius: "var(--radius-sm)",
          border: "none", background: "var(--cyan)",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
          color: "#fff", cursor: "pointer", boxShadow: "0 2px 10px rgba(58,141,255,0.25)",
        }}>Close</button>
      </div>
    </Modal>
  );
}

/* ── Health Check Modal ─────────────────────────────────────────── */
function HealthCheckModal({ device, onClose }) {
  const battOk  = device.battery !== null && device.battery > 35;
  const battWarn = device.battery !== null && device.battery > 15 && device.battery <= 35;
  const battCrit = device.battery !== null && device.battery <= 15;
  const connOk  = device.status === "Online" || device.status === "Battery Low";
  const slotPct = device.slotsTotal > 0 ? Math.round((device.slotsUsed / device.slotsTotal) * 100) : 0;

  const Flag = ({ ok, warn, label }) => {
    const color = ok ? "var(--green)" : warn ? "var(--orange)" : "#E74C3C";
    const text  = ok ? "OK" : warn ? "WARNING" : "CRITICAL";
    return (
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 10, fontWeight: 700,
        letterSpacing: "0.1em", color,
      }}>{text} — {label}</span>
    );
  };

  return (
    <Modal onClose={onClose}>
      <ModalHeader title="Health Check" sub={`Diagnostics · ${device.id}`} onClose={onClose} />
      <div>
        <DetailRow label="Battery">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <BatteryBar level={device.battery} />
            <Flag ok={battOk} warn={battWarn && !battCrit} label={
              device.battery === null ? "No data" :
              battCrit ? `${device.battery}% — replace soon` :
              battWarn ? `${device.battery}% — monitor` :
              `${device.battery}% — healthy`
            } />
          </div>
        </DetailRow>
        <DetailRow label="Connection">
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <span className="page-status-chip" style={{
              color: connOk ? "var(--green)" : "#E74C3C",
              background: connOk ? "rgba(39,174,96,0.08)" : "rgba(231,76,60,0.07)",
              border: `1px solid ${connOk ? "rgba(39,174,96,0.20)" : "rgba(231,76,60,0.18)"}`,
              display: "inline-flex", alignItems: "center",
            }}>
              <StatusDot status={device.status} />{device.status}
            </span>
            <Flag ok={connOk} warn={false} label={connOk ? "reachable" : "unreachable"} />
          </div>
        </DetailRow>
        <DetailRow label="Slot Usage">
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <SlotsIndicator slotsUsed={device.slotsUsed} slotsTotal={device.slotsTotal} />
            <Flag
              ok={slotPct < 100} warn={slotPct >= 80 && slotPct < 100}
              label={slotPct === 100 ? "all slots occupied — refill needed" : slotPct >= 80 ? `${slotPct}% full — monitor` : `${slotPct}% full`}
            />
          </div>
        </DetailRow>
        <DetailRow label="Last Heartbeat" last>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{device.lastHeartbeat}</span>
        </DetailRow>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{
          padding: "9px 28px", borderRadius: "var(--radius-sm)",
          border: "none", background: "var(--violet)",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
          color: "#fff", cursor: "pointer", boxShadow: "0 2px 10px rgba(142,140,255,0.25)",
        }}>Close</button>
      </div>
    </Modal>
  );
}

/* ── Confirm Delete Modal ───────────────────────────────────────── */
function ConfirmDeleteModal({ device, onConfirm, onClose }) {
  return (
    <Modal onClose={onClose} maxWidth={400}>
      <ModalHeader title="Remove Device" sub={`${device.id} · MEDI-DISPENSE`} onClose={onClose} />
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <p style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-secondary)", margin: 0, lineHeight: 1.6 }}>
          Are you sure you want to remove device <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontSize: 12 }}>{device.id}</span> from the registry?
        </p>
        <p style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#E74C3C", margin: 0, letterSpacing: "0.04em" }}>
          This action cannot be undone.
        </p>
      </div>
      <div style={{ height: 1, background: "var(--border-dim)" }} />
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{
          padding: "9px 20px", borderRadius: "var(--radius-sm)",
          border: "1px solid var(--border-soft)", background: "var(--bg-overlay)",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 500,
          color: "var(--text-secondary)", cursor: "pointer",
        }}>Cancel</button>
        <button onClick={onConfirm} style={{
          padding: "9px 24px", borderRadius: "var(--radius-sm)",
          border: "none", background: "#E74C3C",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
          color: "#fff", cursor: "pointer", boxShadow: "0 2px 10px rgba(231,76,60,0.25)",
        }}>Remove Device</button>
      </div>
    </Modal>
  );
}

/* ══════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════ */
export default function Devices() {
  const [devices,            setDevices]           = useState([]);
  const [showRegisterModal,  setShowRegisterModal] = useState(false);
  const [selectedDevice,     setSelectedDevice]    = useState(null);
  const [healthDevice,       setHealthDevice]      = useState(null);
  const [pendingDelete,      setPendingDelete]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDevices = async () => {
      try {
        const data = await apiClient.get('/devices');

        setDevices(data);
      } catch (err) {
        console.error(err);
        setError("Failed to load devices");
      } finally {
        setLoading(false);
      }
    };

    fetchDevices();
  }, []);

  /* Derived counts */
  const total   = devices.length;
  const online  = devices.filter(d => d.status === "Online").length;
  const offline = devices.filter(d => d.status === "Offline").length;
  const battLow = devices.filter(d => d.status === "Battery Low").length;
  const restarting = devices.filter(d => d.status === "Restarting").length;

  const {
    search, setSearch,
    activeFilter, setFilter,
    sort, toggleSort,
    filtered
  } = useTableControls(devices, {
    searchFields: ["id", "ward", "room"],
    filterField: "status",
    sortDefault: { field: "id", dir: "asc" },
    storageKey: "devices"
  });

  /* Register new device */
  const handleRegister = async (formData) => {
    try {
      await apiClient.post('/devices', {
        id: formData.id,
        ward: formData.ward,
        type: formData.type,
      });

      const refreshedData = await apiClient.get('/devices');

      setDevices(refreshedData);

    } catch (err) {
      console.error(err);
    }   
  };

  /* Delete confirmed */
  const handleDelete = async (id) => {
    try {
      await apiClient.delete(`/devices/${id}`);
      const refreshedData = await apiClient.get('/devices');

      setDevices(refreshedData);
      setPendingDelete(null);

    } catch (err) {
      console.error(err);
    }
  };

  /* Restart: set Restarting, then back to Online after 2 s */
  const handleRestart = (id) => {
    setDevices(prev => prev.map(d => d.id === id ? { ...d, status: "Restarting" } : d));
    setTimeout(() => {
      setDevices(prev => prev.map(d =>
        d.id === id && d.status === "Restarting"
          ? { ...d, status: "Online", lastHeartbeat: new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) }
          : d
      ));
    }, 2000);
  };

  /* Live telemetry simulation — ticks every 10 seconds */
  useEffect(() => {
    const interval = setInterval(() => {
      setDevices(prev =>
        prev.map(device => {
          /* Skip devices mid-reboot */
          if (device.status === "Restarting") return device;

          let battery = device.battery;
          if (battery !== null) {
            battery = Math.max(5, battery - Math.floor(Math.random() * 2));
          }

          let status = device.status;
          if (Math.random() < 0.05) {
            status = status === "Online" ? "Offline" : "Online";
          }

          if (battery !== null && battery <= 15 && status === "Online") {
            status = "Battery Low";
          } else if (battery !== null && battery > 15 && status === "Battery Low") {
            status = "Online";
          }

          const slotsUsed = Math.min(
            device.slotsTotal,
            Math.max(0, device.slotsUsed + Math.floor(Math.random() * 3) - 1)
          );

          const lastHeartbeat =
            status !== "Offline"
              ? new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
              : device.lastHeartbeat;

          return { ...device, battery, status, slotsUsed, lastHeartbeat };
        })
      );
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Register Device modal */}
      {showRegisterModal && (
        <RegisterDeviceModal
          onClose={() => setShowRegisterModal(false)}
          onRegister={handleRegister}
        />
      )}

      {/* View Device modal */}
      {selectedDevice && (
        <ViewDeviceModal
          device={selectedDevice}
          onClose={() => setSelectedDevice(null)}
        />
      )}

      {/* Health Check modal */}
      {healthDevice && (
        <HealthCheckModal
          device={healthDevice}
          onClose={() => setHealthDevice(null)}
        />
      )}

      {/* Confirm Delete modal */}
      {pendingDelete && (
        <ConfirmDeleteModal
          device={pendingDelete}
          onConfirm={() => handleDelete(pendingDelete.id)}
          onClose={() => setPendingDelete(null)}
        />
      )}

      <main className="main-content page-main">

        {/* ── Header ──────────────────────────────────────────────── */}
        <header className="dash-header">
          <div className="dash-header-left">
            <span className="breadcrumb">MEDI-DISPENSE</span>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-active">Devices</span>
          </div>
          <div className="dash-header-right">
            <div className="status-pill">
              <span className="pulse-dot" />
              {online} Online
            </div>
            <button className="page-add-btn" onClick={() => setShowRegisterModal(true)}>
              + Register Device
            </button>
          </div>
        </header>

        {/* ── Hero ────────────────────────────────────────────────── */}
        <section className="dash-hero">
          <div className="hero-line" />
          <div className="hero-text">
            <h1 className="hero-title">Device Monitoring</h1>
            <p className="hero-sub">
              IoT medication dispensers · Ward connectivity · Real-time telemetry
            </p>
          </div>
          <div className="hero-badge">{total} DEVICES</div>
        </section>

        {/* ── Summary chips ───────────────────────────────────────── */}
        <div className="page-summary-row">
          <div className="page-summary-chip page-summary-chip--default">
            <span className="page-summary-val">{total}</span>
            <span className="page-summary-lbl">TOTAL</span>
          </div>
          <div className="page-summary-chip page-summary-chip--green">
            <span className="page-summary-val">{online}</span>
            <span className="page-summary-lbl">ONLINE</span>
          </div>
          <div className="page-summary-chip" style={{ borderColor: "rgba(231,76,60,0.20)" }}>
            <span className="page-summary-val" style={{ color: "#E74C3C" }}>{offline}</span>
            <span className="page-summary-lbl">OFFLINE</span>
          </div>
          <div className="page-summary-chip page-summary-chip--orange">
            <span className="page-summary-val">{battLow}</span>
            <span className="page-summary-lbl">BATT LOW</span>
          </div>
        </div>

        {/* ── Filters & Search ──────────────────────────────────── */}
        <div style={{ marginBottom: 16 }}>
          <FilterPills
            options={["Online", "Offline", "Battery Low", "Restarting"]}
            active={activeFilter}
            onChange={setFilter}
            counts={{ "Online": online, "Offline": offline, "Battery Low": battLow, "Restarting": restarting }}
          />
        </div>

        <div className="page-search-bar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" width="16" height="16">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            className="page-search-input"
            type="text"
            placeholder="Search device by ID, ward or status…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button className="page-search-clear" onClick={() => setSearch("")}>✕</button>
          )}
        </div>

        {/* ── Table card ──────────────────────────────────────────── */}
        <div className="page-table-card">
          <table className="page-table">
            <thead>
              <tr>
                <SortableHeader field="id" label="Device ID" sort={sort} onSort={toggleSort} />
                <SortableHeader field="ward" label="Ward" sort={sort} onSort={toggleSort} />
                <SortableHeader field="room" label="Room" sort={sort} onSort={toggleSort} />
                <SortableHeader field="status" label="Status" sort={sort} onSort={toggleSort} />
                <SortableHeader field="battery" label="Battery" sort={sort} onSort={toggleSort} />
                <SortableHeader field="lastHeartbeat" label="Last Heartbeat" sort={sort} onSort={toggleSort} />
                <SortableHeader field="slotsUsed" label="Slots Used" sort={sort} onSort={toggleSort} />
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>

              {/* Loading state */}
              {loading && (
                <tr>
                  <td colSpan="8" className="page-table-loading">
                    <span className="spinner" />{" "}Loading devices…
                  </td>
                </tr>
              )}

              {/* Empty state — no devices registered yet */}
              {!loading && devices.length === 0 && (
                <tr>
                  <td colSpan="8" className="page-table-empty">
                    No devices registered yet. Click <strong>+ Register Device</strong> to add one.
                  </td>
                </tr>
              )}

              {/* No search results */}
              {!loading && devices.length > 0 && filtered.length === 0 && (
                <tr>
                  <td colSpan="8" className="page-table-empty">
                    No devices match your search.
                  </td>
                </tr>
              )}

              {!loading && filtered.map(d => {
                const s = STATUS_MAP[d.status] || STATUS_MAP["Online"];
                const isRestarting = d.status === "Restarting";
                return (
                  <tr key={d.id} className="page-table-row" style={{ opacity: isRestarting ? 0.6 : 1 }}>
                    <td className="page-table-id">{d.id}</td>
                    <td>
                      <span className="page-ward-chip">{d.ward}</span>
                    </td>
                    <td className="page-table-mono">{d.room}</td>
                    <td>
                      <span
                        className="page-status-chip"
                        style={{ color: s.color, background: s.bg, border: `1px solid ${s.border}`, display: "inline-flex", alignItems: "center" }}
                      >
                        <StatusDot status={d.status} />
                        {d.status}
                      </span>
                    </td>
                    <td>
                      <BatteryBar level={d.battery} />
                    </td>
                    <td className="page-table-mono">{d.lastHeartbeat}</td>
                    <td>
                      <SlotsIndicator slotsUsed={d.slotsUsed} slotsTotal={d.slotsTotal} />
                    </td>
                    <td>
                      <div className="page-action-group">
                        <ActionBtn
                          label="View"
                          variant="view"
                          disabled={isRestarting}
                          onClick={() => setSelectedDevice(d)}
                          aria-label={`View device ${d.id}`}
                        />
                        <ActionBtn
                          label="Restart"
                          variant="restart"
                          disabled={isRestarting}
                          onClick={() => handleRestart(d.id)}
                          aria-label={`Restart device ${d.id}`}
                        />
                        <ActionBtn
                          label="Health Check"
                          variant="health"
                          disabled={isRestarting}
                          onClick={() => setHealthDevice(d)}
                          aria-label={`Health check device ${d.id}`}
                        />
                        <ActionBtn
                          label="Delete"
                          variant="delete"
                          disabled={isRestarting}
                          onClick={() => setPendingDelete(d)}
                          aria-label={`Delete device ${d.id}`}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}

            </tbody>
          </table>
        </div>

        {/* ── Footer — S7: year updated to 2026 ─────────────────────────── */}
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