/**
 * SortableHeader — Sprint 5 shared component
 *
 * A <th> element that shows a sort direction indicator and
 * handles click + keyboard (Enter/Space) to toggle sort.
 *
 * Props:
 *   field    string  — the data field this column sorts by
 *   label    string  — display text
 *   sort     object  — { field, dir } from useTableControls
 *   onSort   fn      — toggleSort from useTableControls
 */
export default function SortableHeader({ field, label, sort, onSort }) {
  const isActive = sort.field === field;
  const isAsc    = isActive && sort.dir === "asc";

  const handleKey = (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSort(field);
    }
  };

  return (
    <th
      onClick={() => onSort(field)}
      onKeyDown={handleKey}
      tabIndex={0}
      aria-sort={isActive ? (isAsc ? "ascending" : "descending") : "none"}
      title={`Sort by ${label}`}
      style={{
        cursor: "pointer",
        userSelect: "none",
        outline: "none",
        position: "relative",
      }}
    >
      <span style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        color: isActive ? "var(--cyan)" : undefined,
        transition: "color 0.15s",
      }}>
        {label}
        {/* Sort indicator */}
        <span
          aria-hidden="true"
          style={{
            display: "inline-flex",
            flexDirection: "column",
            gap: 1,
            opacity: isActive ? 1 : 0.35,
            fontSize: 8,
            lineHeight: 1,
            transition: "opacity 0.15s",
          }}
        >
          {/* Up chevron */}
          <span style={{ color: isActive && !isAsc ? "var(--cyan)" : "var(--text-muted)" }}>▲</span>
          {/* Down chevron */}
          <span style={{ color: isActive && isAsc ? "var(--cyan)" : "var(--text-muted)" }}>▼</span>
        </span>
      </span>
    </th>
  );
}
