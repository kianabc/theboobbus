import { useState, useEffect, useRef, useCallback } from "react";
import { generateEmail, sendEmail, getDraft, saveDraft } from "../api";
import "./EmailComposer.css";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

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
  const [testStep, setTestStep] = useState(0); // 0=not started, 1=initial sent, 2+=follow-ups
  const [testTotalSteps, setTestTotalSteps] = useState(0);
  const [testCountdown, setTestCountdown] = useState(0);
  const [testTimers, setTestTimers] = useState([]);

  const contactName = contact.source?.match(/- (.+?),/)?.[1] || null;
  const contactTitle = contact.source?.match(/, (.+?)$/)?.[1]?.replace(/\(.*\)/, "").trim() || null;

  // Track latest values in refs so unmount save has current data
  const subjectRef = useRef(subject);
  const bodyRef = useRef(body);
  const loadingRef = useRef(true);
  subjectRef.current = subject;
  bodyRef.current = body;
  loadingRef.current = loadingDraft;

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

  // Save immediately on unmount
  useEffect(() => {
    return () => doSave();
  }, [doSave]);

  // Test email countdown timer
  useEffect(() => {
    if (testCountdown <= 0) return;
    const interval = setInterval(() => {
      setTestCountdown((c) => {
        if (c <= 1) {
          clearInterval(interval);
          return 0;
        }
        return c - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [testCountdown]);

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

  const doGmailSend = (toEmail, isTest) => {
    setSending(true);
    setStatus(null);

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
          await sendEmail(
            {
              to: toEmail,
              subject: isTest ? `[TEST] ${subject}` : subject,
              body,
              company_id: isTest ? null : companyId,
              email_type: "initial",
            },
            tokenResponse.access_token
          );
          if (isTest) {
            setStatus({ type: "success", text: `Test sent to ${toEmail}` });
            // Don't close composer, don't call onSent
          } else {
            setStatus({ type: "success", text: "Email sent!" });
            if (onSent) onSent();
          }
        } catch (e) {
          setStatus({ type: "error", text: "Failed to send" });
        } finally {
          setSending(false);
        }
      },
    });
    tokenClient.requestAccessToken();
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
    setTestStep(1);

    // Fetch settings to know sequence length
    const { fetchSettings } = await import("../api");
    const settings = await fetchSettings();
    const totalSteps = settings.sequence_length || 3;
    setTestTotalSteps(totalSteps);

    // Step 1: Send initial immediately
    setStatus({ type: "info", text: `Sending initial outreach (1/${totalSteps})...` });
    doGmailSend(testEmail, true);

    // Steps 2+: Generate and send follow-ups every 3 minutes
    // Must match the actual sequence from followup_engine.py:
    // 2 steps: [initial, final]
    // 3 steps: [initial, follow_up, final]
    // 4 steps: [initial, follow_up, follow_up_2, final]
    // 5 steps: [initial, follow_up, follow_up_2, follow_up_3, final]
    const SEQUENCES = {
      2: ["final"],
      3: ["follow_up", "final"],
      4: ["follow_up", "follow_up_2", "final"],
      5: ["follow_up", "follow_up_2", "follow_up_3", "final"],
    };
    const followUpTypes = SEQUENCES[totalSteps] || SEQUENCES[3];

    const timers = [];
    followUpTypes.forEach((emailType, idx) => {
      const delay = (idx + 1) * 180000; // 3 min increments
      const stepNum = idx + 2;
      const timer = setTimeout(async () => {
        setTestStep(stepNum);
        setStatus({ type: "info", text: `Generating & sending step ${stepNum}/${totalSteps}...` });
        try {
          // Generate follow-up with AI
          const draft = await generateEmail({
            company_id: companyId,
            contact_email: contact.email,
            contact_name: contactName,
            contact_title: contactTitle,
            email_type: emailType,
          });
          // Send it
          const tokenClient = window.google.accounts.oauth2.initTokenClient({
            client_id: GOOGLE_CLIENT_ID,
            scope: "https://www.googleapis.com/auth/gmail.send",
            callback: async (tokenResponse) => {
              if (tokenResponse.error) return;
              await sendEmail(
                { to: testEmail, subject: `[TEST ${stepNum}/${totalSteps}] ${draft.subject}`, body: draft.body, company_id: null, email_type: emailType },
                tokenResponse.access_token
              );
              setStatus({ type: "success", text: `Step ${stepNum}/${totalSteps} sent! ${stepNum < totalSteps ? `Next in 3 min...` : "Test sequence complete!"}` });
              if (stepNum === totalSteps) {
                setTestRunning(false);
              }
            },
          });
          tokenClient.requestAccessToken();
        } catch (e) {
          setStatus({ type: "error", text: `Step ${stepNum} failed: ${e.message}` });
        }
      }, delay);
      timers.push(timer);
    });
    setTestTimers(timers);

    // Start countdown for next follow-up
    setTestCountdown(180);
  };

  const cancelTest = () => {
    testTimers.forEach(clearTimeout);
    setTestTimers([]);
    setTestRunning(false);
    setTestStep(0);
    setTestCountdown(0);
    setStatus({ type: "info", text: "Test sequence cancelled" });
  };

  const formatCountdown = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
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
              {testRunning ? (
                <>
                  <span className="test-countdown">
                    Step {testStep}/{testTotalSteps}
                    {testCountdown > 0 && ` - next in ${formatCountdown(testCountdown)}`}
                  </span>
                  <button className="btn btn-cancel-test" onClick={cancelTest}>
                    Stop
                  </button>
                </>
              ) : (
                <button
                  className="btn btn-test"
                  onClick={handleTestSequence}
                  disabled={sending || !testEmail.trim() || !subject.trim()}
                >
                  Run Test
                </button>
              )}
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
