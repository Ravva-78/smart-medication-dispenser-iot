/**
 * DeviceHealth — Sprint 4
 *
 * Accepts live device counts as props from App.jsx.
 * Falls back to "—" when data is still loading.
 *
 * Props:
 *   online   number  — count of Online devices
 *   offline  number  — count of Offline devices
 *   low      number  — count of Battery Low devices
 *   loading  boolean — show skeleton while loading
 */
export default function DeviceHealth({ online = 0, offline = 0, low = 0, loading = false }) {
  const rows = [
    { label: "Online Devices", value: online,  dot: "online"  },
    { label: "Offline Devices", value: offline, dot: "offline" },
    { label: "Battery Low",     value: low,     dot: "warning" },
  ];

  return (
    <div className="device-health-card">
      <div className="card-header">
        <span className="card-header-title">Device Health</span>
        <span className="card-header-badge">LIVE</span>
      </div>

      {rows.map(({ label, value, dot }) => (
        <div className="device-row" key={label}>
          <span className={`device-status-dot ${dot}`} aria-hidden="true" />
          <span className="device-name">{label}</span>
          <span className="device-uptime">
            {loading ? <span style={{ color: "var(--text-muted)", fontSize: 11 }}>—</span> : value}
          </span>
        </div>
      ))}
    </div>
  );
}
