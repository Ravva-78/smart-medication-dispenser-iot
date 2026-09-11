import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../services/apiClient";
import SortableHeader from "../components/SortableHeader";
import { useTableControls } from "../hooks/useTableControls";

export default function DispensingMonitor() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get('/dispense');
      setJobs(data);
    } catch (e) {
      console.error(e);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const { search, setSearch, sort, toggleSort, paginated, filtered } = useTableControls(jobs, {
    searchFields: ["patient", "medication", "device"], sortDefault: { field: "time", dir: "asc" }, pageSize: 12, storageKey: "dispense",
  });

  return (
    <main className="main-content">
      <header className="dash-header">
        <div className="dash-header-left">
          <span className="breadcrumb">MEDI-DISPENSE</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Dispensing Queue</span>
        </div>
      </header>
      <section className="page-hero">
        <h1 className="page-title">Dispensing Monitor</h1>
        <p className="page-sub">Upcoming automated dispensing jobs.</p>
      </section>
      <div className="page-content">
        <div className="page-search-bar">
          <input className="page-search-input" type="text" placeholder="Search by patient, device..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="page-table-card">
          <table className="page-table">
            <thead>
              <tr>
                <SortableHeader field="time" label="Time" sort={sort} onSort={toggleSort} />
                <SortableHeader field="patient" label="Patient" sort={sort} onSort={toggleSort} />
                <SortableHeader field="medication" label="Medication" sort={sort} onSort={toggleSort} />
                <SortableHeader field="device" label="Device" sort={sort} onSort={toggleSort} />
                <SortableHeader field="ward" label="Ward" sort={sort} onSort={toggleSort} />
                <SortableHeader field="status" label="Status" sort={sort} onSort={toggleSort} />
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="6" className="page-table-loading"><span className="spinner" /> Loading jobs…</td></tr>}
              {!loading && filtered.length === 0 && <tr><td colSpan="6" className="page-table-empty">No jobs found.</td></tr>}
              {!loading && paginated.map(j => (
                <tr key={j.id} className="page-table-row">
                  <td className="page-table-mono">{j.time}</td>
                  <td className="page-table-name">{j.patient}</td>
                  <td>{j.medication}</td>
                  <td className="page-table-mono">{j.device}</td>
                  <td><span className="page-ward-chip">{j.ward}</span></td>
                  <td><span className="page-status-chip">{j.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
