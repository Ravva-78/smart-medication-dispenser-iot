/**
 * ConfirmDialog — Sprint 2 shared component
 *
 * Built on ModalShell so backdrop click + Escape key
 * both trigger onCancel automatically.
 *
 * Props
 *   title          string  — modal heading
 *   message        string  — body copy
 *   confirmLabel   string  — confirm button text  (default "Confirm")
 *   confirmVariant "danger" | "primary"           (default "danger")
 *   onConfirm      ()=>void
 *   onCancel       ()=>void
 */
import { ModalShell } from "./ModalShell";

const VARIANT = {
  danger:  { bg: "#E74C3C", shadow: "rgba(231,76,60,0.30)" },
  primary: { bg: "var(--cyan)", shadow: "rgba(58,141,255,0.25)" },
};

export default function ConfirmDialog({
  title         = "Are you sure?",
  message       = "",
  confirmLabel  = "Confirm",
  confirmVariant = "danger",
  onConfirm,
  onCancel,
}) {
  const v = VARIANT[confirmVariant] || VARIANT.danger;

  return (
    <ModalShell onClose={onCancel} maxWidth={400}>
      {/* Icon */}
      <div style={{ display: "flex", justifyContent: "center", marginBottom: 4 }}>
        <div style={{
          width: 48, height: 48, borderRadius: "50%",
          background: confirmVariant === "danger"
            ? "rgba(231,76,60,0.10)"
            : "rgba(58,141,255,0.10)",
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
        }}>
          {confirmVariant === "danger" ? (
            <svg viewBox="0 0 24 24" fill="none" stroke="#E74C3C" strokeWidth="1.8"
              width="22" height="22">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0
                1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="none" stroke="var(--cyan)" strokeWidth="1.8"
              width="22" height="22">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          )}
        </div>
      </div>

      {/* Title */}
      <div style={{ textAlign: "center" }}>
        <div style={{
          fontFamily: "var(--font-display)", fontSize: 17, fontWeight: 800,
          color: "var(--text-primary)", letterSpacing: "-0.02em", marginBottom: 8,
        }}>
          {title}
        </div>
        {message && (
          <p style={{
            margin: 0,
            fontFamily: "var(--font-body)", fontSize: 13,
            color: "var(--text-secondary)", lineHeight: 1.6,
          }}>
            {message}
          </p>
        )}
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, justifyContent: "center", marginTop: 4 }}>
        <button
          onClick={onCancel}
          style={{
            padding: "9px 22px", borderRadius: "var(--radius-sm)",
            border: "1px solid var(--border-soft)", background: "var(--bg-overlay)",
            fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 500,
            color: "var(--text-secondary)", cursor: "pointer",
            minWidth: 90,
          }}
        >
          Cancel
        </button>
        <button
          onClick={onConfirm}
          style={{
            padding: "9px 22px", borderRadius: "var(--radius-sm)",
            border: "none", background: v.bg,
            fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
            color: "#fff", cursor: "pointer",
            boxShadow: `0 2px 10px ${v.shadow}`,
            minWidth: 90,
          }}
        >
          {confirmLabel}
        </button>
      </div>
    </ModalShell>
  );
}
