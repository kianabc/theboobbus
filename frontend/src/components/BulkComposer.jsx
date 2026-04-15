import { useState, useEffect } from "react";
import { bulkGenerate, bulkSend } from "../api";
import "./BulkComposer.css";

export default function BulkComposer({ companyId, contacts, onClose, onSent }) {
  const [angleHint, setAngleHint] = useState("");
  const [phase, setPhase] = useState("prep"); // prep | generating | review | sending | done
  const [drafts, setDrafts] = useState([]); // [{contact_email, contact_name, contact_title, subject, body, status?}]
  const [activeIdx, setActiveIdx] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const handleGenerate = async () => {
    setPhase("generating");
    setError("");
    try {
      const payload = {
        company_id: companyId,
        contacts: contacts.map((c) => ({
          email: c.email,
          name: c.name || null,
          title: c.title || null,
        })),
        angle_hint: angleHint.trim() || null,
        email_type: "initial",
      };
      const res = await bulkGenerate(payload);
      setDrafts(res.map((d) => ({ ...d, status: "ready" })));
      setPhase("review");
    } catch (e) {
      setError(e.message || "Generation failed");
      setPhase("prep");
    }
  };

  const updateDraft = (idx, field, value) => {
    setDrafts((prev) => prev.map((d, i) => (i === idx ? { ...d, [field]: value } : d)));
  };

  const handleSend = async () => {
    setPhase("sending");
    setError("");
    try {
      const res = await bulkSend({
        company_id: companyId,
        emails: drafts.map((d) => ({
          contact_email: d.contact_email,
          contact_name: d.contact_name,
          contact_title: d.contact_title,
          subject: d.subject,
          body: d.body,
        })),
      });
      setResult(res);
      setPhase("done");
      if (onSent) onSent();
    } catch (e) {
      setError(e.message || "Send failed");
      setPhase("review");
    }
  };

  const active = drafts[activeIdx];

  return (
    <div className="bulk-composer-backdrop" onClick={onClose}>
      <div className="bulk-composer" onClick={(e) => e.stopPropagation()}>
        <div className="bulk-header">
          <h2>Bulk compose ({contacts.length} contact{contacts.length === 1 ? "" : "s"})</h2>
          <button className="bulk-close" onClick={onClose}>&times;</button>
        </div>

        {error && <div className="bulk-error">{error}</div>}

        {phase === "prep" && (
          <div className="bulk-prep">
            <p className="bulk-desc">
              Each contact gets an independently generated draft. You'll review and edit each one
              before sending. Sends are jittered 30–120s apart to avoid spam flags.
            </p>
            <div className="bulk-contact-preview">
              <strong>Recipients:</strong>
              <ul>
                {contacts.map((c) => (
                  <li key={c.email}>
                    {c.name || "(no name)"} &middot; {c.email}{c.title ? ` · ${c.title}` : ""}
                  </li>
                ))}
              </ul>
            </div>
            <label className="bulk-label">
              Angle / hint (optional)
              <textarea
                value={angleHint}
                onChange={(e) => setAngleHint(e.target.value)}
                placeholder="e.g. Mention Q4 health fair season. Or: emphasize convenience for their frontline workers."
                rows={3}
              />
              <span className="bulk-hint">
                Applied to all {contacts.length} drafts. Keep it brief — one line is fine.
              </span>
            </label>
            <div className="bulk-actions">
              <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" onClick={handleGenerate}>
                Generate {contacts.length} draft{contacts.length === 1 ? "" : "s"}
              </button>
            </div>
          </div>
        )}

        {phase === "generating" && (
          <div className="bulk-generating">
            <div className="bulk-spinner" />
            <p>Generating {contacts.length} personalized drafts in parallel...</p>
          </div>
        )}

        {phase === "review" && active && (
          <div className="bulk-review">
            <div className="bulk-tabs">
              {drafts.map((d, i) => (
                <button
                  key={d.contact_email}
                  className={`bulk-tab ${i === activeIdx ? "active" : ""}`}
                  onClick={() => setActiveIdx(i)}
                >
                  <span className="bulk-tab-num">{i + 1}</span>
                  <span className="bulk-tab-name">{d.contact_name || d.contact_email}</span>
                  <span className="bulk-tab-email">{d.contact_email}</span>
                </button>
              ))}
            </div>

            <div className="bulk-editor">
              <div className="bulk-editor-meta">
                <strong>To:</strong> {active.contact_name || active.contact_email}
                {active.contact_title && <span> · {active.contact_title}</span>}
                <span className="bulk-editor-email"> &lt;{active.contact_email}&gt;</span>
              </div>
              <label className="bulk-label">
                Subject
                <input
                  type="text"
                  value={active.subject}
                  onChange={(e) => updateDraft(activeIdx, "subject", e.target.value)}
                />
              </label>
              <label className="bulk-label">
                Body
                <textarea
                  value={active.body}
                  onChange={(e) => updateDraft(activeIdx, "body", e.target.value)}
                  rows={18}
                />
              </label>
            </div>

            <div className="bulk-actions">
              <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSend}>
                Send all {drafts.length}
              </button>
            </div>
          </div>
        )}

        {phase === "sending" && (
          <div className="bulk-generating">
            <div className="bulk-spinner" />
            <p>Sending first email now, scheduling the rest...</p>
          </div>
        )}

        {phase === "done" && result && (
          <div className="bulk-done">
            <h3>✓ Queued</h3>
            <p className="bulk-done-summary">
              First email sent immediately. {result.scheduled} remaining will send over the next{" "}
              ~{Math.ceil((result.estimated_last_send_seconds || 0) / 60)} minute
              {result.estimated_last_send_seconds >= 120 ? "s" : ""} with jitter.
            </p>
            <ul className="bulk-done-list">
              {(result.sent_immediately || []).map((r) => (
                <li key={r.contact_email} className={r.status === "sent" ? "ok" : "fail"}>
                  {r.status === "sent" ? "✓" : "✗"} {r.contact_email}
                  {r.error && <span className="bulk-err-detail"> — {r.error}</span>}
                </li>
              ))}
              {result.scheduled > 0 && (
                <li className="scheduled">
                  ⏱ {result.scheduled} scheduled for rolling send
                </li>
              )}
            </ul>
            <div className="bulk-actions">
              <button className="btn btn-primary" onClick={onClose}>Close</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
