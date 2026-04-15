import { useState, useEffect, useRef, useCallback } from "react";
import { generateEmail, sendEmail, getDraft, saveDraft, startTestSequence } from "../api";
import "./EmailComposer.css";

export default function EmailComposer({ companyId, contact, onSent }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState(null);
  const [loadingDraft, setLoadingDraft] = useState(true);

  // Test email state
  const [showTestInput, setShowTestInput] = useState(false);
  const [testEmail, setTestEmail] = useState("");
  const [testRunning, setTestRunning] = useState(false);

  const contactName = contact.source?.match(/- (.+?),/)?.[1] || null;
  const contactTitle = contact.source?.match(/, (.+?)$/)?.[1]?.replace(/\(.*\)/, "").trim() || null;

  // Track latest values in refs so unmount save has current data
  const subjectRef = useRef(subject);
  const bodyRef = useRef(body);
  const loadingRef = useRef(true);
  subjectRef.current = subject;
  bodyRef.current = body;
  loadingRef.current = loadingDraft;

  // Save using sendBeacon (survives unmount/navigation)
  const doSaveBeacon = useCallback(() => {
    if (loadingRef.current) return;
    if (!subjectRef.current && !bodyRef.current) return;
    const API = import.meta.env.VITE_API_URL ?? "";
    const token = localStorage.getItem("google_token");
    const url = `${API}/api/companies/${companyId}/draft`;
    const payload = JSON.stringify({
      contact_email: contact.email,
      subject: subjectRef.current,
      body: bodyRef.current,
    });
    // sendBeacon survives page unload; fetch with keepalive as backup
    try {
      const blob = new Blob([payload], { type: "application/json" });
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      // sendBeacon can't set custom headers, so use fetch with keepalive
      fetch(url, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...headers },
        body: payload,
        keepalive: true,
      });
    } catch {
      // Fallback
      saveDraft(companyId, { contact_email: contact.email, subject: subjectRef.current, body: bodyRef.current });
    }
  }, [companyId, contact.email]);

  const doSave = useCallback(() => {
    if (loadingRef.current) return;
    if (!subjectRef.current && !bodyRef.current) return;
    saveDraft(companyId, { contact_email: contact.email, subject: subjectRef.current, body: bodyRef.current });
  }, [companyId, contact.email]);

  // Load saved draft on mount
  useEffect(() => {
    getDraft(companyId, contact.email).then((draft) => {
      if (draft.subject || draft.body) {
        setSubject(draft.subject || "");
        setBody(draft.body || "");
      }
      setLoadingDraft(false);
    });
  }, [companyId, contact.email]);

  // Auto-save draft when subject/body changes (debounced)
  useEffect(() => {
    if (loadingDraft) return;
    if (!subject && !body) return;
    const timeout = setTimeout(doSave, 1000);
    return () => clearTimeout(timeout);
  }, [subject, body, loadingDraft, doSave]);

  // Save immediately on unmount using keepalive fetch
  useEffect(() => {
    return () => doSaveBeacon();
  }, [doSaveBeacon]);


  const handleGenerate = async () => {
    setGenerating(true);
    setStatus(null);
    try {
      const result = await generateEmail({
        company_id: companyId,
        contact_email: contact.email,
        contact_name: contactName,
        contact_title: contactTitle,
        email_type: "initial",
      });
      setSubject(result.subject || "");
      setBody(result.body || "");
    } catch (e) {
      setStatus({ type: "error", text: "Failed to generate email" });
    } finally {
      setGenerating(false);
    }
  };

  const doGmailSend = async (toEmail, isTest) => {
    setSending(true);
    setStatus(null);
    try {
      const result = await sendEmail({
        to: toEmail,
        subject: isTest ? `[TEST] ${subject}` : subject,
        body,
        company_id: isTest ? null : companyId,
        email_type: "initial",
      });
      if (result.status === "sent") {
        if (isTest) {
          setStatus({ type: "success", text: `Test sent to ${toEmail}` });
        } else {
          setStatus({ type: "success", text: "Email sent!" });
          if (onSent) onSent();
        }
      } else {
        setStatus({ type: "error", text: result.detail || "Failed to send" });
      }
    } catch (e) {
      setStatus({ type: "error", text: "Failed to send. Make sure Gmail is connected in Settings." });
    } finally {
      setSending(false);
    }
  };

  const handleSend = () => {
    if (!subject.trim() || !body.trim()) {
      setStatus({ type: "error", text: "Subject and body are required" });
      return;
    }
    doGmailSend(contact.email, false);
  };

  const handleTestSequence = async () => {
    if (!testEmail.trim() || !subject.trim() || !body.trim()) {
      setStatus({ type: "error", text: "Enter a test email and fill in the subject/body" });
      return;
    }

    setTestRunning(true);
    setStatus({ type: "info", text: "Running test sequence — sends one every 20s, please wait..." });

    try {
      const result = await startTestSequence({
        company_id: companyId,
        contact_email: contact.email,
        contact_name: contactName,
        contact_title: contactTitle,
        test_email: testEmail,
        subject,
        body,
      });
      if (result.status === "complete") {
        const sent = result.sent ?? 0;
        const total = result.total_steps ?? 0;
        if (sent === total) {
          setStatus({
            type: "success",
            text: `Sent all ${sent} test emails to ${testEmail} (20s apart). Check your inbox.`,
          });
        } else if (sent === 0) {
          setStatus({
            type: "error",
            text: `All steps failed. Errors: ${(result.errors || []).join("; ") || "unknown"}`,
          });
        } else {
          setStatus({
            type: "error",
            text: `Sent ${sent}/${total} test emails. Errors: ${(result.errors || []).join("; ") || "unknown"}`,
          });
        }
      } else {
        setStatus({ type: "error", text: result.detail || "Failed to run test sequence" });
      }
    } catch (e) {
      setStatus({ type: "error", text: "Failed to run test. Is Gmail connected in Settings?" });
    } finally {
      setTestRunning(false);
    }
  };

  if (loadingDraft) return <div className="email-composer"><p>Loading draft...</p></div>;

  return (
    <div className="email-composer">
      <div className="composer-header">
        <h4>Compose Email to {contact.email}</h4>
        {(contactName || contactTitle) && (
          <p className="composer-contact-info">
            {contactName}{contactTitle ? ` - ${contactTitle}` : ""}
          </p>
        )}
      </div>

      <div className="composer-controls">
        <button
          className="btn btn-generate"
          onClick={handleGenerate}
          disabled={generating}
        >
          {generating ? "Writing..." : "Draft with AI"}
        </button>
        <span className="autosave-hint">Drafts auto-save</span>
      </div>

      <input
        type="text"
        className="composer-subject"
        placeholder="Subject line..."
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
      />

      <textarea
        className="composer-body"
        placeholder="Email body... Click 'Draft with AI' to generate, or type your own."
        rows={10}
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />

      <div className="composer-actions">
        <button
          className="btn btn-send"
          onClick={handleSend}
          disabled={sending || !subject.trim() || !body.trim()}
        >
          {sending ? "Sending..." : "Send via Gmail"}
        </button>

        <div className="test-section">
          {!showTestInput ? (
            <button
              className="btn btn-test"
              onClick={() => setShowTestInput(true)}
            >
              Test Sequence
            </button>
          ) : (
            <div className="test-input-row">
              <input
                type="email"
                placeholder="Test email address"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
                className="test-email-input"
                disabled={testRunning}
              />
              <button
                className="btn btn-test"
                onClick={handleTestSequence}
                disabled={testRunning || !testEmail.trim() || !subject.trim()}
              >
                {testRunning ? "Starting..." : "Run Test"}
              </button>
            </div>
          )}
        </div>
      </div>

      {status && (
        <div className={`composer-status ${status.type}`}>
          {status.text}
        </div>
      )}
    </div>
  );
}
