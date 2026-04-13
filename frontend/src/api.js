const API = "http://localhost:8000";

export async function fetchCompanies(search = "", industry = "") {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (industry) params.set("industry", industry);
  const res = await fetch(`${API}/companies?${params}`);
  return res.json();
}

export async function fetchCompany(id) {
  const res = await fetch(`${API}/companies/${id}`);
  return res.json();
}

export async function fetchIndustries() {
  const res = await fetch(`${API}/industries`);
  return res.json();
}

export async function scrapeCompany(id) {
  const res = await fetch(`${API}/companies/${id}/scrape`, { method: "POST" });
  return res.json();
}

export async function addCompany(data) {
  const res = await fetch(`${API}/companies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchAllEmails(confidence = "") {
  const params = new URLSearchParams();
  if (confidence) params.set("confidence", confidence);
  const res = await fetch(`${API}/emails?${params}`);
  return res.json();
}
