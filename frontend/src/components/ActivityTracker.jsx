import { useState, useEffect } from "react";
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

  // Group activity by company+contact for a cleaner view
  const grouped = {};
  for (const a of activity) {
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
      };
    }
    grouped[key].emails.push(a);
    if (a.replied) grouped[key].replied = true;
    if (a.next_follow_up_at) grouped[key].next_follow_up = a.next_follow_up_at;
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
      </div>

      {tab === "active" && (
        <>
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
                </tr>
              </thead>
              <tbody>
                {contacts.map((c, i) => (
                  <tr
                    key={i}
                    className="tracker-row"
                    onClick={() => onSelectCompany(c.company_id)}
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
                      ) : c.next_follow_up ? (
                        <span className="badge badge-pending">Waiting</span>
                      ) : (
                        <span className="badge badge-done">Sequence Done</span>
                      )}
                    </td>
                    <td className="date-cell">
                      {new Date(c.latest_date).toLocaleDateString()}
                    </td>
                    <td className="date-cell">
                      {c.next_follow_up
                        ? new Date(c.next_follow_up).toLocaleDateString()
                        : "—"}
                    </td>
                  </tr>
                ))}
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
    </div>
  );
}
