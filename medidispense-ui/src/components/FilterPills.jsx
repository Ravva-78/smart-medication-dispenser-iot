/**
 * FilterPills — Sprint 5 shared component
 *
 * Renders a horizontal row of status filter buttons.
 * "All" is always the first option. Keyboard accessible:
 * left/right arrow keys move between pills.
 *
 * Props:
 *   options  string[]   — list of status values (without "All")
 *   active   string     — currently selected filter ("All" or a status)
 *   onChange fn(string) — called with the newly selected filter
 *   counts   object     — optional { [status]: count } for badge display
 */
export default function FilterPills({ options = [], active, onChange, counts = {} }) {
  const all = ["All", ...options];

  const handleKeyDown = (e, i) => {
    if (e.key === "ArrowRight") {
      const next = all[(i + 1) % all.length];
      onChange(next);
      document.getElementById(`fpill-${next}`)?.focus();
    } else if (e.key === "ArrowLeft") {
      const prev = all[(i - 1 + all.length) % all.length];
      onChange(prev);
      document.getElementById(`fpill-${prev}`)?.focus();
    }
  };

  return (
    <div
      role="group"
      aria-label="Status filter"
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 6,
        margin: "0 0 14px",
      }}
    >
      {all.map((opt, i) => {
        const isActive = active === opt;
        return (
          <button
            key={opt}
            id={`fpill-${opt}`}
            role="radio"
            aria-checked={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(opt)}
            onKeyDown={(e) => handleKeyDown(e, i)}
            style={{
              padding: "5px 13px",
              borderRadius: 20,
              border: isActive
                ? "1px solid var(--cyan)"
                : "1px solid var(--border-soft)",
              background: isActive
                ? "rgba(58,141,255,0.12)"
                : "var(--bg-overlay)",
              color: isActive
                ? "var(--cyan)"
                : "var(--text-secondary)",
              fontFamily: "var(--font-body)",
              fontSize: 12,
              fontWeight: isActive ? 600 : 400,
              cursor: "pointer",
              transition: "all 0.15s ease",
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              outline: "none",
              boxShadow: isActive
                ? "0 0 0 2px rgba(58,141,255,0.18)"
                : "none",
            }}
          >
            {opt}
            {counts[opt] !== undefined && (
              <span style={{
                fontSize: 10, fontWeight: 700,
                background: isActive
                  ? "rgba(58,141,255,0.25)"
                  : "var(--bg-surface)",
                color: isActive ? "var(--cyan)" : "var(--text-muted)",
                borderRadius: 10,
                padding: "1px 6px",
                minWidth: 18,
                textAlign: "center",
              }}>
                {counts[opt]}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
