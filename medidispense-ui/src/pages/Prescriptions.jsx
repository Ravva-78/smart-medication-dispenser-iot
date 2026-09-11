import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../services/apiClient";
import ActionBtn from "../components/ActionBtn";
import FormField from "../components/FormField";
import { ModalShell, ModalHeader, ModalRow } from "../components/ModalShell";
import ConfirmDialog from "../components/ConfirmDialog";
import SortableHeader from "../components/SortableHeader";
import FilterPills from "../components/FilterPills";
import { useTableControls } from "../hooks/useTableControls";
import { notifier } from "../services/NotificationService";

const STATUS_MAP = {
  Active: { color: "var(--green)", bg: "rgba(39,174,96,0.08)", border: "rgba(39,174,96,0.20)" },
  Completed: { color: "var(--cyan)", bg: "rgba(58,141,255,0.08)", border: "rgba(58,141,255,0.20)" },
  Cancelled: { color: "var(--orange)", bg: "rgba(230,126,34,0.08)", border: "rgba(230,126,34,0.20)" },
  Inactive: { color: "var(--text-muted)", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.20)" },
};

const emptyForm = {
  patientId: "",
  medication: "",
  dosage: "500mg",
  frequency: "Once daily",
  doctor: "",
};

function SelectField({ label, value, onChange, children, error }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label style={{
        fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
        letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase",
      }}>
        {label}
        {error && <span style={{ color: "#E74C3C", marginLeft: 4 }}>*</span>}
      </label>
      <select
        value={value}
        onChange={onChange}
        style={{
          padding: "9px 12px",
          borderRadius: "var(--radius-sm)",
          border: `1px solid ${error ? "#E74C3C" : "var(--border-soft)"}`,
          background: "var(--bg-void)",
          fontFamily: "var(--font-body)",
          fontSize: 13,
          color: "var(--text-primary)",
          outline: "none",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        {children}
      </select>
    </div>
  );
}

function ViewModal({ prescription, onClose }) {
  if (!prescription) return null;
  const s = STATUS_MAP[prescription.status] || STATUS_MAP.Active;
  return (
    <ModalShell onClose={onClose} maxWidth={440}>
      <ModalHeader title="Prescription Details" sub="Read-only record" onClose={onClose} />
      <ModalRow label="Rx ID">{prescription.id}</ModalRow>
      <ModalRow label="Patient">{prescription.patientName} ({prescription.patientId})</ModalRow>
      <ModalRow label="Medication">{prescription.medication}</ModalRow>
      <ModalRow label="Dosage">{prescription.dosage}</ModalRow>
      <ModalRow label="Frequency">{prescription.frequency}</ModalRow>
      <ModalRow label="Duration">{prescription.startDate || "Today"} to {prescription.endDate || "Ongoing"}</ModalRow>
      <ModalRow label="Doctor">{prescription.doctor || "Not assigned"}</ModalRow>
      <ModalRow label="Status">
        <span style={{
          color: s.color, background: s.bg, border: `1px solid ${s.border}`,
          padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600, display: "inline-block",
        }}>
          {prescription.status}
        </span>
      </ModalRow>
      <div style={{ marginTop: 24, display: "flex", justifyContent: "flex-end" }}>
        <button onClick={onClose} style={{
          padding: "9px 28px", borderRadius: "var(--radius-sm)", border: "none", background: "var(--cyan)",
          fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600, color: "#fff", cursor: "pointer",
        }}>
          Close
        </button>
      </div>
    </ModalShell>
  );
}

function AddModal({ patients, initialPatientId, onSave, onClose }) {
  const [formData, setFormData] = useState({ ...emptyForm, patientId: initialPatientId || "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    if (!formData.patientId || !formData.medication.trim()) {
      setError("Select a patient and enter medication.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave(formData);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalShell onClose={onClose} maxWidth={480} gap={18}>
      <ModalHeader title="Add Prescription" sub="Link medication to a patient" onClose={onClose} />
      <SelectField
        label="Patient"
        value={formData.patientId}
        onChange={e => setFormData({ ...formData, patientId: e.target.value })}
        error={error && !formData.patientId}
      >
        <option value="">-- Select Patient --</option>
        {patients.map(p => (
          <option key={p.id} value={p.id}>{p.name} - {p.id}</option>
        ))}
      </SelectField>
      <FormField
        label="Medication"
        value={formData.medication}
        onChange={e => setFormData({ ...formData, medication: e.target.value })}
        placeholder="Paracetamol"
        error={error && !formData.medication.trim()}
      />
      <FormField label="Dosage" value={formData.dosage} onChange={e => setFormData({ ...formData, dosage: e.target.value })} />
      <FormField label="Frequency" value={formData.frequency} onChange={e => setFormData({ ...formData, frequency: e.target.value })} />
      <FormField label="Doctor" value={formData.doctor} onChange={e => setFormData({ ...formData, doctor: e.target.value })} />
      {error && <div style={{ color: "#E74C3C", fontSize: 12 }}>{error}</div>}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button onClick={onClose} disabled={saving} style={{ padding: "9px 20px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-soft)", background: "var(--bg-overlay)", color: "var(--text-secondary)", cursor: "pointer" }}>
          Cancel
        </button>
        <button onClick={handleSave} disabled={saving} style={{ padding: "9px 24px", borderRadius: "var(--radius-sm)", border: "none", background: "var(--cyan)", color: "#fff", cursor: "pointer", fontWeight: 700 }}>
          {saving ? "Creating..." : "+ Create"}
        </button>
      </div>
    </ModalShell>
  );
}

function EditModal({ prescription, onSave, onClose }) {
  const [formData, setFormData] = useState({ ...prescription });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await onSave(formData);
    setSaving(false);
  };

  return (
    <ModalShell onClose={onClose} maxWidth={480} gap={20}>
      <ModalHeader title="Edit Prescription" sub={`${prescription.id} - MEDI-DISPENSE`} onClose={onClose} />
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <FormField label="Medication" value={formData.medication} onChange={e => setFormData({ ...formData, medication: e.target.value })} />
        <FormField label="Dosage" value={formData.dosage} onChange={e => setFormData({ ...formData, dosage: e.target.value })} />
        <FormField label="Frequency" value={formData.frequency} onChange={e => setFormData({ ...formData, frequency: e.target.value })} />
        <FormField label="Status" value={formData.status} onChange={e => setFormData({ ...formData, status: e.target.value })} />
      </div>
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 20 }}>
        <button onClick={onClose} disabled={saving} style={{ padding: "9px 20px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-soft)", background: "var(--bg-overlay)", color: "var(--text-secondary)", cursor: "pointer" }}>
          Cancel
        </button>
        <button onClick={handleSave} disabled={saving} style={{ padding: "9px 24px", borderRadius: "var(--radius-sm)", border: "none", background: "var(--teal)", color: "#fff", cursor: "pointer" }}>
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </ModalShell>
  );
}

