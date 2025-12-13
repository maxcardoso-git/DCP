const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8110/api/v2/dcp";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

export async function listDecisions(status = "pending_human_review", limit = 50, offset = 0) {
  return request(
    `/decisions?status=${encodeURIComponent(status)}&limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(
      offset
    )}`
  );
}

export async function createDecisionGate(payload) {
  return request(`/decision-gates`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function approveDecision(id, payload) {
  return request(`/decisions/${id}/approve`, { method: "POST", body: JSON.stringify(payload) });
}

export async function rejectDecision(id, payload) {
  return request(`/decisions/${id}/reject`, { method: "POST", body: JSON.stringify(payload) });
}

export async function escalateDecision(id, payload) {
  return request(`/decisions/${id}/escalate`, { method: "POST", body: JSON.stringify(payload) });
}

export async function modifyDecision(id, payload) {
  return request(`/decisions/${id}/modify`, { method: "POST", body: JSON.stringify(payload) });
}
