import { useState } from "react";
import { addCompany } from "../api";
import "./AddCompany.css";

export default function AddCompany({ onBack }) {
  const [form, setForm] = useState({
    name: "",
    website: "",
    industry: "",
    city: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const update = (field) => (e) =>
    setForm({ ...form, [field]: e.target.value });

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
      });
      onBack();
    } catch {
      setError("Failed to add company");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="add-company">
      <button className="btn btn-secondary" onClick={onBack}>
        &larr; Back to list
      </button>

      <form className="add-form" onSubmit={handleSubmit}>
        <h2>Add a Company</h2>

        {error && <p className="form-error">{error}</p>}

        <label>
          Company Name *
          <input
            type="text"
            value={form.name}
            onChange={update("name")}
            placeholder="e.g. Acme Corp"
          />
        </label>

        <label>
          Website
          <input
            type="url"
            value={form.website}
            onChange={update("website")}
            placeholder="https://www.example.com"
          />
        </label>

        <label>
          Industry
          <input
            type="text"
            value={form.industry}
            onChange={update("industry")}
            placeholder="e.g. Technology"
          />
        </label>

        <label>
          City
          <input
            type="text"
            value={form.city}
            onChange={update("city")}
            placeholder="e.g. Salt Lake City"
          />
        </label>

        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Adding..." : "Add Company"}
        </button>
      </form>
    </div>
  );
}