export default function Prescriptions() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [viewing, setViewing] = useState(null);
  const [editing, setEditing] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [adding, setAdding] = useState(false);

  const fetchPrescriptions = useCallback(async () => {
    setLoading(true);
    try {
      const [rxData, patientData] = await Promise.all([
        apiClient.get("/prescriptions"),
        apiClient.get("/patients"),
      ]);
      setPrescriptions(rxData);
      setPatients(patientData);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPrescriptions(); }, [fetchPrescriptions]);

  const handleCreate = async (data) => {
    await apiClient.post("/prescriptions", data);
    await fetchPrescriptions();
    setAdding(false);
    notifier.success("Prescription added");
  };

  const handleUpdate = async (data) => {
    try {
      await apiClient.put(`/prescriptions/${data.id}`, data);
      await fetchPrescriptions();
      setEditing(null);
      notifier.success("Prescription updated");
    } catch (err) {
      notifier.error(err.message);
    }
  };

  const handleDelete = async () => {
    try {
      await apiClient.delete(`/prescriptions/${deleting.id}`);
      await fetchPrescriptions();
      setDeleting(null);
      notifier.success("Prescription deleted");
    } catch (err) {
      notifier.error(err.message);
    }
  };

  const { search, setSearch, activeFilter, setFilter, sort, toggleSort, paginated, filtered } = useTableControls(prescriptions, {
    searchFields: ["id", "patientName", "medication", "doctor"],
    filterField: "status",
    sortDefault: { field: "id", dir: "asc" },
    pageSize: 8,
    storageKey: "prescriptions",
  });

  const active = prescriptions.filter(p => p.status === "Active").length;
  const completed = prescriptions.filter(p => p.status === "Completed").length;

  return (
    <main className="main-content">
      {viewing && <ViewModal prescription={viewing} onClose={() => setViewing(null)} />}
      {adding && <AddModal patients={patients} initialPatientId={patients[0]?.id} onSave={handleCreate} onClose={() => setAdding(false)} />}
      {editing && <EditModal prescription={editing} onSave={handleUpdate} onClose={() => setEditing(null)} />}
      {deleting && <ConfirmDialog title="Delete Prescription" message={`Delete ${deleting.id}? This cannot be undone.`} onConfirm={handleDelete} onCancel={() => setDeleting(null)} />}

      <header className="dash-header">
        <div className="dash-header-left">
          <span className="breadcrumb">MEDI-DISPENSE</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Prescriptions</span>
        </div>
        <button
          onClick={() => setAdding(true)}
          style={{ border: "none", borderRadius: "var(--radius-sm)", background: "var(--cyan)", color: "#fff", padding: "9px 18px", fontWeight: 700, cursor: "pointer" }}
        >
          + Add Prescription
        </button>
      </header>

      <section className="page-hero">
        <h1 className="page-title">Prescription Management</h1>
        <p className="page-sub">Manage active prescriptions and clinical orders.</p>
      </section>

      <div className="page-content">
        <div style={{ marginBottom: 16 }}>
          <FilterPills options={["Active", "Completed", "Cancelled"]} active={activeFilter} onChange={setFilter} counts={{ Active: active, Completed: completed }} />
        </div>
        <div className="page-search-bar">
          <input className="page-search-input" type="text" placeholder="Search by patient, med, or ID..." value={search} onChange={e => setSearch(e.target.value)} />
          {search && <button className="page-search-clear" onClick={() => setSearch("")}>x</button>}
        </div>

        <div className="page-table-card">
          <table className="page-table">
            <thead>
              <tr>
                <SortableHeader field="id" label="Rx ID" sort={sort} onSort={toggleSort} />
                <SortableHeader field="patientName" label="Patient" sort={sort} onSort={toggleSort} />
                <SortableHeader field="medication" label="Medication" sort={sort} onSort={toggleSort} />
                <SortableHeader field="dosage" label="Dosage" sort={sort} onSort={toggleSort} />
                <SortableHeader field="status" label="Status" sort={sort} onSort={toggleSort} />
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="6" className="page-table-loading"><span className="spinner" /> Loading prescriptions...</td></tr>}
              {!loading && filtered.length === 0 && <tr><td colSpan="6" className="page-table-empty">No matching prescriptions.</td></tr>}
              {!loading && paginated.map(p => {
                const s = STATUS_MAP[p.status] || STATUS_MAP.Active;
                return (
                  <tr key={p.id} className="page-table-row">
                    <td className="page-table-id">{p.id}</td>
                    <td className="page-table-name">{p.patientName}</td>
                    <td>{p.medication}</td>
                    <td className="page-table-mono">{p.dosage}</td>
                    <td><span className="page-status-chip" style={{ color: s.color, background: s.bg, border: `1px solid ${s.border}` }}>{p.status}</span></td>
                    <td>
                      <div className="page-actions">
                        <ActionBtn label="View" variant="view" aria-label={`View ${p.id}`} onClick={() => setViewing(p)} />
                        <ActionBtn label="Edit" variant="edit" aria-label={`Edit ${p.id}`} onClick={() => setEditing(p)} />
                        <ActionBtn label="Delete" variant="delete" aria-label={`Delete ${p.id}`} onClick={() => setDeleting(p)} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
