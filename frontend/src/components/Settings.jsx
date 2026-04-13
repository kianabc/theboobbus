import { useState, useEffect } from "react";
import { fetchSettings, updateSettings } from "../api";
import "./Settings.css";

export default function Settings({ onBack }) {
  const [followUpDays, setFollowUpDays] = useState(5);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings().then((data) => {
      setFollowUpDays(data.follow_up_days);
      setLoading(false);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      await updateSettings({ follow_up_days: followUpDays });
      setStatus({ type: "success", text: "Settings saved" });
    } catch {
      setStatus({ type: "error", text: "Failed to save" });
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="loading">Loading settings...</div>;

  return (
    <div className="settings">
      <button className="btn btn-secondary" onClick={onBack}>
        &larr; Back to dashboard
      </button>

      <div className="settings-card">
        <h2>Follow-up Settings</h2>
        <p className="settings-desc">
          Configure automatic follow-up behavior. When you send an outreach email,
          the system will check for replies and automatically send follow-ups if
          no response is received.
        </p>

        <div className="settings-field">
          <label>Days before follow-up</label>
          <div className="settings-input-row">
            <input
              type="number"
              min="1"
              max="30"
              value={followUpDays}
              onChange={(e) => setFollowUpDays(parseInt(e.target.value) || 5)}
            />
            <span className="settings-hint">days after sending</span>
          </div>
        </div>

        <div className="settings-field">
          <label>Email sequence</label>
          <div className="sequence-preview">
            <div className="sequence-step">
              <span className="step-num">1</span>
              <span className="step-label">Initial Outreach</span>
              <span className="step-timing">Day 0</span>
            </div>
            <div className="sequence-arrow">&darr;</div>
            <div className="sequence-step">
              <span className="step-num">2</span>
              <span className="step-label">Follow-up</span>
              <span className="step-timing">Day {followUpDays}</span>
            </div>
            <div className="sequence-arrow">&darr;</div>
            <div className="sequence-step">
              <span className="step-num">3</span>
              <span className="step-label">Final Check-in</span>
              <span className="step-timing">Day {followUpDays * 2}</span>
            </div>
            <div className="sequence-arrow">&darr;</div>
            <div className="sequence-step sequence-end">
              <span className="step-label">Stop (no more emails)</span>
            </div>
          </div>
        </div>

        <div className="settings-actions">
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : "Save Settings"}
          </button>
          {status && (
            <span className={`settings-status ${status.type}`}>
              {status.text}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
