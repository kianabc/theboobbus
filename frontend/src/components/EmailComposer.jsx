import { useState } from "react";
import { generateEmail, sendEmail } from "../api";
import "./EmailComposer.css";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

export default function EmailComposer({ companyId, contact, onSent }) {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [emailType, setEmailType] = useState("initial");
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState(null);

  // Parse contact name/title from source string (e.g., "Apollo.io - Erica G., HR Manager")
  const contactName = contact.source?.match(/- (.+?),/)?.[1] || null;
  const contactTitle = contact.source?.match(/, (.+?)$/)?.[1]?.replace(/\(.*\)/, "").trim() || null;

  const handleGenerate = async () => {
    setGenerating(true);
    setStatus(null);
    try {
      const result = await generateEmail({
        company_id: companyId,
        contact_email: contact.email,
        contact_name: contactName,
        contact_title: contactTitle,
        email_type: emailType,
      });
      setSubject(result.subject || "");
      setBody(result.body || "");
    } catch (e) {
      setStatus({ type: "error", text: "Failed to generate email" });
    } finally {
      setGenerating(false);
    }
  };

  const handleSend = async () => {
    if (!subject.trim() || !body.trim()) {
      setStatus({ type: "error", text: "Subject and body are required" });
      return;
    }

    setSending(true);
    setStatus(null);

    try {
      // Request Gmail send scope via Google OAuth
      const tokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: "https://www.googleapis.com/auth/gmail.send",
        callback: async (tokenResponse) => {
          if (tokenResponse.error) {
            setStatus({ type: "error", text: "Gmail permission denied" });
            setSending(false);
            return;
          }

          try {
            const result = await sendEmail(
              {
                to: contact.email,
                subject,
                body,
                company_id: companyId,
                email_type: emailType,
              },
              tokenResponse.access_token
            );
            setStatus({ type: "success", text: "Email sent!" });
            setSubject("");
            setBody("");
            if (onSent) onSent();
          } catch (e) {
            setStatus({ type: "error", text: "Failed to send email" });
          } finally {
            setSending(false);
          }
        },
      });
      tokenClient.requestAccessToken();
    } catch (e) {
      setStatus({ type: "error", text: "Gmail auth failed" });
      setSending(false);
    }
  };

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
        <select
          value={emailType}
          onChange={(e) => setEmailType(e.target.value)}
          className="type-select"
        >
          <option value="initial">Initial Outreach</option>
          <option value="follow_up">Follow-up</option>
          <option value="final">Final Check-in</option>
        </select>
        <button
          className="btn btn-generate"
          onClick={handleGenerate}
          disabled={generating}
        >
          {generating ? "Writing..." : "Draft with AI"}
        </button>
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
        {status && (
          <span className={`composer-status ${status.type}`}>
            {status.text}
          </span>
        )}
      </div>
    </div>
  );
}
