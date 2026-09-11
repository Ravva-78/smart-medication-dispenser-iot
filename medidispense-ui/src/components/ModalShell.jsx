import { useEffect } from "react";

/**
 * ModalShell — shared modal backdrop + panel container
 *
 * Used by: Patients, Medications, Alerts, App (ProfileModal)
 * Note: Devices already defines its own local Modal + ModalHeader with
 *       the same visual style — those are left as-is to avoid churn.
 *
 * Includes:
 *   - S5: Shared modal backdrop and panel (eliminates repeated inline styles)
 *   - S6: Escape key listener (auto-closes on Escape)
 *
 * Props:
 *   onClose  – close handler (called on backdrop click and Escape)
 *   children – modal body content
 *   maxWidth – panel max-width in px (default 440)
 *   gap      – flex column gap in px (default 0); use 20 for form modals
 */
export function ModalShell({ onClose, children, maxWidth = 440, gap = 0 }) {
  /* S6 — Escape key support */
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === "Escape") onClose();
    };
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
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-soft)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "0 24px 64px rgba(44,62,80,0.18)",
          padding: "32px 28px 28px",
          width: "100%", maxWidth,
          maxHeight: "calc(100vh - 48px)", overflowY: "auto",
          display: "flex", flexDirection: "column", gap,
        }}
      >
        {children}
      </div>
    </div>
  );
}

/**
 * ModalHeader — title row with subtitle and close button
 *
 * Props:
 *   title    – modal heading text
 *   sub      – small mono subtitle line (optional)
 *   onClose  – close handler for the × button
 *   divider  – whether to render the separator line below (default true)
 */
export function ModalHeader({ title, sub, onClose, divider = true }) {
  return (
    <>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <div style={{
            fontFamily: "var(--font-display)", fontSize: 18, fontWeight: 800,
            color: "var(--text-primary)", letterSpacing: "-0.02em",
          }}>
            {title}
          </div>
          {sub && (
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>
              {sub}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          style={{
            background: "var(--bg-overlay)", border: "1px solid var(--border-soft)",
            borderRadius: "var(--radius-sm)", width: 32, height: 32, cursor: "pointer",
            color: "var(--text-muted)", display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: 14, fontWeight: 600, flexShrink: 0,
          }}
        >
          ✕
        </button>
      </div>
      {divider && <div style={{ height: 1, background: "var(--border-dim)", marginBottom: 4 }} />}
    </>
  );
}

/**
 * ModalRow — a label+value detail row used inside view modals
 *
 * Props:
 *   label    – uppercase mono label
 *   children – value content (string or JSX)
 */
export function ModalRow({ label, children }) {
  return (
    <div style={{
      display: "flex", alignItems: "flex-start",
      padding: "12px 0", borderBottom: "1px solid var(--border-dim)",
      gap: 16,
    }}>
      <span style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
        letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase",
        minWidth: 110, paddingTop: 2, flexShrink: 0,
      }}>
        {label}
      </span>
      <span style={{ fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-primary)", flex: 1 }}>
        {children}
      </span>
    </div>
  );
}

/**
 * ModalDivider — thin horizontal rule between modal sections
 */
export function ModalDivider() {
  return <div style={{ height: 1, background: "var(--border-dim)" }} />;
}

/**
 * ModalActions — right-aligned action button row
 *
 * Props:
 *   children – Cancel + primary button(s)
 */
export function ModalActions({ children }) {
  return (
    <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
      {children}
    </div>
  );
}
