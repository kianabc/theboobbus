import { useState, useEffect } from "react";
import { fetchCompany, scrapeCompany } from "../api";
import "./CompanyDetail.css";

export default function CompanyDetail({ companyId, onBack }) {
  const [company, setCompany] = useState(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeResult, setScrapeResult] = useState(null);

  const load = () => fetchCompany(companyId).then(setCompany);

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
          ? `Found ${results.length} email(s)`
          : "No emails found on this website"
      );
      await load();
    } catch {
      setScrapeResult("Scraping failed — try again later");
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
          {scraping ? "Scraping..." : "Scrape for HR Emails"}
        </button>
        {scrapeResult && <span className="scrape-result">{scrapeResult}</span>}
      </div>

      <div className="emails-section">
        <h3>HR Emails ({company.hr_emails.length})</h3>
        {company.hr_emails.length === 0 ? (
          <p className="no-emails">
            No emails found yet. Click "Scrape for HR Emails" to search this
            company's website.
          </p>
        ) : (
          <table className="email-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Confidence</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {company.hr_emails.map((e, i) => (
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
