import { useState } from "react";
import { addCompany, generateCompanies, bulkAddCompanies } from "../api";
import "./AddCompany.css";

export default function AddCompany({ onBack }) {
  const [mode, setMode] = useState("single"); // "single" | "generate"

  return (
    <div className="add-company">
      <button className="btn btn-secondary" onClick={onBack}>
        &larr; Back to list
      </button>

      <div className="add-tabs">
        <button
          className={`add-tab ${mode === "single" ? "active" : ""}`}
          onClick={() => setMode("single")}
        >
          Add one company
        </button>
        <button
          className={`add-tab ${mode === "generate" ? "active" : ""}`}
          onClick={() => setMode("generate")}
        >
          Generate a batch with AI
        </button>
      </div>

      {mode === "single" ? <SingleAdd onBack={onBack} /> : <BatchGenerate onBack={onBack} />}
    </div>
  );
}

function SingleAdd({ onBack }) {
  const [form, setForm] = useState({
    name: "",
    website: "",
    industry: "",
    city: "",
    county: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setError("Company name is required");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await addCompany({
        name: form.name.trim(),
        website: form.website.trim() || null,
        industry: form.industry.trim() || null,
        city: form.city.trim() || "Utah",
        county: form.county.trim() || null,
      });
      onBack();
    } catch {
      setError("Failed to add company");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form className="add-form" onSubmit={handleSubmit}>
      <h2>Add a Company</h2>
      {error && <p className="form-error">{error}</p>}
      <label>
        Company Name *
        <input type="text" value={form.name} onChange={update("name")} placeholder="e.g. Acme Corp" />
      </label>
      <label>
        Website
        <input type="text" value={form.website} onChange={update("website")} placeholder="www.example.com" />
      </label>
      <label>
        Industry
        <input type="text" value={form.industry} onChange={update("industry")} placeholder="e.g. Technology" />
      </label>
      <label>
        City
        <input type="text" value={form.city} onChange={update("city")} placeholder="e.g. Salt Lake City" />
      </label>
      <label>
        County
        <input type="text" value={form.county} onChange={update("county")} placeholder="e.g. Salt Lake" />
      </label>
      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting ? "Adding..." : "Add Company"}
      </button>
    </form>
  );
}

