import { useState, useEffect } from "react";
import { fetchCompanies, fetchIndustries, fetchCities, fetchCounties } from "../api";
import "./CompanyList.css";

export default function CompanyList({ onSelect, onAdd }) {
  const [companies, setCompanies] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [cities, setCities] = useState([]);
  const [counties, setCounties] = useState([]);
  const [search, setSearch] = useState("");
  const [industry, setIndustry] = useState("");
  const [city, setCity] = useState("");
  const [county, setCounty] = useState("");
  const [sortBy, setSortBy] = useState("name");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchIndustries().then(setIndustries);
    fetchCities().then(setCities);
    fetchCounties().then(setCounties);
  }, []);

  useEffect(() => {
    setLoading(true);
    const timeout = setTimeout(() => {
      fetchCompanies(search, industry, city, county).then((data) => {
        setCompanies(data);
        setLoading(false);
      });
    }, 200);
    return () => clearTimeout(timeout);
  }, [search, industry, city, county]);

  const sortedCompanies = [...companies].sort((a, b) => {
    if (sortBy === "newest") {
      return (b.id || 0) - (a.id || 0); // Higher ID = newer
    }
    return (a.name || "").localeCompare(b.name || "");
  });

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
        <select
          value={county}
          onChange={(e) => setCounty(e.target.value)}
          className="industry-select"
        >
          <option value="">All Counties</option>
          {counties.map((c) => (
            <option key={c} value={c}>
              {c} County
            </option>
          ))}
        </select>
        <select
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="industry-select"
        >
          <option value="">All Cities</option>
          {cities.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="industry-select"
        >
          <option value="name">Sort: A-Z</option>
          <option value="newest">Sort: Newest First</option>
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
          {sortedCompanies.map((c) => (
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
              {c.description && (
                <p className="card-desc">{c.description}</p>
              )}
              {c.website && (
                <a
                  href={c.website.startsWith("http") ? c.website : `https://${c.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card-url"
                  onClick={(e) => e.stopPropagation()}
                >
                  {c.website.replace(/^https?:\/\//, "").replace(/^www\./, "")}
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
