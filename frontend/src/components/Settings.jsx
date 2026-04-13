import { useState, useEffect } from "react";
import { fetchSettings, updateSettings } from "../api";
import "./Settings.css";

const STEP_LABELS = {
  2: ["Initial Outreach", "Final Check-in"],
  3: ["Initial Outreach", "Follow-up", "Final Check-in"],
  4: ["Initial Outreach", "Follow-up 1", "Follow-up 2", "Final Check-in"],
  5: ["Initial Outreach", "Follow-up 1", "Follow-up 2", "Follow-up 3", "Final Check-in"],
};

export default function Settings({ onBack }) {
  const [followUpDays, setFollowUpDays] = useState(5);
  const [sequenceLength, setSequenceLength] = useState(3);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSettings().then((data) => {
      setFollowUpDays(data.follow_up_days);
      setSequenceLength(data.sequence_length);
      setLoading(false);
    });
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      await updateSettings({
        follow_up_days: followUpDays,
        sequence_length: sequenceLength,
      });
      setStatus({ type: "success", text: "Settings saved" });
    } catch {
      setStatus({ type: "error", text: "Failed to save" });
    } finally {
      setSaving(false);
    }
  };

  const labels = STEP_LABELS[sequenceLength] || STEP_LABELS[3];

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
          <label>Days before each follow-up</label>
          <div className="settings-input-row">
            <input
              type="number"
              min="1"
              max="30"
              value={followUpDays}
              onChange={(e) => setFollowUpDays(parseInt(e.target.value) || 5)}
            />
            <span className="settings-hint">days between each email</span>
          </div>
        </div>

        <div className="settings-field">
          <label>Emails in sequence</label>
          <div className="settings-input-row">
            <select
              value={sequenceLength}
              onChange={(e) => setSequenceLength(parseInt(e.target.value))}
              className="settings-select"
            >
              <option value={2}>2 emails (initial + final)</option>
              <option value={3}>3 emails (default)</option>
              <option value={4}>4 emails</option>
              <option value={5}>5 emails (max)</option>
            </select>
          </div>
        </div>

        <div className="settings-field">
          <label>Sequence preview</label>
          <div className="sequence-preview">
            {labels.map((label, i) => (
              <div key={i}>
                {i > 0 && <div className="sequence-arrow">&darr;</div>}
                <div className="sequence-step">
                  <span className="step-num">{i + 1}</span>
                  <span className="step-label">{label}</span>
                  <span className="step-timing">
                    Day {i * followUpDays}
                  </span>
                </div>
              </div>
            ))}
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
