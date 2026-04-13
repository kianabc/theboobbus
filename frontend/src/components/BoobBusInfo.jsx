import { useState, useEffect } from "react";
import { fetchSettings } from "../api";
import "./BoobBusInfo.css";

const API = import.meta.env.VITE_API_URL ?? "";

function authHeaders() {
  const token = localStorage.getItem("google_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const PROMPT_LABELS = {
  initial: "Initial Outreach",
  follow_up: "Follow-up 1",
  follow_up_2: "Follow-up 2",
  follow_up_3: "Follow-up 3",
  final: "Final Check-in",
};

const PROMPT_ORDER = ["initial", "follow_up", "follow_up_2", "follow_up_3", "final"];

export default function BoobBusInfo({ onBack }) {
  const [info, setInfo] = useState("");
  const [customerFeedback, setCustomerFeedback] = useState("");
  const [prompts, setPrompts] = useState({});
  const [defaults, setDefaults] = useState({});
  const [sequenceLength, setSequenceLength] = useState(3);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activePrompt, setActivePrompt] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/boobbus-info`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/api/prompts`, { headers: authHeaders() }).then((r) => r.json()),
      fetchSettings(),
    ]).then(([infoData, promptData, settingsData]) => {
      setInfo(infoData.info);
      setCustomerFeedback(infoData.customer_feedback || "");
      setPrompts(promptData.prompts);
      setDefaults(promptData.defaults);
      setSequenceLength(settingsData.sequence_length);
      setLoading(false);
    });
  }, []);

  // Determine which prompts are active based on sequence length
  const activePrompts = (() => {
    if (sequenceLength === 2) return ["initial", "final"];
    if (sequenceLength === 3) return ["initial", "follow_up", "final"];
    if (sequenceLength === 4) return ["initial", "follow_up", "follow_up_2", "final"];
    return ["initial", "follow_up", "follow_up_2", "follow_up_3", "final"];
  })();

  const handleSave = async () => {
    setSaving(true);
    setStatus(null);
    try {
      await fetch(`${API}/api/boobbus-info-update`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ info, prompts, customer_feedback: customerFeedback }),
      });
      setStatus({ type: "success", text: "All changes saved" });
    } catch {
      setStatus({ type: "error", text: "Failed to save" });
    } finally {
      setSaving(false);
    }
  };

  const resetPrompt = (key) => {
    setPrompts((p) => ({ ...p, [key]: defaults[key] }));
  };

  const resetInfo = () => {
    // Fetch default info
    fetch(`${API}/api/boobbus-info`, { headers: authHeaders() })
      .then((r) => r.json())
      .then(() => {
        // Clear custom to get default back
        setInfo("");
        fetch(`${API}/api/boobbus-info-update`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ info: "" }),
        }).then(() => {
          fetch(`${API}/api/boobbus-info`, { headers: authHeaders() })
            .then((r) => r.json())
            .then((data) => setInfo(data.info));
        });
      });
  };

  if (loading) return <div className="loading">Loading...</div>;

  return (
    <div className="boobbus-info">
      <button className="btn btn-secondary" onClick={onBack}>
        &larr; Back to dashboard
      </button>

      {/* ── Boob Bus Context ── */}
      <div className="info-card">
        <h2>Boob Bus Information</h2>
        <p className="info-desc">
          This is the context that Claude AI uses when writing all emails.
          It includes facts about The Boob Bus, services, pricing, and benefits.
        </p>

        <textarea
          className="info-editor"
          value={info}
          onChange={(e) => setInfo(e.target.value)}
          rows={14}
        />

        <div className="info-actions">
          <button className="btn btn-secondary btn-sm" onClick={resetInfo}>
            Reset to Default
          </button>
        </div>
      </div>

      {/* ── Customer Feedback ── */}
      <div className="info-card">
        <h2>Customer Feedback & Testimonials</h2>
        <p className="info-desc">
          Real quotes, stats, and stories from Boob Bus customers. The AI will reference
          these in emails but will <strong>never make up</strong> fake testimonials or statistics.
          Only what you put here will be used.
        </p>

        <textarea
          className="info-editor"
          value={customerFeedback}
          onChange={(e) => setCustomerFeedback(e.target.value)}
          rows={8}
          placeholder={`Example:\n- "The Boob Bus made it so easy for our team. We had 30 employees get screened in one afternoon." - HR Manager at a Provo tech company\n- 95% of employees who used The Boob Bus said they would recommend it\n- One employee's early detection story (with permission): ...`}
        />
      </div>

      {/* ── Email Prompts ── */}
      <div className="info-card">
        <h2>Email Prompts</h2>
        <p className="info-desc">
          Customize the AI instructions for each step in the email sequence.
          Use <code>{"{contact_info}"}</code>, <code>{"{company_name}"}</code>,{" "}
          <code>{"{company_industry}"}</code>, and <code>{"{company_city}"}</code> as
          placeholders. Based on your settings, {sequenceLength} emails are active.
        </p>

        <div className="prompt-list">
          {PROMPT_ORDER.map((key) => {
            const isActive = activePrompts.includes(key);
            const isExpanded = activePrompt === key;

            return (
              <div
                key={key}
                className="prompt-item"
              >
                <div
                  className="prompt-header"
                  onClick={() => setActivePrompt(isExpanded ? null : key)}
                >
                  <div className="prompt-title">
                    <span className={`prompt-badge ${isActive ? "active" : ""}`}>
                      {isActive ? activePrompts.indexOf(key) + 1 : "-"}
                    </span>
                    <span className="prompt-name">{PROMPT_LABELS[key]}</span>
                  </div>
                  <div className="prompt-header-right">
                    {!isActive && (
                      <span className="prompt-inactive-label">
                        Not in current sequence ({sequenceLength} emails)
                      </span>
                    )}
                    <span className="prompt-expand">{isExpanded ? "Collapse" : "Edit"}</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="prompt-editor">
                    <textarea
                      value={prompts[key] || ""}
                      onChange={(e) =>
                        setPrompts((p) => ({ ...p, [key]: e.target.value }))
                      }
                      rows={12}
                    />
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => resetPrompt(key)}
                    >
                      Reset to Default
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Save All ── */}
      <div className="info-actions sticky-save">
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? "Saving..." : "Save All Changes"}
        </button>
        {status && (
          <span className={`info-status ${status.type}`}>{status.text}</span>
        )}
      </div>
    </div>
  );
}
