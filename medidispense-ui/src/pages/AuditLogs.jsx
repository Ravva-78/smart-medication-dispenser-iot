import { useState, useEffect, useCallback } from "react";
import { apiClient } from "../services/apiClient";
import SortableHeader from "../components/SortableHeader";
import { useTableControls } from "../hooks/useTableControls";

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.get('/audits');
      setLogs(data);
    } catch (e) {
      console.error(e);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const { search, setSearch, sort, toggleSort, paginated, filtered } = useTableControls(logs, {
    searchFields: ["user", "module", "action", "result"], sortDefault: { field: "timestamp", dir: "desc" }, pageSize: 15, storageKey: "audits",
  });

  return (
    <main className="main-content">
      <header className="dash-header">
        <div className="dash-header-left">
          <span className="breadcrumb">MEDI-DISPENSE</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Audit Logs</span>
        </div>
      </header>
      <section className="page-hero">
        <h1 className="page-title">Audit Trail</h1>
        <p className="page-sub">Immutable log of system actions.</p>
      </section>
      <div className="page-content">
        <div className="page-search-bar">
          <input className="page-search-input" type="text" placeholder="Search by module, user..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <div className="page-table-card">
          <table className="page-table">
            <thead>
              <tr>
                <SortableHeader field="id" label="ID" sort={sort} onSort={toggleSort} />
                <SortableHeader field="timestamp" label="Timestamp" sort={sort} onSort={toggleSort} />
                <SortableHeader field="user" label="User" sort={sort} onSort={toggleSort} />
                <SortableHeader field="module" label="Module" sort={sort} onSort={toggleSort} />
                <SortableHeader field="action" label="Action" sort={sort} onSort={toggleSort} />
                <SortableHeader field="result" label="Result" sort={sort} onSort={toggleSort} />
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan="6" className="page-table-loading"><span className="spinner" /> Loading audits…</td></tr>}
              {!loading && filtered.length === 0 && <tr><td colSpan="6" className="page-table-empty">No audits found.</td></tr>}
              {!loading && paginated.map(a => (
                <tr key={a.id} className="page-table-row">
                  <td className="page-table-id">{a.id}</td>
                  <td className="page-table-mono">{new Date(a.timestamp).toLocaleString()}</td>
                  <td>{a.user}</td>
                  <td>{a.module}</td>
                  <td className="page-table-name">{a.action}</td>
                  <td><span className="page-status-chip">{a.result}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
