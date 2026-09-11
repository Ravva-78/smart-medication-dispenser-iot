import { useState, useEffect } from "react";
import { apiClient } from "../services/apiClient";
import FormField from "../components/FormField";

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await apiClient.get('/settings');
      setSettings(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const res = await apiClient.put('/settings', settings);
      setMessage({ type: 'success', text: "Settings saved successfully." });
    } catch (e) {
      setMessage({ type: 'error', text: e.message || "Failed to save settings." });
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div style={{ padding: 24 }}>Loading settings...</div>;

  return (
    <main className="main-content page-main">
      <header className="dash-header">
        <div className="dash-header-left">
          <span className="breadcrumb">MEDI-DISPENSE</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-active">Settings</span>
        </div>
      </header>

      <div style={{ padding: "0 24px", maxWidth: 600 }}>
        <div className="table-card">
          <div className="table-header">
            <h2>Application Configuration</h2>
          </div>
          <div style={{ padding: 20 }}>
            {message && (
              <div style={{ 
                padding: 12, marginBottom: 20, borderRadius: 6, fontSize: 13,
                backgroundColor: message.type === 'error' ? 'rgba(231, 76, 60, 0.1)' : 'rgba(74, 163, 162, 0.1)',
                color: message.type === 'error' ? '#e74c3c' : '#4AA3A2' 
              }}>
                {message.text}
              </div>
            )}
            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <FormField 
                label="Hospital Name" 
                value={settings.hospitalName} 
                onChange={e => setSettings({...settings, hospitalName: e.target.value})} 
              />
              <FormField 
                label="Ward Count" 
                value={settings.wardCount} 
                type="number"
                onChange={e => setSettings({...settings, wardCount: Number(e.target.value)})} 
              />
              <FormField 
                label="Device Count" 
                value={settings.deviceCount} 
                type="number"
                onChange={e => setSettings({...settings, deviceCount: Number(e.target.value)})} 
              />
              
              <div style={{ height: 1, backgroundColor: "var(--border-dim)", margin: "10px 0" }} />
              
              <FormField 
                label="Critical Stock Threshold" 
                value={settings.alertThresholds.criticalStock} 
                type="number"
                onChange={e => setSettings({
                  ...settings, 
                  alertThresholds: { ...settings.alertThresholds, criticalStock: Number(e.target.value) }
                })} 
              />
              <FormField 
                label="Low Stock Threshold" 
                value={settings.alertThresholds.lowStock} 
                type="number"
                onChange={e => setSettings({
                  ...settings, 
                  alertThresholds: { ...settings.alertThresholds, lowStock: Number(e.target.value) }
                })} 
              />

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 20 }}>
                <button type="submit" disabled={saving} style={{
                  padding: "9px 24px", borderRadius: "var(--radius-sm)",
                  border: "none", background: "var(--teal)",
                  fontFamily: "var(--font-body)", fontSize: 13, fontWeight: 600,
                  color: "#fff", cursor: saving ? "not-allowed" : "pointer",
                  opacity: saving ? 0.6 : 1
                }}>
                  {saving ? "Saving..." : "Save Settings"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
