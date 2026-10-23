/**
 * ReverseSidePanel — Stage B of the single-camera, two-stage inspection.
 *
 * Stage A (the front-side scan: pockets, tablets, baseline, verification) is finished before this panel is
 * shown and is never read or changed here. This panel only reads the printed label on the back of the blister
 * (POST /api/v1/ocr/reverse-side) and asks the operator to Confirm or Reject the text.
 *
 * Nothing is saved: the captured image, OCR text and the operator's decision live in this component only.
 * The session / scan ids are props shown for reference; persisting them would need a (not yet approved) schema change.
 */
import { useState, useEffect, useRef } from "react";
import { fetchCameraFrame, beginExclusive, endExclusive } from "./cameraCapture";

const CARD = { background: "var(--surface-1,#162032)", border: "1px solid var(--border-dim,#2a3a4a)", borderRadius: 12, padding: 18 };
const LABEL = { fontSize: 11, fontWeight: 700, color: "var(--text-muted,#8899aa)", textTransform: "uppercase", letterSpacing: ".1em" };
const MUTED = { color: "var(--text-muted,#8899aa)", fontSize: 12, lineHeight: 1.5 };
const BTN = { padding: "9px 14px", borderRadius: 8, border: "none", fontWeight: 700, cursor: "pointer", color: "#fff", fontSize: 13 };

const STATUS = {
  READABLE:  { color: "#22c55e", text: "Text found, confidence at or above the OCR floor (70%). Still check it: OCR confuses similar characters such as 0/O and 5/S." },
  UNCERTAIN: { color: "#f59e0b", text: "Low confidence. Treat the text as a guess and retake the photo if you can." },
  NO_TEXT:   { color: "#ef4444", text: "No text was found. Check focus, lighting and that the printed side faces the camera." },
};

async function errorText(res, fallback) {
  try {
    const d = (await res.json()).detail;
    return (d && d.message) || (typeof d === "string" ? d : `${fallback} (HTTP ${res.status}).`);
  } catch {
    return `${fallback} (HTTP ${res.status}).`;
  }
}

