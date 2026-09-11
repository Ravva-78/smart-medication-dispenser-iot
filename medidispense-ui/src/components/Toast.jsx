import { useEffect } from "react";

/**
 * Global Toast Notification
 * Auto-dismisses after 3.5s. Variants: "success" | "error" | "warning" | "info"
 */
export default function Toast({ message, variant, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3500);
    return () => clearTimeout(t);
  }, [onDismiss]);

  let bg = "rgba(39,174,96,0.12)";
  let border = "rgba(39,174,96,0.30)";
  let color = "var(--green)";
  let icon = "✓";

  if (variant === "error") {
    bg = "rgba(231,76,60,0.12)";
    border = "rgba(231,76,60,0.30)";
    color = "#E74C3C";
    icon = "✕";
  } else if (variant === "warning") {
    bg = "rgba(230,126,34,0.12)";
    border = "rgba(230,126,34,0.30)";
    color = "var(--orange)";
    icon = "!";
  } else if (variant === "info") {
    bg = "rgba(74,163,162,0.12)";
    border = "rgba(74,163,162,0.30)";
    color = "var(--teal)";
    icon = "i";
  }

  return (
    <div style={{
      position: "fixed", bottom: 28, right: 28, zIndex: 9999,
      display: "flex", alignItems: "center", gap: 10,
      padding: "12px 18px", borderRadius: "var(--radius-sm)",
      background: bg,
      border: `1px solid ${border}`,
      boxShadow: "0 8px 32px rgba(10,15,30,0.28)",
      backdropFilter: "blur(8px)",
      fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 500,
      color: color,
      animation: "fadeSlideIn 0.2s ease",
      minWidth: 240, maxWidth: 380,
    }}>
      <span style={{ fontSize: 16 }}>{icon}</span>
      <span style={{ flex: 1 }}>{message}</span>
      <button
        onClick={onDismiss}
        style={{
          background: "none", border: "none", cursor: "pointer",
          color: "inherit", fontSize: 16, lineHeight: 1, padding: "0 2px",
          opacity: 0.7,
        }}
      >
        ×
      </button>
    </div>
  );
}
