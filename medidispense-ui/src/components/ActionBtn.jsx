/**
 * ActionBtn — shared table-row action button
 *
 * Used by: Patients, Medications, Alerts
 * Note: Devices uses its own local ActionBtn (supports additional
 *       variants: restart, health; and a disabled prop) — keep it separate.
 *
 * Props:
 *   label   – button text
 *   variant – "view" | "edit" | "delete" | "resolve" | "ignore"
 *   onClick – click handler
 */
const VARIANT_STYLES = {
  view:    { color: "var(--cyan)",        bg: "rgba(58,141,255,0.08)",  border: "rgba(58,141,255,0.20)"  },
  edit:    { color: "var(--teal)",        bg: "rgba(74,163,162,0.08)",  border: "rgba(74,163,162,0.20)"  },
  delete:  { color: "#E74C3C",            bg: "rgba(231,76,60,0.07)",   border: "rgba(231,76,60,0.18)"   },
  resolve: { color: "var(--green)",       bg: "rgba(39,174,96,0.08)",   border: "rgba(39,174,96,0.20)"   },
  ignore:  { color: "var(--text-muted)",  bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.20)" },
};

export default function ActionBtn({ label, variant, onClick, ...props }) {
  const s = VARIANT_STYLES[variant] ?? VARIANT_STYLES.view;
  return (
    <button
      className="page-action-btn"
      style={{ color: s.color, background: s.bg, border: `1px solid ${s.border}` }}
      onClick={onClick}
      {...props}
    >
      {label}
    </button>
  );
}