export default function ReverseSidePanel({ apiUrl, sessionId, scanNo }) {
  const [step, setStep] = useState("idle");        // idle | flip | working | review | restore
  const [phase, setPhase] = useState("");          // Capturing… | Reading text…
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState("");
  const [ocr, setOcr] = useState(null);
  const [imgUrl, setImgUrl] = useState(null);
  const [decision, setDecision] = useState(null);  // confirmed | rejected | null
  const abortRef = useRef(null);
  const fileRef = useRef(null);

  const clearImage = () => setImgUrl(prev => { if (prev) URL.revokeObjectURL(prev); return null; });

  // A new front-side scan starts a new inspection: forget any earlier reverse-side result.
  useEffect(() => {
    if (abortRef.current) abortRef.current.abort();
    setStep("idle"); setOcr(null); setDecision(null); setError(""); clearImage();
  }, [sessionId]);

  useEffect(() => () => { if (abortRef.current) abortRef.current.abort(); }, []);

  useEffect(() => {
    if (step !== "working") return;
    setElapsed(0);
    const t = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(t);
  }, [step]);

  const readLabel = async (getBlob) => {
    setError(""); setOcr(null); setDecision(null); setStep("working");
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const blob = await getBlob(ctrl.signal);
      clearImage();
      setImgUrl(URL.createObjectURL(blob));
      setPhase("Reading text…");
      const fd = new FormData();
      fd.append("file", blob, "reverse_side.jpg");
      if (sessionId) fd.append("session_id", sessionId);
      if (scanNo) fd.append("scan_no", String(scanNo));
      const res = await fetch(`${apiUrl}/api/v1/ocr/reverse-side`, { method: "POST", body: fd, signal: ctrl.signal });
      if (!res.ok) throw new Error(await errorText(res, "Reading the label failed"));
      setOcr(await res.json());
      setStep("review");
    } catch (e) {
      if (e.name === "AbortError") return;
      setError(e.message || "Reverse-side capture failed.");
      setStep("flip");
    }
  };

  const captureFromCamera = () => {
    setPhase("Capturing…");
    return readLabel(async (signal) => {
      beginExclusive();   // the live preview pauses (and drops any request in flight) while this capture runs
      try {
        return await fetchCameraFrame(apiUrl, { signal, exclusive: true });
      } finally {
        endExclusive();
      }
    });
  };

  const handleUploadedFile = (e) => {
    const f = e.target.files && e.target.files[0];
    e.target.value = "";
    if (!f) return;
    if (!/^image\/(jpeg|png|webp)$/.test(f.type) || f.size > 5 * 1024 * 1024) {
      setError("Choose a JPG, PNG or WEBP image up to 5 MB.");
      return;
    }
    setPhase("Reading text…");
    readLabel(async () => f);
  };

  const cancel = () => {
    if (abortRef.current) abortRef.current.abort();
    setStep("flip");
  };

  const decide = (d) => {
    setDecision(d);
    if (d === "rejected") { setOcr(null); clearImage(); }
    setStep("restore");
  };

  const meta = ocr ? STATUS[ocr.ocr_status] || STATUS.UNCERTAIN : null;
  const cand = ocr && ocr.candidates
    ? [["Medicine", ocr.candidates.medicine_name], ["Strength", ocr.candidates.strength], ["Batch", ocr.candidates.batch_number],
       ["Expiry", ocr.candidates.expiry_date], ["Manufacturer", ocr.candidates.manufacturer]].filter(([, v]) => v)
    : [];

  return (
    <div style={CARD}>
      <div style={{ ...LABEL, marginBottom: 6 }}>Reverse-side label (Stage B)</div>
      <div style={{ ...MUTED, marginBottom: 12 }}>
        Optional second capture with the same camera. It only reads the printed label: it never changes the front-side
        pocket counts, tablet counts or verification shown above, and nothing here is saved.
        {scanNo ? ` Linked to scan #${scanNo}` : ""}{sessionId ? ` · session ${sessionId}` : ""}.
      </div>

      {step === "idle" && (
        <>
          {decision === "confirmed" && ocr && (
            <div style={{ ...MUTED, marginBottom: 10, padding: "8px 12px", background: "var(--surface-2,#1e2a3a)", borderRadius: 8 }}>
              <strong style={{ color: "#22c55e" }}>Last reverse-side check: text confirmed by operator</strong> (kept on this page only, not saved).
              <pre style={{ margin: "6px 0 0", whiteSpace: "pre-wrap", color: "var(--text-primary,#e8f0fe)", fontSize: 12 }}>{ocr.text}</pre>
            </div>
          )}
          {decision === "rejected" && (
            <div style={{ ...MUTED, marginBottom: 10 }}>Last reverse-side check: text rejected and discarded.</div>
          )}
          <button onClick={() => { setError(""); setStep("flip"); }} style={{ ...BTN, background: "#0080ff" }}>
            ↻ {decision ? "Check reverse side again" : "Start reverse-side check"}
          </button>
        </>
      )}

      {step === "flip" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ padding: "12px 14px", borderRadius: 8, background: "rgba(245,158,11,.13)", border: "1px solid #f59e0b", color: "#f59e0b", fontWeight: 600, fontSize: 13 }}>
            Step 1 · Turn the blister over so the printed label faces the camera, then capture.
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={captureFromCamera} style={{ ...BTN, background: "#0080ff" }}>📸 Capture reverse side</button>
            <button onClick={() => fileRef.current && fileRef.current.click()} style={{ ...BTN, background: "transparent", border: "1px solid var(--border-dim,#2a3a4a)", color: "var(--text-muted,#8899aa)" }}>
              Upload a photo instead
            </button>
            <button onClick={() => { setError(""); setStep("idle"); }} style={{ ...BTN, background: "transparent", color: "var(--text-muted,#8899aa)" }}>Cancel</button>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handleUploadedFile} style={{ display: "none" }} />
          </div>
          <div style={MUTED}>The camera link can take 1–20 s per picture and sometimes drops a frame; retry if it fails.</div>
        </div>
      )}

      {step === "working" && (
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ color: "#00d4ff", fontWeight: 600, fontSize: 13 }}>{phase} {elapsed}s</div>
          <button onClick={cancel} style={{ ...BTN, background: "transparent", color: "var(--text-muted,#8899aa)" }}>Cancel</button>
        </div>
      )}

      {step === "review" && ocr && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            {imgUrl && <img src={imgUrl} alt="Reverse side" style={{ width: 150, maxHeight: 120, objectFit: "contain", borderRadius: 8, border: "1px solid var(--border-dim,#2a3a4a)" }} />}
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: meta.color }}>
                {ocr.ocr_status} · {Math.round((ocr.mean_confidence || 0) * 100)}% mean confidence
              </div>
              <div style={MUTED}>{meta.text}</div>
            </div>
          </div>

          <div style={{ background: "var(--surface-2,#1e2a3a)", borderRadius: 8, padding: "10px 12px" }}>
            <div style={{ ...LABEL, marginBottom: 4 }}>Text read from the label (unconfirmed)</div>
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "var(--font-mono, monospace)", fontSize: 12, color: "var(--text-primary,#e8f0fe)" }}>
              {ocr.text || "(nothing read)"}
            </pre>
          </div>

          {cand.length > 0 && (
            <div>
              <div style={{ ...LABEL, marginBottom: 4 }}>Possible fields (unconfirmed suggestions)</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 12 }}>
                {cand.map(([k, v]) => (
                  <div key={k} style={{ background: "var(--surface-2,#1e2a3a)", borderRadius: 8, padding: "6px 10px" }}>
                    <div style={{ fontSize: 10, color: "var(--text-muted,#8899aa)" }}>{k}</div>
                    <div style={{ color: "var(--text-primary,#e8f0fe)", fontWeight: 600 }}>{v}</div>
                  </div>
                ))}
              </div>
              <div style={{ ...MUTED, marginTop: 4 }}>Suggestions come from a fixed list of known names and may be wrong or missing. Compare with the packaging.</div>
            </div>
          )}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button onClick={() => decide("confirmed")} disabled={ocr.ocr_status === "NO_TEXT"}
              style={{ ...BTN, background: ocr.ocr_status === "NO_TEXT" ? "#2a3a4a" : "#16a34a", cursor: ocr.ocr_status === "NO_TEXT" ? "not-allowed" : "pointer" }}>
              ✓ Confirm: the text matches the label
            </button>
            <button onClick={() => decide("rejected")} style={{ ...BTN, background: "#dc2626" }}>✕ Reject</button>
            <button onClick={() => { setOcr(null); clearImage(); setStep("flip"); }} style={{ ...BTN, background: "transparent", border: "1px solid var(--border-dim,#2a3a4a)", color: "var(--text-muted,#8899aa)" }}>
              Retake
            </button>
          </div>
        </div>
      )}

      {step === "restore" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ ...MUTED }}>
            {decision === "confirmed" ? "Reverse-side text confirmed by the operator (not saved)." : "Reverse-side text rejected and discarded."}
          </div>
          <div style={{ padding: "12px 14px", borderRadius: 8, background: "rgba(245,158,11,.13)", border: "1px solid #f59e0b", color: "#f59e0b", fontWeight: 600, fontSize: 13 }}>
            Step 2 · Turn the blister back to its original orientation before the next scan.
          </div>
          <div>
            <button onClick={() => setStep("idle")} style={{ ...BTN, background: "#0080ff" }}>Done, blister turned back</button>
          </div>
        </div>
      )}

      {error && <div style={{ marginTop: 10, fontSize: 12, color: "#ef4444", lineHeight: 1.4 }}>⚠ {error}</div>}
    </div>
  );
}
