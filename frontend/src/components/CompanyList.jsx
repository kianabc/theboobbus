import { useState, useEffect } from "react";
import { fetchCompanies, fetchIndustries } from "../api";
import "./CompanyList.css";

export default function CompanyList({ onSelect, onAdd }) {
  const [companies, setCompanies] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [search, setSearch] = useState("");
  const [industry, setIndustry] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIndustries().then(setIndustries);
  }, []);

  useEffect(() => {
    setLoading(true);
    const timeout = setTimeout(() => {
      fetchCompanies(search, industry).then((data) => {
        setCompanies(data);
        setLoading(false);
      });
    }, 200);
    return () => clearTimeout(timeout);
  }, [search, industry]);

  return (
    <div className="company-list">
      <div className="list-toolbar">
        <input
          type="text"
          placeholder="Search companies..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />
        <select
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          className="industry-select"
        >
          <option value="">All Industries</option>
          {industries.map((ind) => (
            <option key={ind} value={ind}>
              {ind}
            </option>
          ))}
        </select>
        <button className="btn btn-primary" onClick={onAdd}>
          + Add Company
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading companies...</div>
      ) : companies.length === 0 ? (
        <div className="empty">No companies found.</div>
      ) : (
        <div className="company-grid">
          {companies.map((c) => (
            <div
              key={c.id}
              className="company-card"
              onClick={() => onSelect(c.id)}
            >
              <div className="card-top">
                <h3>{c.name}</h3>
                {c.email_count > 0 && (
                  <span className="email-indicator" title={`${c.email_count} contact(s) found`}>
                    {c.email_count}
                  </span>
                )}
              </div>
              <div className="card-meta">
                <span className="badge badge-industry">{c.industry}</span>
                <span className="card-city">{c.city}</span>
              </div>
              {c.website && (
                <a
                  href={c.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card-url"
                  onClick={(e) => e.stopPropagation()}
                >
                  {new URL(c.website).hostname}
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
