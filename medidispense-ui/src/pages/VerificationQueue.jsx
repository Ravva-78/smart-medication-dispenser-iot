import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../services/apiClient";
import SortableHeader from "../components/SortableHeader";
import { useTableControls } from "../hooks/useTableControls";

export default function VerificationQueue() {
  const [verifications, setVerifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchVerifications = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get('/verifications');
      setVerifications(data);
    } catch (e) {
      console.error(e);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchVerifications(); }, [fetchVerifications]);

  const { search, setSearch, sort, toggleSort, paginated, filtered } = useTableControls(verifications, {
    searchFields: ["patient", "medication"], sortDefault: { field: "scheduledTime", dir: "asc" }, pageSize: 12, storageKey: "verifications",
  });

  return (
    <main className="main-content">
      <header className="dash-header">
        <div className="dash-header-left">
          <span className="breadcrumb">MEDI-DISPENSE</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Verification Queue</span>
        </div>
      </header>
      <section className="page-hero">
        <h1 className="page-title">Verification Queue</h1>
        <p className="page-sub">Pending CV flags and manual approvals.</p>
      </section>
      <div className="page-content">
        <div className="page-search-bar">
          <input className="page-search-input" type="text" placeholder="Search by patient, medication..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="page-table-card">
          <table className="page-table">
            <thead>
              <tr>
                <SortableHeader field="scheduledTime" label="Scheduled" sort={sort} onSort={toggleSort} />
                <SortableHeader field="patient" label="Patient" sort={sort} onSort={toggleSort} />
                <SortableHeader field="medication" label="Medication" sort={sort} onSort={toggleSort} />
                <SortableHeader field="deviceId" label="Device" sort={sort} onSort={toggleSort} />
                <SortableHeader field="priority" label="Priority" sort={sort} onSort={toggleSort} />
                <SortableHeader field="status" label="Status" sort={sort} onSort={toggleSort} />
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="6" className="page-table-loading"><span className="spinner" /> Loading queue…</td></tr>}
              {!loading && filtered.length === 0 && <tr><td colSpan="6" className="page-table-empty">Queue empty.</td></tr>}
              {!loading && paginated.map(v => (
                <tr key={v.id} className="page-table-row">
                  <td className="page-table-mono">{v.scheduledTime}</td>
                  <td className="page-table-name">{v.patient}</td>
                  <td>{v.medication}</td>
                  <td className="page-table-mono">{v.deviceId}</td>
                  <td>{v.priority}</td>
                  <td><span className="page-status-chip">{v.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
