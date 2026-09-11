import { useState, useEffect } from "react";
import { apiClient } from "../services/apiClient";
import SortableHeader from "../components/SortableHeader";
import { useTableControls } from "../hooks/useTableControls";

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const data = await apiClient.get('/reports');
      setReports(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (type) => {
    setGenerating(true);
    try {
      await apiClient.post('/reports/generate', { type });
      await loadReports();
    } catch (e) {
      console.error(e);
    } finally {
      setGenerating(false);
    }
  };

  const { sort, toggleSort, filtered } = useTableControls(reports, {
    searchFields: ["id", "type", "status"],
    sortDefault: { field: "generatedAt", dir: "desc" },
    storageKey: "reports"
  });

  return (
    <main className="main-content page-main">
      <header className="dash-header">
        <div className="dash-header-left">
          <span className="breadcrumb">MEDI-DISPENSE</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Reports</span>
        </div>
        <div className="dash-header-right">
          <button 
            type="button" 
            className="page-add-btn" 
            onClick={() => handleGenerate("System Summary")}
            disabled={generating}
          >
            + Generate Report
          </button>
        </div>
      </header>

      <div style={{ padding: "0 24px" }}>
        <div className="table-card">
          <div className="table-header">
            <h2>Generated Reports</h2>
          </div>
          
          <div className="table-wrap">
            {loading ? (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>Loading...</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <SortableHeader label="Report ID" field="id" sort={sort} onSort={toggleSort} />
                    <SortableHeader label="Type" field="type" sort={sort} onSort={toggleSort} />
                    <SortableHeader label="Generated" field="generatedAt" sort={sort} onSort={toggleSort} />
                    <SortableHeader label="Format" field="format" sort={sort} onSort={toggleSort} />
                    <SortableHeader label="Status" field="status" sort={sort} onSort={toggleSort} />
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="empty-state">No reports found.</td>
                    </tr>
                  ) : (
                    filtered.map(report => (
                      <tr key={report.id}>
                        <td>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600 }}>{report.id}</div>
                        </td>
                        <td>{report.type}</td>
                        <td style={{ color: "var(--text-secondary)" }}>
                          {new Date(report.generatedAt).toLocaleString()}
                        </td>
                        <td>{report.format}</td>
                        <td>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            padding: '4px 8px',
                            borderRadius: 'var(--radius-xs)',
                            fontSize: 11,
                            fontWeight: 600,
                            backgroundColor: report.status === 'Ready' ? 'rgba(74, 163, 162, 0.1)' : 'rgba(230, 126, 34, 0.1)',
                            color: report.status === 'Ready' ? 'var(--teal)' : 'var(--orange)'
                          }}>
                            {report.status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
