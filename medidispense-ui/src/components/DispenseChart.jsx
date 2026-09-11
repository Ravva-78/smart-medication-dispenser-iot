import { useEffect, useRef, useState } from "react";

// Static sample data — 7-day dispense activity (swap with real API later)
const WEEK_DATA = [
  { day: "Mon", value: 18 },
  { day: "Tue", value: 24 },
  { day: "Wed", value: 21 },
  { day: "Thu", value: 31 },
  { day: "Fri", value: 28 },
  { day: "Sat", value: 14 },
  { day: "Sun", value: 9  },
];

const W   = 640;
const H   = 200;
const PAD = { top: 24, right: 20, bottom: 40, left: 38 };
const CW  = W - PAD.left - PAD.right;
const CH  = H - PAD.top  - PAD.bottom;

function px(i, len) { return PAD.left + (i / (len - 1)) * CW; }
function py(v, max) { return PAD.top  + CH - (v / max)  * CH; }

// Smooth cubic-bezier spine through data points
function buildSmooth(data, max) {
  if (data.length < 2) return "";
  const pts = data.map((d, i) => ({ x: px(i, data.length), y: py(d.value, max) }));
  let d = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`;
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1];
    const curr = pts[i];
    const cpx  = (prev.x + curr.x) / 2;
    d += ` C ${cpx.toFixed(2)} ${prev.y.toFixed(2)},${cpx.toFixed(2)} ${curr.y.toFixed(2)},${curr.x.toFixed(2)} ${curr.y.toFixed(2)}`;
  }
  return d;
}

function buildArea(data, max) {
  const lastX = px(data.length - 1, data.length);
  const baseY = PAD.top + CH;
  return `${buildSmooth(data, max)} L ${lastX.toFixed(2)} ${baseY} L ${PAD.left} ${baseY} Z`;
}

function yTicks(max) {
  const step = Math.ceil(max / 4 / 5) * 5;
  return [0, 1, 2, 3, 4].map(i => i * step).filter(v => v <= max * 1.05);
}

export default function DispenseChart() {
  const max   = Math.max(...WEEK_DATA.map(d => d.value)) * 1.2;
  const ticks = yTicks(max);
  const total = WEEK_DATA.reduce((s, d) => s + d.value, 0);
  const peak  = WEEK_DATA.reduce((a, b) => b.value > a.value ? b : a);

  const [ready,   setReady]   = useState(false);
  const [hovered, setHovered] = useState(null);
  const lineRef = useRef(null);

  // Delay mount so CSS animation starts cleanly
  useEffect(() => {
    const t = setTimeout(() => setReady(true), 120);
    return () => clearTimeout(t);
  }, []);

  // Measure actual path length and run draw animation
  useEffect(() => {
    if (!ready || !lineRef.current) return;
    const el  = lineRef.current;
    const len = el.getTotalLength ? el.getTotalLength() : 1400;
    el.style.strokeDasharray  = `${len}`;
    el.style.strokeDashoffset = `${len}`;
    void el.getBoundingClientRect();           // force reflow
    el.style.transition       = "stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)";
    el.style.strokeDashoffset = "0";
  }, [ready]);

  const colW = CW / (WEEK_DATA.length - 1);

  return (
    <div className="chart-panel">
      {/* Header */}
      <div className="chart-panel-header">
        <div className="chart-panel-left">
          <span className="chart-title">Dispense Activity</span>
          <span className="chart-sub">Last 7 days · All wards</span>
        </div>

        <div className="chart-meta">
          {hovered !== null ? (
            <div className="chart-hover-stat">
              <span className="chart-hover-day">{WEEK_DATA[hovered].day}</span>
              <span className="chart-hover-val">{WEEK_DATA[hovered].value}</span>
              <span className="chart-hover-lbl">dispenses</span>
            </div>
          ) : (
            <div className="chart-summary">
              <div className="chart-chip">
                <span className="chip-lbl">TOTAL</span>
                <span className="chip-val">{total}</span>
              </div>
              <div className="chart-chip chart-chip--peak">
                <span className="chip-lbl">PEAK</span>
                <span className="chip-val">{peak.day} · {peak.value}</span>
              </div>
            </div>
          )}
          <div className="chart-legend">
            <span className="legend-dot" />
            <span className="legend-label">Dispenses / day</span>
          </div>
        </div>
      </div>

      {/* SVG */}
      <div className="chart-wrap">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          preserveAspectRatio="xMidYMid meet"
          className="chart-svg"
          aria-label="Dispense Activity — last 7 days"
          role="img"
        >
          <defs>
            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="#00d4ff" stopOpacity="0.26" />
              <stop offset="70%"  stopColor="#00d4ff" stopOpacity="0.05" />
              <stop offset="100%" stopColor="#00d4ff" stopOpacity="0"    />
            </linearGradient>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%"   stopColor="#0072ff" />
              <stop offset="50%"  stopColor="#00c8ff" />
              <stop offset="100%" stopColor="#00ffd0" />
            </linearGradient>
            <filter id="lineGlow" x="-5%" y="-80%" width="110%" height="260%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <filter id="dotGlow" x="-100%" y="-100%" width="300%" height="300%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
            </filter>
            <clipPath id="cClip">
              <rect x={PAD.left} y={0} width={CW} height={H} />
            </clipPath>
          </defs>

          {/* Y-axis grid + labels */}
          {ticks.map(v => {
            const y = py(v, max);
            return (
              <g key={v}>
                <line
                  x1={PAD.left} y1={y} x2={PAD.left + CW} y2={y}
                  stroke={v === 0 ? "rgba(255,255,255,0.1)" : "rgba(255,255,255,0.05)"}
                  strokeWidth="1"
                  strokeDasharray={v === 0 ? "0" : "3 5"}
                />
                {v > 0 && (
                  <text x={PAD.left - 8} y={y + 4}
                    textAnchor="end" fill="rgba(255,255,255,0.3)"
                    fontSize="9.5" fontFamily="'Space Mono',monospace">
                    {v}
                  </text>
                )}
              </g>
            );
          })}

          {/* Area */}
          <path
            d={buildArea(WEEK_DATA, max)}
            fill="url(#areaGrad)"
            clipPath="url(#cClip)"
            style={{ opacity: ready ? 1 : 0, transition: "opacity 0.8s ease 0.5s" }}
          />

          {/* Line */}
          <path
            ref={lineRef}
            d={buildSmooth(WEEK_DATA, max)}
            fill="none"
            stroke="url(#lineGrad)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter="url(#lineGlow)"
            clipPath="url(#cClip)"
          />

          {/* Points, hover zones, tooltips */}
          {WEEK_DATA.map((d, i) => {
            const x    = px(i, WEEK_DATA.length);
            const y    = py(d.value, max);
            const isHov = hovered === i;

            // Tooltip box — clamp to chart edges
            const bw = 52; const bh = 30;
            const bx = Math.min(Math.max(x - bw / 2, PAD.left), PAD.left + CW - bw);
            const by = Math.max(y - bh - 12, PAD.top + 2);

            return (
              <g key={i}>
                {/* Hit area */}
                <rect
                  x={x - colW / 2} y={PAD.top}
                  width={colW} height={CH}
                  fill="transparent"
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                  style={{ cursor: "crosshair" }}
                />

                {/* Vertical rule on hover */}
                {isHov && (
                  <line x1={x} y1={PAD.top} x2={x} y2={PAD.top + CH}
                    stroke="rgba(0,212,255,0.28)" strokeWidth="1" strokeDasharray="3 4" />
                )}

                {/* Dot */}
                <circle
                  cx={x} cy={y}
                  r={isHov ? 6.5 : 3.5}
                  fill={isHov ? "#00d4ff" : "rgba(11,15,28,0.95)"}
                  stroke={isHov ? "#00d4ff" : "rgba(0,200,255,0.65)"}
                  strokeWidth={isHov ? 2 : 1.5}
                  filter={isHov ? "url(#dotGlow)" : undefined}
                  opacity={ready ? 1 : 0}
                  style={{ transition: "r 0.18s ease, opacity 0.3s ease" }}
                />

                {/* Tooltip */}
                {isHov && (
                  <g>
                    <rect x={bx} y={by} width={bw} height={bh} rx="8"
                      fill="rgba(18,24,44,0.97)"
                      stroke="rgba(0,212,255,0.38)" strokeWidth="1" />
                    <text x={bx + bw/2} y={by + 11.5} textAnchor="middle"
                      fill="rgba(255,255,255,0.45)" fontSize="8.5"
                      fontFamily="'Space Mono',monospace">
                      {d.day}
                    </text>
                    <text x={bx + bw/2} y={by + 24} textAnchor="middle"
                      fill="#00d4ff" fontSize="12.5"
                      fontFamily="'Space Mono',monospace" fontWeight="700">
                      {d.value}
                    </text>
                  </g>
                )}

                {/* X-axis label */}
                <text x={x} y={H - 10} textAnchor="middle"
                  fill={isHov ? "rgba(0,212,255,0.95)" : "rgba(255,255,255,0.3)"}
                  fontSize="9.5" fontFamily="'Space Mono',monospace"
                  fontWeight={isHov ? "700" : "400"}
                  style={{ transition: "fill 0.15s ease" }}>
                  {d.day}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}