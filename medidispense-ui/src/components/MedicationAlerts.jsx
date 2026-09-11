/**
 * MedicationAlerts — Sprint 4
 *
 * Accepts live medication list from App.jsx.
 * Shows up to 3 non-OK medications sorted by urgency (Critical first).
 * Falls back gracefully when loading or when no data is available.
 *
 * Props:
 *   medications  array   — full medication list from backend
 *   loading      boolean — show skeleton rows while fetching
 */

const CHIP_MAP = {
  "Critical":  { cls: "critical", label: "Critical"     },
  "Low Stock": { cls: "warn",     label: "Low Stock"     },
  "Expired":   { cls: "critical", label: "Expired"       },
};

const STRIPE_MAP = {
  "Critical":  "critical",
  "Low Stock": "warn",
  "Expired":   "critical",
};

const URGENCY = { Critical: 0, Expired: 0, "Low Stock": 1 };

export default function MedicationAlerts({ medications = [], loading = false }) {
  /* Filter non-OK meds, sort by urgency, cap at 3 */
  const alerts = medications
    .filter(m => m.status !== "OK")
    .sort((a, b) => (URGENCY[a.status] ?? 2) - (URGENCY[b.status] ?? 2))
    .slice(0, 3);

  const activeCount = medications.filter(m => m.status !== "OK").length;

  return (
    <div className="med-alert-card">
      <div className="card-header">
        <span className="card-header-title">Medication Alerts</span>
        <span className="card-header-badge">
          {loading ? "…" : `${activeCount} ACTIVE`}
        </span>
      </div>

      {/* Skeleton rows */}
      {loading && [0, 1, 2].map(i => (
        <div key={i} className="alert-row" style={{ gap: 10 }}>
          <span className="alert-stripe info" aria-hidden="true"
            style={{ opacity: 0.3 }} />
          <div className="alert-body">
            <span className="skel-line" style={{ width: "60%", height: 11 }} />
            <span className="skel-line" style={{ width: "40%", height: 9, marginTop: 5 }} />
          </div>
        </div>
      ))}

      {/* Live rows */}
      {!loading && alerts.map(m => {
        const chip   = CHIP_MAP[m.status]   || { cls: "info", label: m.status };
        const stripe = STRIPE_MAP[m.status] || "info";
        return (
          <div className="alert-row" key={m.id}>
            <span className={`alert-stripe ${stripe}`} aria-hidden="true" />
            <div className="alert-body">
              <span className="alert-name">{m.name}</span>
              <span className="alert-detail">
                {m.stock} units · threshold {m.threshold}
              </span>
            </div>
            <span className={`alert-chip ${chip.cls}`}>{chip.label}</span>
          </div>
        );
      })}

      {/* Empty state */}
      {!loading && alerts.length === 0 && (
        <div style={{
          padding: "18px 0", textAlign: "center",
          fontFamily: "var(--font-body)", fontSize: 12,
          color: "var(--text-muted)",
        }}>
          All medications within threshold ✓
        </div>
      )}
    </div>
  );
}
