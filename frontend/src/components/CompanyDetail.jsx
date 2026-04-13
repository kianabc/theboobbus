import { useState, useEffect } from "react";
import {
  fetchCompany, scrapeCompany, fetchOutreachHistory,
  addContact, updateCompany, deleteContact, deleteCompany,
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
      description: company.description || "",
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

  const handleDeleteCompany = async () => {
    const contactCount = company.hr_emails.length;
    const outreachCount = outreach.length;

    // Confirmation 1
    if (!confirm(
      `Are you sure you want to delete "${company.name}"?\n\n` +
      `This will permanently delete:\n` +
      `- ${contactCount} contact(s)\n` +
      `- ${outreachCount} sent email(s)\n` +
      `- All saved drafts\n\n` +
      `This action CANNOT be undone.`
    )) return;

    // Confirmation 2
    if (!confirm(
      `FINAL WARNING: You are about to permanently delete "${company.name}" and ALL related data.\n\n` +
      `Type OK below to confirm you understand this is irreversible.`
    )) return;

    // Confirmation 3
    const typed = prompt(`Type the company name "${company.name}" to confirm deletion:`);
    if (typed !== company.name) {
      alert("Company name didn't match. Deletion cancelled.");
      return;
    }

    try {
      await deleteCompany(companyId);
      alert(`"${company.name}" has been deleted.`);
      onBack();
    } catch (e) {
      alert("Failed to delete: " + e.message);
    }
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
            <label>
              Description
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                rows={3}
                className="edit-description"
              />
            </label>
            <div className="edit-actions">
              <button className="btn btn-primary" onClick={handleSaveEdit} disabled={savingEdit}>
                {savingEdit ? "Saving..." : "Save"}
              </button>
              <button className="btn btn-secondary" onClick={() => setEditing(false)}>Cancel</button>
              <button className="btn btn-danger" onClick={handleDeleteCompany}>
                Delete Company
              </button>
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
                <th>Name</th>
                <th>Title</th>
                <th>Source</th>
                <th>Confidence</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {company.hr_emails.map((e, i) => {
                const contacted = contactedEmails.has(e.email);
                // Parse "Source - Name, Title" from source string
                const s = e.source || "";
                const dashIdx = s.indexOf(" - ");
                let sourceName = "";
                let sourceTitle = "";
                let sourceOrigin = s;
                if (dashIdx !== -1) {
                  sourceOrigin = s.substring(0, dashIdx);
                  const rest = s.substring(dashIdx + 3);
                  const commaIdx = rest.indexOf(", ");
                  if (commaIdx !== -1) {
                    sourceName = rest.substring(0, commaIdx);
                    sourceTitle = rest.substring(commaIdx + 2);
                  } else {
                    sourceName = rest;
                  }
                }
                return (
                  <>
                    <tr key={i}>
                      <td>
                        <a href={`mailto:${e.email}`} className="email-link">{e.email}</a>
                      </td>
                      <td className="name-cell">{sourceName || "-"}</td>
                      <td className="title-cell">{sourceTitle || "-"}</td>
                      <td className="source-cell">{sourceOrigin}</td>
                      <td>
                        <span className={`badge badge-${e.confidence}`}>{e.confidence}</span>
                      </td>
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
                        <td colSpan={7} className="composer-cell">
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
