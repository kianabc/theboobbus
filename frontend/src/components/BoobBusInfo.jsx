import { useState, useEffect } from "react";
import "./BoobBusInfo.css";

const API = import.meta.env.VITE_API_URL ?? "";

function authHeaders() {
  const token = localStorage.getItem("google_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function BoobBusInfo({ onBack }) {
  const [info, setInfo] = useState("");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/boobbus-info`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((data) => {
        setInfo(data.info);
        setLoading(false);
      });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      const res = await fetch(`${API}/api/boobbus-info-update`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ info }),
      });
      if (res.ok) {
        setStatus({ type: "success", text: "Saved! AI will use this info for future emails." });
      } else {
        setStatus({ type: "error", text: "Failed to save" });
      }
    } catch {
      setStatus({ type: "error", text: "Failed to save" });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    // Delete the custom info to revert to default
    try {
      await fetch(`${API}/api/boobbus-info-update`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ info: "" }),
      });
      // Re-fetch to get default
      const res = await fetch(`${API}/api/boobbus-info`, { headers: authHeaders() });
      const data = await res.json();
      setInfo(data.info);
      setStatus({ type: "success", text: "Reset to default" });
    } catch {
      setStatus({ type: "error", text: "Failed to reset" });
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="boobbus-info">
      <button className="btn btn-secondary" onClick={onBack}>
        &larr; Back to dashboard
      </button>

      <div className="info-card">
        <h2>Boob Bus Information</h2>
        <p className="info-desc">
          This is the context that Claude AI uses when drafting outreach emails.
          Edit it to update facts, add new services, change pricing, or adjust the messaging.
          Everything here will be included in the AI's instructions.
        </p>

        <div className="info-tips">
          <strong>Tips:</strong> Include key stats, pricing, benefits, services offered,
          and any talking points you want in your emails. The more specific, the better
          the AI's emails will be.
        </div>

        <textarea
          className="info-editor"
          value={info}
          onChange={(e) => setInfo(e.target.value)}
          rows={20}
        />

        <div className="info-actions">
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
          <button className="btn btn-secondary" onClick={handleReset}>
            Reset to Default
          </button>
          {status && (
            <span className={`info-status ${status.type}`}>{status.text}</span>
          )}
        </div>
      </div>
    </div>
  );
}
