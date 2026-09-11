import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../services/apiClient";
import SortableHeader from "../components/SortableHeader";
import { useTableControls } from "../hooks/useTableControls";
import FormField from "../components/FormField";
import { ModalShell, ModalHeader } from "../components/ModalShell";

export default function Schedules() {
  const [schedules, setSchedules] = useState([]);
  const [patients, setPatients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ patientId: "", minutesFromNow: "3" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const fetchSchedules = useCallback(async () => {
    setLoading(true);
    try {
      const [data, patientData] = await Promise.all([
        apiClient.get('/schedules'),
        apiClient.get('/patients'),
      ]);
      setSchedules(data);
      setPatients(Array.isArray(patientData) ? patientData : []);
    } catch (e) {
      console.error(e);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchSchedules(); }, [fetchSchedules]);

  const openAdd = () => {
    setForm({ patientId: patients[0]?.id || "", minutesFromNow: "3" });
    setError(null);
    setShowAdd(true);
  };

  const createSchedule = async (e) => {
    e.preventDefault();
    if (!form.patientId) {
      setError("Select a patient first.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await apiClient.post("/schedules", {
        patientId: form.patientId,
        minutesFromNow: form.minutesFromNow,
      });
      await fetchSchedules();
      setShowAdd(false);
    } catch (err) {
      setError(err.message || "Could not create schedule.");
    } finally {
      setSaving(false);
    }
  };

  const { search, setSearch, sort, toggleSort, paginated, filtered } = useTableControls(schedules, {
    searchFields: ["patient", "medication", "time"], sortDefault: { field: "time", dir: "asc" }, pageSize: 12, storageKey: "schedules",
  });

  return (
    <>
    {showAdd && (
      <ModalShell onClose={() => setShowAdd(false)} maxWidth={460} gap={18}>
        <ModalHeader title="Add Schedule" sub="Create an image scan schedule" onClose={() => setShowAdd(false)} />
        <form onSubmit={createSchedule} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label style={{
              fontFamily: "var(--font-mono)", fontSize: 9, fontWeight: 700,
              letterSpacing: "0.14em", color: "var(--text-muted)", textTransform: "uppercase",
            }}>
              Patient
            </label>
            <select
              value={form.patientId}
              onChange={e => setForm(prev => ({ ...prev, patientId: e.target.value }))}
              style={{
                padding: "9px 12px", borderRadius: "var(--radius-sm)",
                border: "1px solid var(--border-soft)", background: "var(--bg-void)",
                fontFamily: "var(--font-body)", fontSize: 13, color: "var(--text-primary)",
              }}
            >
              <option value="">Select patient</option>
              {patients.map(p => (
                <option key={p.id} value={p.id}>{p.name} - {p.id}</option>
              ))}
            </select>
          </div>

          <FormField
            label="Due in minutes"
            type="number"
            value={form.minutesFromNow}
            onChange={e => setForm(prev => ({ ...prev, minutesFromNow: e.target.value }))}
            placeholder="3"
          />

          {error && <div style={{ color: "#E74C3C", fontSize: 13 }}>{error}</div>}

          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <button type="button" onClick={() => setShowAdd(false)} className="page-add-btn" style={{ background: "var(--bg-overlay)", color: "var(--text-secondary)" }}>
              Cancel
            </button>
            <button type="submit" disabled={saving} className="page-add-btn">
              {saving ? "Creating..." : "+ Create"}
            </button>
          </div>
        </form>
      </ModalShell>
    )}

    <main className="main-content">
      <header className="dash-header">
        <div className="dash-header-left">
          <span className="breadcrumb">MEDI-DISPENSE</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Schedules</span>
        </div>
        <div className="dash-header-right">
          <button type="button" className="page-add-btn" onClick={openAdd}>
            + Add Schedule
          </button>
        </div>
      </header>
      <section className="page-hero">
        <h1 className="page-title">Medication Schedule</h1>
        <p className="page-sub">View upcoming, missed, and completed doses.</p>
      </section>
      <div className="page-content">
        <div className="page-search-bar">
          <input className="page-search-input" type="text" placeholder="Search by patient, time..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="page-table-card">
          <table className="page-table">
            <thead>
              <tr>
                <SortableHeader field="time" label="Time" sort={sort} onSort={toggleSort} />
                <SortableHeader field="patient" label="Patient" sort={sort} onSort={toggleSort} />
                <SortableHeader field="prescriptionId" label="Rx ID" sort={sort} onSort={toggleSort} />
                <SortableHeader field="medication" label="Medication" sort={sort} onSort={toggleSort} />
                <SortableHeader field="deviceId" label="Device" sort={sort} onSort={toggleSort} />
                <SortableHeader field="status" label="Status" sort={sort} onSort={toggleSort} />
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="6" className="page-table-loading"><span className="spinner" /> Loading schedules…</td></tr>}
              {!loading && filtered.length === 0 && <tr><td colSpan="6" className="page-table-empty">No schedules found.</td></tr>}
              {!loading && paginated.map(s => (
                <tr key={s.id} className="page-table-row">
                  <td className="page-table-mono">{s.time}</td>
                  <td className="page-table-name">{s.patient}</td>
                  <td className="page-table-id">{s.prescriptionId}</td>
                  <td>{s.medication}</td>
                  <td className="page-table-mono">{s.deviceId}</td>
                  <td><span className="page-status-chip">{s.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
    </>
  );
}
