import { useEffect, useRef, useState } from "react";

// Animated number counter
function Counter({ target }) {
  const [display, setDisplay] = useState(0);
  const rafRef = useRef(null);

  useEffect(() => {
    const duration = 900;
    const start = performance.now();
    const from = 0;

    const tick = (now) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(from + (target - from) * eased));
      if (progress < 1) rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target]);

  return <span>{display}</span>;
}

export default function StatCard({ label, value, icon, accent, glow, tag, index }) {
  return (
    <div
      className="stat-card"
      style={{
        "--accent": accent,
        "--glow": glow,
        "--delay": `${index * 80}ms`,
      }}
    >
      {/* Glow layer */}
      <div className="card-glow-bg" />

      {/* Top row: tag + icon */}
      <div className="card-top">
        <span className="card-tag">{tag}</span>
        <div className="card-icon">{icon}</div>
      </div>

      {/* Value */}
      <div className="card-value">
        <Counter target={value} />
      </div>

      {/* Label */}
      <div className="card-label">{label}</div>

      {/* Bottom accent bar */}
      <div className="card-bar" />

      {/* Shine sweep on hover */}
      <div className="card-shine" />
    </div>
  );
}
