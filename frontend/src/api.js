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

export async function generateEmail(data) {
  const res = await authFetch(`${API}/api/generate-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function sendEmail(data, gmailToken) {
  const res = await authFetch(`${API}/api/send-email`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Gmail-Token": gmailToken,
    },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchOutreachHistory(companyId) {
  const res = await authFetch(`${API}/api/companies/${companyId}/outreach`);
  return res.json();
}

export async function updateCompany(companyId, data) {
  const res = await authFetch(`${API}/api/companies/${companyId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function deleteContact(contactId) {
  const res = await authFetch(`${API}/api/contacts/${contactId}`, {
    method: "DELETE",
  });
  return res.json();
}

export async function addContact(companyId, data) {
  const res = await authFetch(`${API}/api/companies/${companyId}/contacts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function fetchSettings() {
  const res = await authFetch(`${API}/api/settings`);
  return res.json();
}

export async function updateSettings(data) {
  const res = await authFetch(`${API}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}
