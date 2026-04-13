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

export async function fetchCities() {
  const res = await authFetch(`${API}/api/cities`);
  return res.json();
}

export async function fetchCounties() {
  const res = await authFetch(`${API}/api/counties`);
  return res.json();
}

export async function fetchCompanies(search = "", industry = "", city = "", county = "") {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  if (industry) params.set("industry", industry);
  if (city) params.set("city", city);
  if (county) params.set("county", county);
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

export async function sendEmail(data, gmailToken = null) {
  const headers = { "Content-Type": "application/json" };
  if (gmailToken) headers["X-Gmail-Token"] = gmailToken;
  const res = await authFetch(`${API}/api/send-email`, {
    method: "POST",
    headers,
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

export async function deleteCompany(companyId) {
  const res = await authFetch(`${API}/api/companies/${companyId}`, {
    method: "DELETE",
  });
  return res.json();
}

export async function updateContact(contactId, data) {
  const res = await authFetch(`${API}/api/contacts/${contactId}`, {
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

export async function getDraft(companyId, contactEmail) {
  const res = await authFetch(`${API}/api/companies/${companyId}/draft/${encodeURIComponent(contactEmail)}`);
  return res.json();
}

export async function saveDraft(companyId, data) {
  const res = await authFetch(`${API}/api/companies/${companyId}/draft`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function startTestSequence(data) {
  const res = await authFetch(`${API}/api/test-sequence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function gmailAuthorize(code, redirectUri) {
  const res = await authFetch(`${API}/api/gmail/authorize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  });
  return res.json();
}

export async function gmailStatus() {
  const res = await authFetch(`${API}/api/gmail/status`);
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
