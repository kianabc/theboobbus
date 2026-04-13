import { useState, useEffect } from "react";
import { fetchCompany, scrapeCompany, fetchOutreachHistory, addContact } from "../api";
import EmailComposer from "./EmailComposer";
import "./CompanyDetail.css";

export default function CompanyDetail({ companyId, onBack }) {
  const [company, setCompany] = useState(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeResult, setScrapeResult] = useState(null);
  const [composingFor, setComposingFor] = useState(null);
  const [outreach, setOutreach] = useState([]);
  const [showAddContact, setShowAddContact] = useState(false);
  const [newContact, setNewContact] = useState({ email: "", name: "", title: "" });
  const [addingContact, setAddingContact] = useState(false);

  const load = () => {
    fetchCompany(companyId).then(setCompany);
    fetchOutreachHistory(companyId).then(setOutreach);
  };

  useEffect(() => {
    load();
  }, [companyId]);

  const handleScrape = async () => {
    setScraping(true);
    setScrapeResult(null);
    try {
      const results = await scrapeCompany(companyId);
      setScrapeResult(
        results.length > 0
          ? `Found ${results.length} contact(s)`
          : "No contacts found for this company"
      );
      await load();
    } catch {
      setScrapeResult("Search failed — try again later");
    } finally {
      setScraping(false);
    }
  };

  if (!company) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="company-detail">
      <button className="btn btn-secondary back-btn" onClick={onBack}>
        &larr; Back to list
      </button>

      <div className="detail-header">
        <h2>{company.name}</h2>
        <div className="detail-meta">
          <span className="badge badge-industry">{company.industry}</span>
          <span>{company.city}</span>
          {company.website && (
            <a
              href={company.website}
              target="_blank"
              rel="noopener noreferrer"
              className="detail-link"
            >
              {new URL(company.website).hostname}
            </a>
          )}
        </div>
      </div>

      <div className="scrape-section">
        <button
          className="btn btn-primary"
          onClick={handleScrape}
          disabled={scraping}
        >
          {scraping ? "Finding contacts..." : "Find HR Contacts"}
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => setShowAddContact(!showAddContact)}
        >
          {showAddContact ? "Cancel" : "+ Add Contact"}
        </button>
        {scrapeResult && <span className="scrape-result">{scrapeResult}</span>}
      </div>

      {showAddContact && (
        <div className="add-contact-form">
          <input
            type="email"
            placeholder="Email address *"
            value={newContact.email}
            onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
          />
          <input
            type="text"
            placeholder="Name (optional)"
            value={newContact.name}
            onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
          />
          <input
            type="text"
            placeholder="Job title (optional)"
            value={newContact.title}
            onChange={(e) => setNewContact({ ...newContact, title: e.target.value })}
          />
          <button
            className="btn btn-primary"
            disabled={!newContact.email.trim() || addingContact}
            onClick={async () => {
              setAddingContact(true);
              await addContact(companyId, newContact);
              setNewContact({ email: "", name: "", title: "" });
              setShowAddContact(false);
              setAddingContact(false);
              load();
            }}
          >
            {addingContact ? "Adding..." : "Add Contact"}
          </button>
        </div>
      )}

      <div className="emails-section">
        <h3>HR Contacts ({company.hr_emails.length})</h3>
        {company.hr_emails.length === 0 ? (
          <p className="no-emails">
            No contacts found yet. Click "Find HR Contacts" to search for
            decision makers at this company.
          </p>
        ) : (
          <>
            <table className="email-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Confidence</th>
                  <th>Source</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {company.hr_emails.map((e, i) => (
                  <>
                    <tr key={i}>
                      <td>
                        <a href={`mailto:${e.email}`} className="email-link">
                          {e.email}
                        </a>
                      </td>
                      <td>
                        <span className={`badge badge-${e.confidence}`}>
                          {e.confidence}
                        </span>
                      </td>
                      <td className="source-cell">{e.source}</td>
                      <td>
                        <button
                          className="btn btn-compose"
                          onClick={() =>
                            setComposingFor(composingFor === i ? null : i)
                          }
                        >
                          {composingFor === i ? "Close" : "Compose"}
                        </button>
                      </td>
                    </tr>
                    {composingFor === i && (
                      <tr key={`composer-${i}`}>
                        <td colSpan={4} className="composer-cell">
                          <EmailComposer
                            companyId={companyId}
                            contact={e}
                            onSent={load}
                          />
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>

      {outreach.length > 0 && (
        <div className="outreach-section">
          <h3>Outreach History ({outreach.length})</h3>
          <table className="email-table">
            <thead>
              <tr>
                <th>To</th>
                <th>Subject</th>
                <th>Type</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {outreach.map((o) => (
                <tr key={o.id}>
                  <td>{o.to_email}</td>
                  <td>{o.subject}</td>
                  <td>
                    <span className="badge badge-type">{o.email_type}</span>
                  </td>
                  <td>
                    {o.replied ? (
                      <span className="badge badge-high">Replied</span>
                    ) : o.next_follow_up_at ? (
                      <span className="badge badge-medium" title={`Follow-up on ${new Date(o.next_follow_up_at).toLocaleDateString()}`}>
                        Pending
                      </span>
                    ) : (
                      <span className="badge badge-low">Done</span>
                    )}
                  </td>
                  <td className="source-cell">
                    {new Date(o.sent_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