function BatchGenerate({ onBack }) {
  const [filters, setFilters] = useState({
    count: 10,
    city: "",
    county: "",
    industry: "",
    min_employees: 50,
    prioritize_women: false,
    avoid_keywords: "",
  });
  const [loading, setLoading] = useState(false);
  const [proposed, setProposed] = useState(null); // array or null
  const [selected, setSelected] = useState({}); // name -> bool
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const updateF = (field) => (e) => {
    const val = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setFilters((f) => ({ ...f, [field]: val }));
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setProposed(null);
    setStatus("");
    try {
      const payload = {
        count: Math.max(1, Math.min(25, parseInt(filters.count) || 10)),
        city: filters.city.trim() || null,
        county: filters.county.trim() || null,
        industry: filters.industry.trim() || null,
        min_employees: parseInt(filters.min_employees) || null,
        prioritize_women: filters.prioritize_women,
        avoid_keywords: filters.avoid_keywords
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      const result = await generateCompanies(payload);
      setProposed(result);
      // Default-select verified, non-duplicate rows
      const initial = {};
      result.forEach((c) => {
        initial[c.name] = c.website_verified && !c.already_exists;
      });
      setSelected(initial);
    } catch (err) {
      setError(err.message || "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const toggleAll = (value) => {
    const next = {};
    (proposed || []).forEach((c) => {
      next[c.name] = value && !c.already_exists;
    });
    setSelected(next);
  };

  const handleSave = async () => {
    if (!proposed) return;
    const toAdd = proposed
      .filter((c) => selected[c.name] && !c.already_exists)
      .map((c) => ({
        name: c.name,
        website: c.website || null,
        industry: c.industry || null,
        city: c.city || "Utah",
        county: c.county || null,
      }));
    if (toAdd.length === 0) {
      setError("Select at least one company to add.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await bulkAddCompanies(toAdd);
      setStatus(`Added ${res.added} companies.${res.skipped ? ` Skipped ${res.skipped} duplicates.` : ""}`);
      setTimeout(onBack, 900);
    } catch {
      setError("Failed to save companies.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="batch-generate">
      <form className="add-form" onSubmit={handleGenerate}>
        <h2>Generate a batch with AI</h2>
        <p className="batch-hint">
          Claude picks real Utah companies matching your filters. Websites are auto-verified and
          duplicates flagged. You review before saving.
        </p>
        {error && <p className="form-error">{error}</p>}

        <label>
          How many?
          <input type="number" min="1" max="25" value={filters.count} onChange={updateF("count")} />
        </label>
        <label>
          City (optional)
          <input type="text" value={filters.city} onChange={updateF("city")} placeholder="e.g. Logan" />
        </label>
        <label>
          County (optional)
          <input type="text" value={filters.county} onChange={updateF("county")} placeholder="e.g. Cache" />
        </label>
        <label>
          Industry (optional)
          <input type="text" value={filters.industry} onChange={updateF("industry")} placeholder="e.g. Healthcare" />
        </label>
        <label>
          Minimum employee count
          <input type="number" min="0" value={filters.min_employees} onChange={updateF("min_employees")} />
        </label>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={filters.prioritize_women}
            onChange={updateF("prioritize_women")}
          />
          Prioritize women-heavy workforces (healthcare, education, nonprofits, etc.)
        </label>
        <label>
          Avoid (comma-separated keywords)
          <input
            type="text"
            value={filters.avoid_keywords}
            onChange={updateF("avoid_keywords")}
            placeholder="e.g. tobacco, firearms"
          />
        </label>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? "Generating..." : "Generate"}
        </button>
      </form>

      {proposed && (
        <div className="batch-results">
          <div className="batch-results-header">
            <h3>
              Proposed companies ({proposed.length})
            </h3>
            <div className="batch-results-actions">
              <button className="btn btn-secondary" onClick={() => toggleAll(true)}>Select all</button>
              <button className="btn btn-secondary" onClick={() => toggleAll(false)}>Clear</button>
            </div>
          </div>
          {status && <p className="batch-status">{status}</p>}
          <ul className="batch-list">
            {proposed.map((c) => (
              <li key={c.name} className={`batch-item ${c.already_exists ? "duplicate" : ""}`}>
                <label className="batch-item-check">
                  <input
                    type="checkbox"
                    checked={!!selected[c.name]}
                    disabled={c.already_exists}
                    onChange={(e) =>
                      setSelected((s) => ({ ...s, [c.name]: e.target.checked }))
                    }
                  />
                </label>
                <div className="batch-item-body">
                  <div className="batch-item-title">
                    <strong>{c.name}</strong>
                    <span className="batch-item-meta">
                      {[c.industry, c.city, c.county && `${c.county} County`]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </div>
                  {c.website && (
                    <a
                      href={c.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="batch-item-link"
                    >
                      {c.website}
                    </a>
                  )}
                  <div className="batch-item-badges">
                    {c.website_verified ? (
                      <span className="badge badge-ok">✓ Website verified</span>
                    ) : (
                      <span className="badge badge-warn">⚠ Website unreachable</span>
                    )}
                    {c.already_exists && <span className="badge badge-dup">Already in DB</span>}
                    {c.estimated_employees && (
                      <span className="badge badge-info">~{c.estimated_employees} employees</span>
                    )}
                  </div>
                  {c.reasoning && <p className="batch-item-reason">{c.reasoning}</p>}
                </div>
              </li>
            ))}
          </ul>
          <div className="batch-save-row">
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : `Save selected (${Object.values(selected).filter(Boolean).length})`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
