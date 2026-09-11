/**
 * FormField — shared labeled text input with validation state
 *
 * Used by: Patients (Add, Edit modals), Devices (Register modal)
 * Note: Medications uses inline Field closures with different state binding;
 *       those are left as-is to avoid breaking the existing pattern.
 *
 * Props:
 *   label       – uppercase label string
 *   value       – controlled input value
 *   onChange    – change handler
 *   placeholder – placeholder text
 *   error       – boolean; turns border red and shows asterisk on label
 *   type        – input type (default "text")
 */
export default function FormField({ label, value, onChange, placeholder, error, type = "text" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
        letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase",
      }}>
        {label}
        {error && <span style={{ color: "#E74C3C", marginLeft: 4 }}>*</span>}
      </label>
      <input
        type={type}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={{
          padding: "9px 12px",
          borderRadius: "var(--radius-sm)",
          border: `1px solid ${error ? "#E74C3C" : "var(--border-soft)"}`,
          background: "var(--bg-void)",
          fontFamily: "var(--font-body)",
          fontSize: 13,
          color: "var(--text-primary)",
          outline: "none",
          transition: "border-color 0.16s ease",
          width: "100%",
          boxSizing: "border-box",
        }}
        onFocus={e  => { e.target.style.borderColor = "var(--cyan)"; }}
        onBlur={e   => { e.target.style.borderColor = error ? "#E74C3C" : "var(--border-soft)"; }}
      />
    </div>
  );
}
