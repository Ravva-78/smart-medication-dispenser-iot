import os

svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 1100" width="100%" height="100%" style="background:#0b1120; font-family:'Segoe UI', system-ui, -apple-system, sans-serif;">
  <defs>
    <!-- Background Grid Pattern -->
    <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
      <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#1e293b" stroke-width="0.8" opacity="0.6"/>
    </pattern>

    <!-- Gradients -->
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0284c7" />
      <stop offset="50%" stop-color="#06b6d4" />
      <stop offset="100%" stop-color="#10b981" />
    </linearGradient>

    <linearGradient id="cardGradDark" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" stop-opacity="0.95" />
      <stop offset="100%" stop-color="#0f172a" stop-opacity="0.95" />
    </linearGradient>

    <linearGradient id="blueCard" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e3a8a" />
      <stop offset="100%" stop-color="#0284c7" />
    </linearGradient>

    <linearGradient id="cyanCard" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0e7490" />
      <stop offset="100%" stop-color="#06b6d4" />
    </linearGradient>

    <linearGradient id="emeraldCard" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#065f46" />
      <stop offset="100%" stop-color="#10b981" />
    </linearGradient>

    <linearGradient id="purpleCard" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#581c87" />
      <stop offset="100%" stop-color="#9333ea" />
    </linearGradient>

    <linearGradient id="amberCard" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#78350f" />
      <stop offset="100%" stop-color="#d97706" />
    </linearGradient>

    <!-- Filters & Shadows -->
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000000" flood-opacity="0.5"/>
    </filter>

    <filter id="glowBlue" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>

    <!-- Arrow Markers -->
    <marker id="arrowCyan" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto">
      <path d="M0,0 L0,6 L8,3 z" fill="#06b6d4" />
    </marker>
    <marker id="arrowEmerald" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto">
      <path d="M0,0 L0,6 L8,3 z" fill="#10b981" />
    </marker>
    <marker id="arrowPurple" markerWidth="10" markerHeight="10" refX="6" refY="3" orient="auto">
      <path d="M0,0 L0,6 L8,3 z" fill="#a855f7" />
    </marker>
  </defs>

  <!-- Background Layer -->
  <rect width="1200" height="1100" fill="#0b1120" />
  <rect width="1200" height="1100" fill="url(#grid)" />

  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <!-- HEADER & TITLE -->
  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <g transform="translate(50, 40)">
    <rect x="0" y="0" width="1100" height="85" rx="16" fill="url(#cardGradDark)" stroke="#334155" stroke-width="1.5" filter="url(#shadow)"/>
    <circle cx="45" cy="42" r="22" fill="#0284c7" opacity="0.2"/>
    <path d="M45 28 L45 56 M31 42 L59 42" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"/>
    
    <text x="85" y="38" font-size="24" font-weight="800" fill="#f8fafc" letter-spacing="0.5">MEDIDISPENSE · SYSTEM ARCHITECTURE</text>
    <text x="85" y="62" font-size="13" font-weight="500" fill="#94a3b8">Autonomous AI Medicine Blister Strip Inspection &amp; Clinical Adherence Platform</text>
    
    <rect x="940" y="28" width="130" height="28" rx="14" fill="#065f46" stroke="#10b981" stroke-width="1"/>
    <circle cx="956" cy="42" r="5" fill="#34d399"/>
    <text x="968" y="47" font-size="12" font-weight="700" fill="#a7f3d0">PRODUCTION v1.0</text>
  </g>

  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <!-- TIER 1: INPUT ACQUISITION -->
  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <g transform="translate(380, 155)">
    <rect x="0" y="0" width="440" height="65" rx="14" fill="url(#cardGradDark)" stroke="#0284c7" stroke-width="1.8" filter="url(#shadow)"/>
    <text x="220" y="28" text-anchor="middle" font-size="14" font-weight="700" fill="#38bdf8">📸 1. DATA ACQUISITION &amp; CAMERA INPUT</text>
    <text x="220" y="48" text-anchor="middle" font-size="12" font-weight="500" fill="#cbd5e1">IoT Camera Frame • Video Stream • Mobile Upload • High-Res RGB</text>
  </g>

  <!-- Flow 1 -> 2 -->
  <path d="M 600 220 L 600 255" fill="none" stroke="#06b6d4" stroke-width="2.5" marker-end="url(#arrowCyan)" />

  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <!-- TIER 2: COMPUTER VISION PIPELINE (MODELS A -> B -> C) -->
  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <g transform="translate(50, 260)">
    <!-- Container Box -->
    <rect x="0" y="0" width="1100" height="210" rx="18" fill="url(#cardGradDark)" stroke="#0e7490" stroke-width="1.5" filter="url(#shadow)"/>
    <rect x="25" y="-12" width="280" height="24" rx="6" fill="#083344" stroke="#06b6d4" stroke-width="1"/>
    <text x="165" y="4" text-anchor="middle" font-size="12" font-weight="800" fill="#67e8f9">🤖 MULTI-STAGE COMPUTER VISION CASCADE</text>

    <!-- Stage 1: Model A -->
    <g transform="translate(30, 30)">
      <rect x="0" y="0" width="240" height="150" rx="12" fill="#0f172a" stroke="#1e3a8a" stroke-width="1.2"/>
      <rect x="12" y="12" width="216" height="30" rx="6" fill="url(#blueCard)"/>
      <text x="120" y="32" text-anchor="middle" font-size="13" font-weight="800" fill="#ffffff">STAGE 1: MODEL A</text>
      <text x="120" y="65" text-anchor="middle" font-size="12" font-weight="700" fill="#38bdf8">YOLO11s Strip Detector</text>
      <text x="120" y="85" text-anchor="middle" font-size="11" fill="#94a3b8">Locates Blister Pack in Scene</text>
      
      <line x1="20" y1="100" x2="220" y2="100" stroke="#334155" stroke-width="0.8"/>
      <rect x="30" y="112" width="180" height="24" rx="12" fill="#1e293b" stroke="#3b82f6" stroke-width="0.8"/>
      <text x="120" y="128" text-anchor="middle" font-size="11" font-weight="700" fill="#93c5fd">mAP50: 99.50% | Prec: 99.9%</text>
    </g>

    <!-- Arrow 1 -> 2 -->
    <path d="M 275 105 L 305 105" fill="none" stroke="#06b6d4" stroke-width="2.5" marker-end="url(#arrowCyan)" />

    <!-- Stage 2: Perspective Correction -->
    <g transform="translate(310, 30)">
      <rect x="0" y="0" width="225" height="150" rx="12" fill="#0f172a" stroke="#047857" stroke-width="1.2"/>
      <rect x="12" y="12" width="201" height="30" rx="6" fill="url(#emeraldCard)"/>
      <text x="112" y="32" text-anchor="middle" font-size="13" font-weight="800" fill="#ffffff">STAGE 2: RECTIFIER</text>
      <text x="112" y="65" text-anchor="middle" font-size="12" font-weight="700" fill="#34d399">Perspective Homography</text>
      <text x="112" y="85" text-anchor="middle" font-size="11" fill="#94a3b8">Norms Angle &amp; Shadows</text>
      
      <line x1="20" y1="100" x2="205" y2="100" stroke="#334155" stroke-width="0.8"/>
      <rect x="25" y="112" width="175" height="24" rx="12" fill="#1e293b" stroke="#10b981" stroke-width="0.8"/>
      <text x="112" y="128" text-anchor="middle" font-size="11" font-weight="700" fill="#6ee7b7">Canvas: 800 × 600 px</text>
    </g>

    <!-- Arrow 2 -> 3 -->
    <path d="M 540 105 L 570 105" fill="none" stroke="#06b6d4" stroke-width="2.5" marker-end="url(#arrowCyan)" />

    <!-- Stage 3: Model B -->
    <g transform="translate(575, 30)">
      <rect x="0" y="0" width="240" height="150" rx="12" fill="#0f172a" stroke="#6d28d9" stroke-width="1.2"/>
      <rect x="12" y="12" width="216" height="30" rx="6" fill="url(#purpleCard)"/>
      <text x="120" y="32" text-anchor="middle" font-size="13" font-weight="800" fill="#ffffff">STAGE 3: MODEL B</text>
      <text x="120" y="65" text-anchor="middle" font-size="12" font-weight="700" fill="#c084fc">YOLO11s Pocket Grid</text>
      <text x="120" y="85" text-anchor="middle" font-size="11" fill="#94a3b8">Detects Every Cavity / Pocket</text>
      
      <line x1="20" y1="100" x2="220" y2="100" stroke="#334155" stroke-width="0.8"/>
      <rect x="30" y="112" width="180" height="24" rx="12" fill="#1e293b" stroke="#a855f7" stroke-width="0.8"/>
      <text x="120" y="128" text-anchor="middle" font-size="11" font-weight="700" fill="#d8b4fe">mAP50: 99.50% | Recall 100%</text>
    </g>

    <!-- Arrow 3 -> 4 -->
    <path d="M 820 105 L 850 105" fill="none" stroke="#06b6d4" stroke-width="2.5" marker-end="url(#arrowCyan)" />

    <!-- Stage 4: Model C -->
    <g transform="translate(855, 30)">
      <rect x="0" y="0" width="215" height="150" rx="12" fill="#0f172a" stroke="#b45309" stroke-width="1.2"/>
      <rect x="12" y="12" width="191" height="30" rx="6" fill="url(#amberCard)"/>
      <text x="107" y="32" text-anchor="middle" font-size="13" font-weight="800" fill="#ffffff">STAGE 4: MODEL C</text>
      <text x="107" y="65" text-anchor="middle" font-size="12" font-weight="700" fill="#fbbf24">MobileNetV3 Classifier</text>
      <text x="107" y="85" text-anchor="middle" font-size="11" fill="#94a3b8">Binary: Present vs Missing</text>
      
      <line x1="20" y1="100" x2="195" y2="100" stroke="#334155" stroke-width="0.8"/>
      <rect x="25" y="112" width="165" height="24" rx="12" fill="#1e293b" stroke="#f59e0b" stroke-width="0.8"/>
      <text x="107" y="128" text-anchor="middle" font-size="11" font-weight="700" fill="#fde68a">Accuracy: 99.76%</text>
    </g>
  </g>

  <!-- Flow 2 -> 3 -->
  <path d="M 600 470 L 600 505" fill="none" stroke="#10b981" stroke-width="2.5" marker-end="url(#arrowEmerald)" />
  <rect x="520" y="476" width="160" height="20" rx="10" fill="#064e3b" stroke="#10b981" stroke-width="0.8"/>
  <text x="600" y="490" text-anchor="middle" font-size="10" font-weight="700" fill="#a7f3d0">InspectionResult Contract</text>

  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <!-- TIER 3: DOMAIN CORE & EVENT-DRIVEN SUBSYSTEMS -->
  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <g transform="translate(50, 510)">
    <rect x="0" y="0" width="1100" height="175" rx="18" fill="url(#cardGradDark)" stroke="#065f46" stroke-width="1.5" filter="url(#shadow)"/>
    <rect x="25" y="-12" width="280" height="24" rx="6" fill="#022c22" stroke="#10b981" stroke-width="1"/>
    <text x="165" y="4" text-anchor="middle" font-size="12" font-weight="800" fill="#a7f3d0">⚙️ EVENT-DRIVEN DOMAIN CORE SUBSYSTEMS</text>

    <!-- Subsystem 1: Inventory -->
    <g transform="translate(25, 25)">
      <rect x="0" y="0" width="245" height="125" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.2"/>
      <text x="20" y="30" font-size="13" font-weight="800" fill="#38bdf8">📦 Inventory Subsystem</text>
      <text x="20" y="52" font-size="11" fill="#94a3b8">• Baseline &amp; Delta Math (Δ)</text>
      <text x="20" y="70" font-size="11" fill="#94a3b8">• Invariant Checks &amp; Validation</text>
      <text x="20" y="88" font-size="11" fill="#94a3b8">• Immutable InventoryState</text>
      <rect x="15" y="98" width="215" height="18" rx="4" fill="#082f49"/>
      <text x="122" y="111" text-anchor="middle" font-size="10" font-weight="600" fill="#7dd3fc">Output: InventoryEvent</text>
    </g>

    <!-- Arrow Sub 1 -> 2 -->
    <path d="M 275 88 L 295 88" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#arrowEmerald)" />

    <!-- Subsystem 2: OCR -->
    <g transform="translate(300, 25)">
      <rect x="0" y="0" width="245" height="125" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.2"/>
      <text x="20" y="30" font-size="13" font-weight="800" fill="#a855f7">🔍 OCR Subsystem</text>
      <text x="20" y="52" font-size="11" fill="#94a3b8">• CLAHE Contrast Equalization</text>
      <text x="20" y="70" font-size="11" fill="#94a3b8">• EasyOCR Packaging Text</text>
      <text x="20" y="88" font-size="11" fill="#94a3b8">• Medicine Entity Parser</text>
      <rect x="15" y="98" width="215" height="18" rx="4" fill="#3b0764"/>
      <text x="122" y="111" text-anchor="middle" font-size="10" font-weight="600" fill="#d8b4fe">Output: MedicineIdentity</text>
    </g>

    <!-- Arrow Sub 2 -> 3 -->
    <path d="M 550 88 L 570 88" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#arrowEmerald)" />

    <!-- Subsystem 3: Clinical Engine -->
    <g transform="translate(575, 25)">
      <rect x="0" y="0" width="250" height="125" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.2"/>
      <text x="20" y="30" font-size="13" font-weight="800" fill="#f59e0b">⚖️ Clinical Decision Engine</text>
      <text x="20" y="52" font-size="11" fill="#94a3b8">• Prescription Schedule Match</text>
      <text x="20" y="70" font-size="11" fill="#94a3b8">• Grace Period Evaluation</text>
      <text x="20" y="88" font-size="11" fill="#94a3b8">• CORRECT / MISSED / EXTRA</text>
      <rect x="15" y="98" width="220" height="18" rx="4" fill="#451a03"/>
      <text x="125" y="111" text-anchor="middle" font-size="10" font-weight="600" fill="#fde68a">Output: ComplianceDecision</text>
    </g>

    <!-- Arrow Sub 3 -> 4 -->
    <path d="M 830 88 L 850 88" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#arrowEmerald)" />

    <!-- Subsystem 4: Alerting -->
    <g transform="translate(855, 25)">
      <rect x="0" y="0" width="220" height="125" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1.2"/>
      <text x="20" y="30" font-size="13" font-weight="800" fill="#f43f5e">🚨 Alert Engine</text>
      <text x="20" y="52" font-size="11" fill="#94a3b8">• Severity Matrix Routing</text>
      <text x="20" y="70" font-size="11" fill="#94a3b8">• Caregiver SMS &amp; Push</text>
      <text x="20" y="88" font-size="11" fill="#94a3b8">• Hardware Buzzer Alarm</text>
      <rect x="15" y="98" width="190" height="18" rx="4" fill="#4c0519"/>
      <text x="110" y="111" text-anchor="middle" font-size="10" font-weight="600" fill="#fecdd3">Output: AlertMessage[]</text>
    </g>
  </g>

  <!-- Flow 3 -> 4 -->
  <path d="M 600 685 L 600 720" fill="none" stroke="#a855f7" stroke-width="2.5" marker-end="url(#arrowPurple)" />

  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <!-- TIER 4: SERVICE & PERSISTENCE LAYER -->
  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <g transform="translate(50, 725)">
    <rect x="0" y="0" width="1100" height="150" rx="18" fill="url(#cardGradDark)" stroke="#6b21a8" stroke-width="1.5" filter="url(#shadow)"/>
    <rect x="25" y="-12" width="250" height="24" rx="6" fill="#3b0764" stroke="#a855f7" stroke-width="1"/>
    <text x="150" y="4" text-anchor="middle" font-size="12" font-weight="800" fill="#f3e8ff">🌐 BACKEND &amp; PERSISTENCE LAYER</text>

    <!-- FastAPI Box -->
    <g transform="translate(30, 25)">
      <rect x="0" y="0" width="500" height="105" rx="12" fill="#0f172a" stroke="#009688" stroke-width="1.2"/>
      <text x="25" y="32" font-size="14" font-weight="800" fill="#2dd4bf">⚡ FastAPI REST API Server (Port 8000)</text>
      <text x="25" y="56" font-size="11" fill="#cbd5e1">• Core AI Endpoints: /api/v1/devices/{id}/inspection, /health</text>
      <text x="25" y="74" font-size="11" fill="#cbd5e1">• Management Endpoints: /patients, /devices, /medications, /alerts</text>
      <text x="25" y="92" font-size="11" fill="#94a3b8">• Resilient Fast Fallback &amp; Thread-Safe Cache Architecture</text>
    </g>

    <!-- MongoDB Box -->
    <g transform="translate(570, 25)">
      <rect x="0" y="0" width="500" height="105" rx="12" fill="#0f172a" stroke="#16a34a" stroke-width="1.2"/>
      <text x="25" y="32" font-size="14" font-weight="800" fill="#4ade80">🍃 MongoDB Atlas (8 Persistent Collections)</text>
      <text x="25" y="56" font-size="11" fill="#cbd5e1">• patients, devices, prescriptions, daily_schedule</text>
      <text x="25" y="74" font-size="11" fill="#cbd5e1">• inspection_sessions, clinical_decisions, alerts, medicine_catalogue</text>
      <text x="25" y="92" font-size="11" fill="#94a3b8">• TLS Encrypted, Replica Set Resilient Persistence</text>
    </g>
  </g>

  <!-- Flow 4 -> 5 -->
  <path d="M 600 875 L 600 910" fill="none" stroke="#06b6d4" stroke-width="2.5" marker-end="url(#arrowCyan)" />

  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <!-- TIER 5: PRESENTATION & MONITORING -->
  <!-- ═══════════════════════════════════════════════════════════════════════════ -->
  <g transform="translate(50, 915)">
    <rect x="0" y="0" width="1100" height="135" rx="18" fill="url(#cardGradDark)" stroke="#0284c7" stroke-width="1.5" filter="url(#shadow)"/>
    <rect x="25" y="-12" width="290" height="24" rx="6" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
    <text x="170" y="4" text-anchor="middle" font-size="12" font-weight="800" fill="#bae6fd">🖥️ PRESENTATION &amp; MONITORING APPS</text>

    <!-- React/Vite UI -->
    <g transform="translate(30, 22)">
      <rect x="0" y="0" width="500" height="95" rx="12" fill="#0f172a" stroke="#0284c7" stroke-width="1.2"/>
      <text x="25" y="30" font-size="14" font-weight="800" fill="#38bdf8">⚛️ React + Vite Telemetry Dashboard (Port 5173)</text>
      <text x="25" y="52" font-size="11" fill="#cbd5e1">• Real-time Ward Monitoring, AI Scanner &amp; Verification Queue</text>
      <text x="25" y="70" font-size="11" fill="#cbd5e1">• Patient Demographics, Devices &amp; Dynamic Schedule Engine</text>
    </g>

    <!-- Streamlit Apps -->
    <g transform="translate(570, 22)">
      <rect x="0" y="0" width="500" height="95" rx="12" fill="#0f172a" stroke="#ef4444" stroke-width="1.2"/>
      <text x="25" y="30" font-size="14" font-weight="800" fill="#f87171">📊 Streamlit Developer Suite (Apps 01 - 10)</text>
      <text x="25" y="52" font-size="11" fill="#cbd5e1">• Visual Subsystem Isolations, Trace Inspector &amp; Live Demo</text>
      <text x="25" y="70" font-size="11" fill="#cbd5e1">• Hospital Analytics &amp; Blind Dataset Benchmark Portal</text>
    </g>
  </g>

</svg>
"""

os.makedirs("docs", exist_ok=True)
with open("docs/architecture.svg", "w", encoding="utf-8") as f:
    f.write(svg_content)

print("Created docs/architecture.svg successfully!")
