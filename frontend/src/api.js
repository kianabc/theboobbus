const API = import.meta.env.VITE_API_URL ?? "";

function authHeaders() {
  const token = localStorage.getItem("google_token");
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function authFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...options.headers },
  });
  if (res.status === 401) {
    localStorage.removeItem("google_token");
    window.location.reload();
    throw new Error("Unauthorized");
  }
  return res;
}

export async function fetchCompanies(search = "", industry = "") {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (industry) params.set("industry", industry);
  const res = await authFetch(`${API}/api/companies?${params}`);
  return res.json();
}

export async function fetchCompany(id) {
  const res = await authFetch(`${API}/api/companies/${id}`);
  return res.json();
}

export async function fetchIndustries() {
  const res = await authFetch(`${API}/api/industries`);
  return res.json();
}

export async function scrapeCompany(id) {
  const res = await authFetch(`${API}/api/companies/${id}/scrape`, { method: "POST" });
  return res.json();
}

export async function addCompany(data) {
  const res = await authFetch(`${API}/api/companies`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchAllEmails(confidence = "") {
  const params = new URLSearchParams();
  if (confidence) params.set("confidence", confidence);
  const res = await authFetch(`${API}/api/emails?${params}`);
  return res.json();
}
