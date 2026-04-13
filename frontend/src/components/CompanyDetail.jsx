import { useState, useEffect } from "react";
import {
  fetchCompany, scrapeCompany, fetchOutreachHistory,
  addContact, updateCompany, deleteContact,
} from "../api";
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
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [savingEdit, setSavingEdit] = useState(false);

  const load = () => {
    fetchCompany(companyId).then(setCompany);
    fetchOutreachHistory(companyId).then(setOutreach);
  };

  useEffect(() => { load(); }, [companyId]);

  const handleScrape = async () => {
    setScraping(true);
    setScrapeResult(null);
    try {
      const results = await scrapeCompany(companyId);
      setScrapeResult(results.length > 0 ? `Found ${results.length} contact(s)` : "No contacts found");
      load();
    } catch {
      setScrapeResult("Search failed");
    } finally {
      setScraping(false);
    }
  };

  const handleAddContact = async () => {
    if (!newContact.email.trim()) return;
    setAddingContact(true);
    try {
      await addContact(companyId, {
        email: newContact.email.trim(),
        name: newContact.name.trim() || null,
        title: newContact.title.trim() || null,
      });
      setNewContact({ email: "", name: "", title: "" });
      setShowAddContact(false);
      load();
    } catch (e) {
      console.error("Add contact failed:", e);
    } finally {
      setAddingContact(false);
    }
  };

  const handleStartEdit = () => {
    setEditForm({
      name: company.name,
      website: company.website || "",
      industry: company.industry || "",
      city: company.city || "",
    });
    setEditing(true);
  };

  const handleSaveEdit = async () => {
    setSavingEdit(true);
    try {
      const result = await updateCompany(companyId, editForm);
      if (result.id) {
        setEditing(false);
        load();
      } else {
        alert("Update failed: " + JSON.stringify(result));
      }
    } catch (e) {
      alert("Update failed: " + e.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleDeleteContact = async (contactId, email) => {
    if (!confirm(`Delete contact ${email}?`)) return;
    await deleteContact(contactId);
    load();
  };

  if (!company) return <div className="loading">Loading...</div>;

  const contactedEmails = new Set(outreach.map((o) => o.to_email));

  return (
    <div className="company-detail">
      <button className="btn btn-secondary back-btn" onClick={onBack}>
        &larr; Back to list
      </button>

      {/* ── Company Header ── */}
      <div className="detail-header">
        {editing ? (
          <div className="edit-company-form">
            <label>
              Name
              <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
            </label>
            <label>
              Website
              <input value={editForm.website} onChange={(e) => setEditForm({ ...editForm, website: e.target.value })} />
            </label>
            <label>
              Industry
              <input value={editForm.industry} onChange={(e) => setEditForm({ ...editForm, industry: e.target.value })} />
            </label>
            <label>
              City
              <input value={editForm.city} onChange={(e) => setEditForm({ ...editForm, city: e.target.value })} />
            </label>
            <div className="edit-actions">
              <button className="btn btn-primary" onClick={handleSaveEdit} disabled={savingEdit}>
                {savingEdit ? "Saving..." : "Save"}
              </button>
              <button className="btn btn-secondary" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          </div>
        ) : (
          <>
            <div className="detail-title-row">
              <h2>{company.name}</h2>
              <button className="btn btn-edit" onClick={handleStartEdit}>Edit</button>
            </div>
            <div className="detail-meta">
              <span className="badge badge-industry">{company.industry}</span>
              <span>{company.city}</span>
              {company.website && (
                <a href={company.website.startsWith("http") ? company.website : `https://${company.website}`} target="_blank" rel="noopener noreferrer" className="detail-link">
                  {company.website.replace(/^https?:\/\//, "")}
                </a>
              )}
            </div>
            {company.description && (
              <p className="detail-desc">{company.description}</p>
            )}
          </>
        )}
      </div>

      {/* ── Actions ── */}
      <div className="scrape-section">
        <button className="btn btn-primary" onClick={handleScrape} disabled={scraping}>
          {scraping ? "Finding contacts..." : "Find HR Contacts"}
        </button>
        <button className="btn btn-secondary" onClick={() => setShowAddContact(!showAddContact)}>
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
            onClick={handleAddContact}
          >
            {addingContact ? "Adding..." : "Add"}
          </button>
        </div>
      )}

      {/* ── Contacts Table ── */}
      <div className="emails-section">
        <h3>HR Contacts ({company.hr_emails.length})</h3>
        {company.hr_emails.length === 0 ? (
          <p className="no-emails">
            No contacts found yet. Click "Find HR Contacts" or "+ Add Contact".
          </p>
        ) : (
          <table className="email-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Confidence</th>
                <th>Source</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {company.hr_emails.map((e, i) => {
                const contacted = contactedEmails.has(e.email);
                return (
                  <>
                    <tr key={i}>
                      <td>
                        <a href={`mailto:${e.email}`} className="email-link">{e.email}</a>
                      </td>
                      <td>
                        <span className={`badge badge-${e.confidence}`}>{e.confidence}</span>
                      </td>
                      <td className="source-cell">{e.source}</td>
                      <td>
                        {contacted ? (
                          <span className="badge badge-contacted">Contacted</span>
                        ) : (
                          <span className="badge badge-not-contacted">Not contacted</span>
                        )}
                      </td>
                      <td className="actions-cell">
                        {contacted ? (
                          <span className="contacted-check">Sent</span>
                        ) : (
                          <button className="btn btn-compose" onClick={() => setComposingFor(composingFor === i ? null : i)}>
                            {composingFor === i ? "Close" : "Compose"}
                          </button>
                        )}
                        <button
                          className="btn btn-delete-sm"
                          onClick={() => handleDeleteContact(e.id, e.email)}
                          title="Delete contact"
                        >
                          &times;
                        </button>
                      </td>
                    </tr>
                    {composingFor === i && !contacted && (
                      <tr key={`composer-${i}`}>
                        <td colSpan={5} className="composer-cell">
                          <EmailComposer companyId={companyId} contact={e} onSent={load} />
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Outreach History ── */}
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
                  <td><span className="badge badge-type">{o.email_type}</span></td>
                  <td>
                    {o.replied ? (
                      <span className="badge badge-high">Replied</span>
                    ) : o.next_follow_up_at ? (
                      <span className="badge badge-medium" title={`Follow-up on ${new Date(o.next_follow_up_at).toLocaleDateString()}`}>Pending</span>
                    ) : (
                      <span className="badge badge-low">Done</span>
                    )}
                  </td>
                  <td className="source-cell">{new Date(o.sent_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
