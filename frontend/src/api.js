const API = import.meta.env.VITE_API_URL ?? "";

function authHeaders() {
  const token = localStorage.getItem("google_token");
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

let reloading = false;
async function authFetch(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { ...authHeaders(), ...options.headers },
  });
  if (res.status === 401 && !reloading) {
    reloading = true;
    localStorage.removeItem("google_token");
    window.location.reload();
    throw new Error("Unauthorized");
  }
  return res;
}

export async function fetchCities() {
  try {
    const res = await authFetch(`${API}/api/cities`);
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch { return []; }
}

export async function fetchCounties() {
  try {
    const res = await authFetch(`${API}/api/counties`);
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch { return []; }
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

export async function generateCompanies(filters) {
  const res = await authFetch(`${API}/api/companies/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(filters),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to generate");
  }
  return res.json();
}

export async function bulkAddCompanies(companies) {
  const res = await authFetch(`${API}/api/companies/bulk`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ companies }),
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

export async function bulkGenerate(data) {
  const res = await authFetch(`${API}/api/bulk-generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to generate drafts");
  }
  return res.json();
}

export async function bulkSend(data) {
  const res = await authFetch(`${API}/api/bulk-send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to send");
  }
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

export async function deleteTestActivity(sentEmailId) {
  const res = await authFetch(`${API}/api/activity/test/${sentEmailId}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete");
  }
  return res.json();
}

export async function deleteAllTestActivity() {
  const res = await authFetch(`${API}/api/activity/test`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to clear tests");
  }
  return res.json();
}

export async function stopSequence(companyId, contactEmail) {
  const res = await authFetch(`${API}/api/companies/${companyId}/stop-sequence`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contact_email: contactEmail }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to stop sequence");
  }
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

export async function gmailDisconnect() {
  const res = await authFetch(`${API}/api/gmail/disconnect`, { method: "DELETE" });
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

export async function fetchEmailModels() {
  const res = await authFetch(`${API}/api/email-models`);
  return res.json();
}

export async function fetchOrgGmailOptions() {
  try {
    const res = await authFetch(`${API}/api/org-gmail/options`);
    if (!res.ok) return [];
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

export async function updateSettings(data) {
  const res = await authFetch(`${API}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}
