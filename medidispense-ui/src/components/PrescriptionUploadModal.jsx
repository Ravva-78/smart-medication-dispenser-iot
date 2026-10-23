/**
 * PrescriptionUploadModal — read text from an uploaded prescription (image or PDF) for a person to review.
 *
 * Flow: choose file -> preview -> "Read text" (POST /api/v1/prescriptions/extract) -> review/edit fields ->
 * tick "I have checked these details" -> "Continue" hands the reviewed values to the existing Add Prescription form.
 *
 * Nothing is saved here: the file, its text and the fields stay in this component. The extraction is OCR and can be
 * wrong; it never identifies a blister or tablet. Saving happens only if the operator presses Create in the
 * existing Add Prescription form (existing POST /prescriptions).
 */
import { useState, useEffect } from "react";
import { ModalShell, ModalHeader } from "./ModalShell";
import FormField from "./FormField";
import { ENV } from "../config/env";

const MAX_BYTES = 8 * 1024 * 1024;
const ACCEPT = "image/jpeg,image/png,image/webp,application/pdf";
const WARN = { color: "var(--orange)", bg: "rgba(230,126,34,0.08)", border: "rgba(230,126,34,0.20)" };
const LABEL = { fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700, letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase" };
const BTN = { padding: "9px 18px", borderRadius: "var(--radius-sm)", border: "none", fontWeight: 700, cursor: "pointer", color: "#fff" };

export default function PrescriptionUploadModal({ onUse, onClose }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [fields, setFields] = useState({ medication: "", dosage: "", frequency: "", doctor: "" });
  const [checked, setChecked] = useState(false);

  useEffect(() => () => { if (previewUrl) URL.revokeObjectURL(previewUrl); }, [previewUrl]);

  const pick = (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setResult(null); setChecked(false); setError("");
    if (!ACCEPT.split(",").includes(f.type)) { setFile(null); setPreviewUrl(null); setError("Choose a JPG, PNG, WEBP or PDF file."); return; }
    if (f.size > MAX_BYTES) { setFile(null); setPreviewUrl(null); setError("The file is larger than 8 MB."); return; }
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
  };

  const read = async () => {
    if (!file) return;
    setReading(true); setError(""); setResult(null); setChecked(false);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${ENV.API_URL}/api/v1/prescriptions/extract`, { method: "POST", body: fd });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail || `Could not read the file (HTTP ${res.status}).`);
      }
      setResult(await res.json());
    } catch (e) {
      setError(e.message || "Could not read the file.");
    } finally {
      setReading(false);
    }
  };

  const applyCandidate = (c) =>
    setFields(f => ({ ...f, medication: c.medicine_name, dosage: c.strength || f.dosage }));

  const canContinue = fields.medication.trim() && checked;

  return (
    <ModalShell onClose={onClose} maxWidth={640} gap={14}>
      <ModalHeader title="Upload Prescription" sub="Text is read by OCR · you review every field" onClose={onClose} />

      <div style={{ ...WARN, background: WARN.bg, border: `1px solid ${WARN.border}`, borderRadius: "var(--radius-sm)", padding: "10px 12px", fontSize: 12, lineHeight: 1.5 }}>
        <strong>Unconfirmed.</strong> OCR can misread letters and numbers. Compare everything with the document. A prescription
        does not identify any blister or tablet, and nothing is saved until you press Create in the next form.
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <span style={LABEL}>File (JPG, PNG, WEBP or PDF, up to 8 MB)</span>
        <input type="file" accept={ACCEPT} onChange={pick} />
      </div>

      {previewUrl && file && (
        <div style={{ border: "1px solid var(--border-soft)", borderRadius: "var(--radius-sm)", padding: 8, background: "var(--bg-void)" }}>
          {file.type === "application/pdf"
            ? <object data={previewUrl} type="application/pdf" width="100%" height="240" aria-label="PDF preview">PDF selected: {file.name}</object>
            : <img src={previewUrl} alt="Prescription preview" style={{ maxWidth: "100%", maxHeight: 240, display: "block", margin: "0 auto" }} />}
        </div>
      )}

      <div>
        <button onClick={read} disabled={!file || reading} style={{ ...BTN, background: !file || reading ? "var(--text-muted)" : "var(--cyan)" }}>
          {reading ? "Reading…" : "Read text"}
        </button>
      </div>

      {error && <div style={{ color: "#E74C3C", fontSize: 12 }}>⚠ {error}</div>}

      {result && (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={LABEL}>Text read from the document (unconfirmed)</span>
            <textarea readOnly value={result.text || "(nothing read)"} rows={5}
              style={{ padding: "9px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-soft)", background: "var(--bg-void)", color: "var(--text-primary)", fontFamily: "var(--font-mono)", fontSize: 12, resize: "vertical" }} />
            {result.pages_truncated && <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Only the first {result.pages_read} pages were read.</span>}
          </div>

          {result.candidates.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <span style={LABEL}>Medicines the reader recognised (suggestions only)</span>
              {result.candidates.map((c, i) => (
                <button key={i} onClick={() => applyCandidate(c)}
                  style={{ textAlign: "left", padding: "8px 12px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-soft)", background: "var(--bg-overlay)", color: "var(--text-primary)", cursor: "pointer", fontSize: 12 }}>
                  Use <strong>{c.medicine_name}</strong>{c.strength ? ` ${c.strength}` : ""} <span style={{ color: "var(--text-muted)" }}>— "{c.line}"</span>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {result.status === "NO_TEXT" ? "No text was found." : "No known medicine name was recognised."} Type the details yourself from the document below.
            </div>
          )}

          {result.dosage_lines.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={LABEL}>Lines that mention a dose or frequency</span>
              {result.dosage_lines.map((l, i) => <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)" }}>• {l}</div>)}
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 12, paddingTop: 6, borderTop: "1px solid var(--border-dim)" }}>
            <span style={LABEL}>Details to carry into Add Prescription (edit as needed)</span>
            <FormField label="Medication" value={fields.medication} onChange={e => setFields({ ...fields, medication: e.target.value })} placeholder="as written on the prescription" />
            <FormField label="Dosage" value={fields.dosage} onChange={e => setFields({ ...fields, dosage: e.target.value })} placeholder="e.g. 500mg" />
            <FormField label="Frequency" value={fields.frequency} onChange={e => setFields({ ...fields, frequency: e.target.value })} placeholder="e.g. Twice daily" />
            <FormField label="Doctor" value={fields.doctor} onChange={e => setFields({ ...fields, doctor: e.target.value })} />
            <label style={{ display: "flex", gap: 8, alignItems: "flex-start", fontSize: 12, color: "var(--text-secondary)" }}>
              <input type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)} style={{ marginTop: 2 }} />
              I have checked these details against the document.
            </label>
          </div>
        </>
      )}

      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{ ...BTN, background: "var(--bg-overlay)", border: "1px solid var(--border-soft)", color: "var(--text-secondary)", fontWeight: 400 }}>Cancel</button>
        {result && (
          <button onClick={() => onUse(fields)} disabled={!canContinue} style={{ ...BTN, background: canContinue ? "var(--cyan)" : "var(--text-muted)", cursor: canContinue ? "pointer" : "not-allowed" }}>
            Continue to Add Prescription
          </button>
        )}
      </div>
    </ModalShell>
  );
}
