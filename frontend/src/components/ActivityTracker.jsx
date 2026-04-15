import { useState, useEffect } from "react";
import { stopSequence, deleteTestActivity, deleteAllTestActivity } from "../api";
import { formatDateTime, formatNextFollowUp } from "../utils/formatDate";
import "./ActivityTracker.css";

const API = import.meta.env.VITE_API_URL ?? "";

function authHeaders() {
  const token = localStorage.getItem("google_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function ActivityTracker({ onBack, onSelectCompany }) {
  const [activity, setActivity] = useState([]);
  const [unreached, setUnreached] = useState([]);
  const [tab, setTab] = useState("active");
  const [loading, setLoading] = useState(true);
  const [stoppingKey, setStoppingKey] = useState(null);
  const [expandedKey, setExpandedKey] = useState(null);

  const handleStop = async (companyId, contactEmail) => {
    const key = `${companyId}-${contactEmail}`;
    if (!confirm(`Stop the follow-up sequence for ${contactEmail}? Already-sent emails won't be recalled, but no more follow-ups will fire.`)) return;
    setStoppingKey(key);
    try {
      await stopSequence(companyId, contactEmail);
      // Refetch activity so the row updates to "Sequence Done"
      const refreshed = await fetch(`${API}/api/activity`, { headers: authHeaders() }).then((r) => r.json());
      setActivity(refreshed);
    } catch (e) {
      alert(`Failed to stop sequence: ${e.message}`);
    } finally {
      setStoppingKey(null);
    }
  };

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/activity`, { headers: authHeaders() }).then((r) => r.json()),
      fetch(`${API}/api/activity/unreached`, { headers: authHeaders() }).then((r) => r.json()),
    ]).then(([act, unr]) => {
      setActivity(act);
      setUnreached(unr);
      setLoading(false);
    });
  }, []);

  // Split real outreach from test sends — they want different presentations.
  const realActivity = activity.filter((a) => !a.is_test);
  const testActivity = activity.filter((a) => a.is_test);

  // Group real activity by company+contact for a cleaner view
  const grouped = {};
  for (const a of realActivity) {
    const key = `${a.company_id}-${a.to_email}`;
    if (!grouped[key]) {
      grouped[key] = {
        company_id: a.company_id,
        company_name: a.company_name,
        industry: a.industry,
        to_email: a.to_email,
        emails: [],
        replied: false,
        latest_type: a.email_type,
        latest_date: a.sent_at,
        next_follow_up: null,
        opened: false,
        total_opens: 0,
      };
    }
    grouped[key].emails.push(a);
    if (a.replied) grouped[key].replied = true;
    if (a.next_follow_up_at) grouped[key].next_follow_up = a.next_follow_up_at;
    if (a.opened_at) grouped[key].opened = true;
    grouped[key].total_opens += a.open_count || 0;
  }
  const contacts = Object.values(grouped);

  if (loading) return <div className="loading">Loading activity...</div>;

  return (
    <div className="activity-tracker">
      <button className="btn btn-secondary" onClick={onBack}>
        &larr; Back to dashboard
      </button>

      <h2>Activity Tracker</h2>

      <div className="tracker-tabs">
        <button
          className={`tab ${tab === "active" ? "active" : ""}`}
          onClick={() => setTab("active")}
        >
          Active Outreach ({contacts.length})
        </button>
        <button
          className={`tab ${tab === "unreached" ? "active" : ""}`}
          onClick={() => setTab("unreached")}
        >
          Ready to Contact ({unreached.length})
        </button>
        <button
          className={`tab ${tab === "tests" ? "active" : ""}`}
          onClick={() => setTab("tests")}
        >
          Test Runs ({testActivity.length})
        </button>
      </div>

      {tab === "active" && (
        <>
          <div className="status-legend">
            <strong>Status key:</strong>
            <span className="legend-item">
              <span className="badge badge-replied">Replied</span>
              recipient wrote back — sequence stopped
            </span>
            <span className="legend-item">
              <span className="badge badge-viewed">👁 Viewed</span>
              opened — every open event listed in the timeline below. Note: an open within ~30s of
              send is usually Gmail's image proxy auto-fetching, not a human view. We can't
              reliably tell sender opens (your own Sent folder) from recipient opens
            </span>
            <span className="legend-item">
              <span className="badge badge-pending">Waiting</span>
              sent, no reply yet — a follow-up is scheduled
            </span>
            <span className="legend-item">
              <span className="badge badge-done">Sequence Done</span>
              all emails sent, no reply, no more follow-ups
            </span>
          </div>
          {contacts.length === 0 ? (
            <p className="empty-state">
              No outreach started yet. Find HR contacts on a company and send your first email.
            </p>
          ) : (
            <table className="tracker-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Contact</th>
                  <th>Stage</th>
                  <th>Emails Sent</th>
                  <th>Status</th>
                  <th>Last Sent</th>
                  <th>Next Follow-up</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {contacts.map((c, i) => {
                  const rowKey = `${c.company_id}-${c.to_email}`;
                  const isExpanded = expandedKey === rowKey;
                  return (
                  <>
                  <tr
                    key={i}
                    className={`tracker-row ${isExpanded ? "tracker-row-expanded" : ""}`}
                    onClick={() => setExpandedKey(isExpanded ? null : rowKey)}
                  >
                    <td>
                      <div className="company-cell">
                        <span className="company-name">{c.company_name}</span>
                        <span className="company-industry">{c.industry}</span>
                      </div>
                    </td>
                    <td className="email-cell">{c.to_email}</td>
                    <td>
                      <span className="badge badge-type">
                        {c.latest_type?.replace("_", " ")}
                      </span>
                    </td>
                    <td className="center">{c.emails.length}</td>
                    <td>
                      {c.replied ? (
                        <span className="badge badge-replied">Replied</span>
                      ) : c.opened ? (
                        <span className="badge badge-viewed" title="See timeline below for individual open events">
                          👁 Viewed
                        </span>
                      ) : c.next_follow_up ? (
                        <span className="badge badge-pending">Waiting</span>
                      ) : (
                        <span className="badge badge-done">Sequence Done</span>
                      )}
                    </td>
                    <td className="date-cell">{formatDateTime(c.latest_date)}</td>
                    <td className="date-cell">{formatNextFollowUp(c.next_follow_up)}</td>
                    <td className="stop-cell" onClick={(e) => e.stopPropagation()}>
                      {c.next_follow_up && !c.replied && (
                        <button
                          className="btn btn-stop-sm"
                          disabled={stoppingKey === rowKey}
                          onClick={() => handleStop(c.company_id, c.to_email)}
                          title="Stop future follow-ups for this contact"
                        >
                          {stoppingKey === rowKey ? "..." : "Stop"}
                        </button>
                      )}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${i}-expanded`} className="tracker-row-detail">
                      <td colSpan={8}>
                        <TimelinePanel
                          contact={c}
                          onViewCompany={() => onSelectCompany(c.company_id)}
                        />
                      </td>
                    </tr>
                  )}
                  </>
                  );
                })}
              </tbody>
            </table>
          )}
        </>
      )}

      {tab === "unreached" && (
        <>
          {unreached.length === 0 ? (
            <p className="empty-state">
              All companies with found emails have been contacted. Find more contacts to fill this list.
            </p>
          ) : (
            <table className="tracker-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Industry</th>
                  <th>City</th>
                  <th>Contacts Found</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {unreached.map((c) => (
                  <tr
                    key={c.id}
                    className="tracker-row"
                    onClick={() => onSelectCompany(c.id)}
                  >
                    <td className="company-name">{c.name}</td>
                    <td>{c.industry}</td>
                    <td>{c.city}</td>
                    <td className="center">{c.email_count}</td>
                    <td>
                      <button className="btn btn-small btn-primary">
                        Start Outreach
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {tab === "tests" && (
        <TestRunsPanel
          tests={testActivity}
          onRefresh={async () => {
            const refreshed = await fetch(`${API}/api/activity`, { headers: authHeaders() }).then((r) => r.json());
            setActivity(refreshed);
          }}
        />
      )}
    </div>
  );
}


function TestRunsPanel({ tests, onRefresh }) {
  const [deletingId, setDeletingId] = useState(null);
  const [clearing, setClearing] = useState(false);

  const handleDelete = async (id) => {
    if (!confirm("Delete this test record?")) return;
    setDeletingId(id);
    try {
      await deleteTestActivity(id);
      await onRefresh();
    } catch (e) {
      alert(`Failed to delete: ${e.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!confirm(`Delete all ${tests.length} test records? This cannot be undone.`)) return;
    setClearing(true);
    try {
      await deleteAllTestActivity();
      await onRefresh();
    } catch (e) {
      alert(`Failed to clear: ${e.message}`);
    } finally {
      setClearing(false);
    }
  };

  if (tests.length === 0) {
    return (
      <p className="empty-state">
        No test sends yet. Run a test from any email composer to see it here.
      </p>
    );
  }

  return (
    <>
      <div className="test-runs-header">
        <p className="test-runs-hint">
          Test sends are real emails routed to the test address you specified in the composer —
          they go through Gmail like any other send. Delete them here to keep the list clean.
        </p>
        <button
          className="btn btn-stop-sm"
          disabled={clearing}
          onClick={handleClearAll}
        >
          {clearing ? "Clearing..." : `Clear all (${tests.length})`}
        </button>
      </div>
      <table className="tracker-table">
        <thead>
          <tr>
            <th>Sent</th>
            <th>To</th>
            <th>Company</th>
            <th>Subject</th>
            <th>Step</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {tests.map((t) => (
            <tr key={t.id} className="tracker-row">
              <td className="date-cell">{formatDateTime(t.sent_at)}</td>
              <td className="email-cell">{t.to_email}</td>
              <td>{t.company_name}</td>
              <td className="test-subject-cell">{t.subject}</td>
              <td>
                <span className="badge badge-type">
                  {t.email_type?.replace(/_/g, " ")}
                </span>
              </td>
              <td className="stop-cell">
                <button
                  className="btn btn-stop-sm"
                  disabled={deletingId === t.id}
                  onClick={() => handleDelete(t.id)}
                >
                  {deletingId === t.id ? "..." : "Delete"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}


function TimelinePanel({ contact, onViewCompany }) {
  // Build a flat event list: each email (send), each open, each reply.
  // Sort chronologically so the UI reads top-to-bottom.
  const events = [];
  for (const e of contact.emails) {
    events.push({
      type: "sent",
      at: e.sent_at,
      label: `Sent — ${e.email_type.replace(/_/g, " ")}`,
      subject: e.subject,
    });
    for (const opened_at of (e.opens || [])) {
      events.push({ type: "opened", at: opened_at });
    }
    if (e.replied) {
      events.push({ type: "replied", at: null, label: "Replied" });
    }
  }
  // Sort by timestamp (replied events without a timestamp float to end)
  events.sort((a, b) => {
    if (!a.at && !b.at) return 0;
    if (!a.at) return 1;
    if (!b.at) return -1;
    return new Date(a.at) - new Date(b.at);
  });

  return (
    <div className="timeline-panel">
      <div className="timeline-header">
        <div>
          <strong>{contact.to_email}</strong>
          <span className="timeline-sub"> at {contact.company_name}</span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={onViewCompany}>
          Open company →
        </button>
      </div>

      {events.length === 0 ? (
        <p className="timeline-empty">No events yet.</p>
      ) : (
        <ol className="timeline-list">
          {events.map((ev, i) => (
            <li key={i} className={`timeline-event timeline-${ev.type}`}>
              <span className="timeline-dot" />
              <div className="timeline-content">
                <div className="timeline-label">
                  {ev.type === "sent" && <>📤 {ev.label}</>}
                  {ev.type === "opened" && <>👁 Opened</>}
                  {ev.type === "replied" && <>💬 {ev.label}</>}
                </div>
                {ev.subject && <div className="timeline-subject">{ev.subject}</div>}
                <div className="timeline-time">
                  {ev.at ? formatDateTime(ev.at) : "time unknown"}
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}

      {contact.next_follow_up && !contact.replied && (
        <div className="timeline-next">
          ⏱ Next follow-up sends around {formatNextFollowUp(contact.next_follow_up)}
        </div>
      )}
    </div>
  );
}
