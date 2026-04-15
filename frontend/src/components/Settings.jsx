import { useState, useEffect } from "react";
import { fetchSettings, updateSettings, gmailAuthorize, gmailStatus, gmailDisconnect, fetchOrgGmailOptions } from "../api";
import "./Settings.css";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

const STEP_LABELS = {
  2: ["Initial Outreach", "Final Check-in"],
  3: ["Initial Outreach", "Follow-up", "Final Check-in"],
  4: ["Initial Outreach", "Follow-up 1", "Follow-up 2", "Final Check-in"],
  5: ["Initial Outreach", "Follow-up 1", "Follow-up 2", "Follow-up 3", "Final Check-in"],
};

export default function Settings({ onBack }) {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [gmail, setGmail] = useState(null);
  const [connectingGmail, setConnectingGmail] = useState(false);
  const [changedKeys, setChangedKeys] = useState({}); // Track which API keys user edited
  const [orgGmailOptions, setOrgGmailOptions] = useState([]);

  useEffect(() => {
    fetchSettings().then(setSettings);
    gmailStatus().then(setGmail);
    fetchOrgGmailOptions().then(setOrgGmailOptions);
  }, []);

  const update = (key, value) => setSettings((s) => ({ ...s, [key]: value }));

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      // Only send API keys that were actually changed (not masked values)
      const payload = { ...settings };
      if (!changedKeys.hunter_api_key) delete payload.hunter_api_key;
      if (!changedKeys.apollo_api_key) delete payload.apollo_api_key;
      if (!changedKeys.anthropic_api_key) delete payload.anthropic_api_key;
      const result = await updateSettings(payload);
      setSettings(result);
      setChangedKeys({});
      setStatus({ type: "success", text: "Settings saved" });
    } catch {
      setStatus({ type: "error", text: "Failed to save" });
    } finally {
      setSaving(false);
    }
  };

  if (!settings) return <div className="loading">Loading settings...</div>;

  const labels = STEP_LABELS[settings.sequence_length] || STEP_LABELS[3];

  return (
    <div className="settings">
      <button className="btn btn-secondary" onClick={onBack}>
        &larr; Back to dashboard
      </button>

      {/* ── Follow-up Settings ── */}
      <div className="settings-card">
        <h2>Follow-up Settings</h2>
        <p className="settings-desc">
          Configure automatic follow-up behavior when no reply is received.
        </p>

        <div className="settings-field">
          <label>Days before each follow-up</label>
          <div className="settings-input-row">
            <input
              type="number"
              min="1"
              max="30"
              value={settings.follow_up_days}
              onChange={(e) => update("follow_up_days", parseInt(e.target.value) || 5)}
            />
            <span className="settings-hint">days between each email</span>
          </div>
        </div>

        <div className="settings-field">
          <label>Emails in sequence</label>
          <div className="settings-input-row">
            <select
              value={settings.sequence_length}
              onChange={(e) => update("sequence_length", parseInt(e.target.value))}
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
                  <span className="step-timing">Day {i * settings.follow_up_days}</span>
                </div>
              </div>
            ))}
            <div className="sequence-arrow">&darr;</div>
            <div className="sequence-step sequence-end">
              <span className="step-label">Stop (no more emails)</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Data Sources ── */}
      <div className="settings-card">
        <h2>Contact Finding Sources</h2>
        <p className="settings-desc">
          Enable or disable data sources used when finding HR contacts.
          Add your API keys here or use the ones from environment variables.
        </p>

        <div className="source-item">
          <div className="source-header">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={settings.hunter_enabled}
                onChange={(e) => update("hunter_enabled", e.target.checked)}
              />
              <span className="toggle-name">Hunter.io</span>
            </label>
            <span className="source-desc">Find emails by company domain + verify patterns</span>
          </div>
          {settings.hunter_enabled && (
            <div className="source-config">
              <input
                type="password"
                placeholder="Hunter.io API Key"
                value={changedKeys.hunter_api_key !== undefined ? settings.hunter_api_key : settings.hunter_api_key}
                onChange={(e) => { update("hunter_api_key", e.target.value); setChangedKeys(k => ({...k, hunter_api_key: true})); }}
                className="api-key-input"
              />
              {settings.hunter_api_key_set && !changedKeys.hunter_api_key && (
                <span className="settings-hint key-status">Key is set (masked for security)</span>
              )}
              <span className="settings-hint">Leave blank to use environment variable</span>
            </div>
          )}
        </div>

        <div className="source-item">
          <div className="source-header">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={settings.apollo_enabled}
                onChange={(e) => update("apollo_enabled", e.target.checked)}
              />
              <span className="toggle-name">Apollo.io</span>
            </label>
            <span className="source-desc">Find HR people by job title at companies</span>
          </div>
          {settings.apollo_enabled && (
            <div className="source-config">
              <input
                type="password"
                placeholder="Apollo.io API Key"
                value={changedKeys.apollo_api_key !== undefined ? settings.apollo_api_key : settings.apollo_api_key}
                onChange={(e) => { update("apollo_api_key", e.target.value); setChangedKeys(k => ({...k, apollo_api_key: true})); }}
                className="api-key-input"
              />
              {settings.apollo_api_key_set && !changedKeys.apollo_api_key && (
                <span className="settings-hint key-status">Key is set (masked for security)</span>
              )}
              <span className="settings-hint">
                Free tier: names are partially hidden, no emails.{" "}
                <a href="https://www.apollo.io/pricing" target="_blank" rel="noopener noreferrer" className="upgrade-link">
                  Upgrade Apollo plan
                </a>{" "}
                to get full names and verified emails.
              </span>
            </div>
          )}
        </div>

        <div className="source-item">
          <div className="source-header">
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={settings.scraping_enabled}
                onChange={(e) => update("scraping_enabled", e.target.checked)}
              />
              <span className="toggle-name">Web Scraping</span>
            </label>
            <span className="source-desc">Crawl company websites for email addresses (no API key needed)</span>
          </div>
        </div>
      </div>

      {/* ── AI API Key ── */}
      <div className="settings-card">
        <h2>AI Email Generation</h2>
        <p className="settings-desc">
          API key for Claude AI, used to generate personalized outreach emails.
        </p>

        <div className="source-item">
          <div className="source-header">
            <span className="toggle-name">Claude API (Anthropic)</span>
            <span className="source-desc">Powers all AI-generated email drafts</span>
          </div>
          <div className="source-config">
            <input
              type="password"
              placeholder="Anthropic API Key (sk-ant-...)"
              value={changedKeys.anthropic_api_key !== undefined ? settings.anthropic_api_key : settings.anthropic_api_key}
              onChange={(e) => { update("anthropic_api_key", e.target.value); setChangedKeys(k => ({...k, anthropic_api_key: true})); }}
              className="api-key-input"
            />
            {settings.anthropic_api_key_set && !changedKeys.anthropic_api_key && (
              <span className="settings-hint key-status">Key is set (masked for security)</span>
            )}
          </div>
        </div>
      </div>

      {/* ── Email Signature ── */}
      <div className="settings-card">
        <h2>Email Signature</h2>
        <p className="settings-desc">
          Appended to every AI-generated email. Use <code>{"{sender_name}"}</code> for the logged-in user's name.
        </p>
        <textarea
          className="signature-input"
          value={settings.email_signature}
          onChange={(e) => update("email_signature", e.target.value)}
          rows={5}
        />
      </div>

      {/* ── Organization Send Account ── */}
      <div className="settings-card">
        <h2>Organization Send Account</h2>
        <p className="settings-desc">
          All outreach — initial emails, test sequences, and auto follow-ups — goes out through the
          Gmail account selected here, regardless of which teammate is logged in. Set this once and
          every user's sends land in the same Sent folder. Leave blank to fall back to each user's
          own connected Gmail.
        </p>

        <div className="settings-field">
          <label>Send emails from</label>
          <select
            value={settings.org_gmail_account || ""}
            onChange={(e) => update("org_gmail_account", e.target.value)}
            className="settings-select"
          >
            <option value="">— Use each user's own Gmail —</option>
            {orgGmailOptions.map((opt) => (
              <option key={opt.email} value={opt.email}>
                {opt.full_name} ({opt.email})
              </option>
            ))}
          </select>
          {orgGmailOptions.length === 0 && (
            <span className="settings-hint">
              No Gmail accounts connected yet. Connect one below first.
            </span>
          )}
        </div>
      </div>

      {/* ── Gmail Connection for Auto Follow-ups ── */}
      <div className="settings-card">
        <h2>Gmail Connection</h2>
        <p className="settings-desc">
          Connect your Gmail account to enable automatic follow-up emails.
          Without this, follow-ups must be sent manually.
        </p>

        {gmail?.authorized ? (
          <div className="gmail-connected">
            <span className="gmail-status-icon">&#10003;</span>
            <div style={{flex: 1}}>
              <strong>Connected:</strong> {gmail.email}
              <br/>
              <span className="settings-hint">
                Auto follow-ups are active. Last updated: {new Date(gmail.updated_at).toLocaleString()}
              </span>
            </div>
            <button
              className="btn btn-secondary"
              style={{marginLeft: "auto", fontSize: 12}}
              onClick={async () => {
                if (!confirm(`Disconnect ${gmail.email}? Auto follow-ups will stop until you reconnect.`)) return;
                await gmailDisconnect();
                setGmail({ authorized: false });
                setStatus({ type: "success", text: "Gmail disconnected. You can connect a different account now." });
              }}
            >
              Disconnect
            </button>
          </div>
        ) : (
          <button
            className="btn btn-primary"
            disabled={connectingGmail}
            onClick={() => {
              setConnectingGmail(true);
              const redirectUri = window.location.origin;
              // Use Google's code client to get an authorization code with offline access
              const codeClient = window.google.accounts.oauth2.initCodeClient({
                client_id: GOOGLE_CLIENT_ID,
                scope: "https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly",
                ux_mode: "popup",
                redirect_uri: redirectUri,
                callback: async (response) => {
                  if (response.error) {
                    setStatus({ type: "error", text: "Gmail authorization denied" });
                    setConnectingGmail(false);
                    return;
                  }
                  try {
                    const result = await gmailAuthorize(response.code, redirectUri);
                    setGmail({ authorized: true, email: result.email, updated_at: new Date().toISOString() });
                    setStatus({ type: "success", text: "Gmail connected! Auto follow-ups are now active." });
                  } catch (e) {
                    setStatus({ type: "error", text: "Failed to connect Gmail: " + e.message });
                  } finally {
                    setConnectingGmail(false);
                  }
                },
              });
              codeClient.requestCode();
            }}
          >
            {connectingGmail ? "Connecting..." : "Connect Gmail for Auto Follow-ups"}
          </button>
        )}
      </div>

      {/* ── Save ── */}
      <div className="settings-actions">
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save All Settings"}
        </button>
        {status && (
          <span className={`settings-status ${status.type}`}>{status.text}</span>
        )}
      </div>
    </div>
  );
}
