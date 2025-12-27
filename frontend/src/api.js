/**
 * API client for DCP backend.
 * Uses TAH token authentication via Authorization header.
 */

const inferredBase = (() => {
  if (import.meta.env.VITE_API_BASE) return import.meta.env.VITE_API_BASE;
  const host = typeof window !== "undefined" ? window.location.hostname : "localhost";
  return `http://${host}:8110/api/v2/dcp`;
})();

const API_BASE = inferredBase;

/**
 * Token storage utilities.
 */
export const authStorage = {
  getToken: () => localStorage.getItem("access_token"),
  setToken: (token) => {
    if (token) {
      localStorage.setItem("access_token", token);
      localStorage.setItem("auth_source", "tah");
    }
  },
  clearToken: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("auth_source");
  },
  getAuthSource: () => localStorage.getItem("auth_source"),
  isAuthenticated: () => !!localStorage.getItem("access_token"),
};

/**
 * Custom error class for API errors.
 */
export class ApiError extends Error {
  constructor(status, statusText, body) {
    super(`HTTP ${status}: ${statusText}`);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }

  get isUnauthorized() {
    return this.status === 401;
  }

  get isForbidden() {
    return this.status === 403;
  }

  get isNotFound() {
    return this.status === 404;
  }

  get isRateLimited() {
    return this.status === 429;
  }

  get isServerError() {
    return this.status >= 500;
  }

  get userMessage() {
    if (this.isUnauthorized) return "Please log in to continue.";
    if (this.isForbidden) return "You don't have permission to perform this action.";
    if (this.isNotFound) return "The requested resource was not found.";
    if (this.isRateLimited) return "Too many requests. Please try again later.";
    if (this.isServerError) return "Server error. Please try again later.";

    // Try to extract message from body
    if (this.body?.detail) return this.body.detail;
    if (this.body?.message) return this.body.message;

    return "An unexpected error occurred.";
  }
}

/**
 * Make an API request with error handling.
 */
async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = options.timeout || 30000;

  const timeoutId = setTimeout(() => controller.abort(), timeout);

  // Build headers with Authorization if token exists
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  // Add Authorization header if we have a token
  const token = authStorage.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers,
      credentials: "include", // Keep for backwards compatibility
      signal: controller.signal,
      ...options,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let body = null;
      try {
        body = await res.json();
      } catch {
        try {
          body = { detail: await res.text() };
        } catch {
          body = null;
        }
      }

      // If 401, clear stored token
      if (res.status === 401) {
        authStorage.clearToken();
      }

      throw new ApiError(res.status, res.statusText, body);
    }

    // Handle empty responses
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      return res.json();
    }

    return null;
  } catch (err) {
    clearTimeout(timeoutId);

    if (err.name === "AbortError") {
      throw new ApiError(408, "Request Timeout", { detail: "Request timed out" });
    }

    if (err instanceof ApiError) {
      throw err;
    }

    // Network error
    throw new ApiError(0, "Network Error", { detail: err.message });
  }
}

/**
 * Get current session info.
 */
export async function getSession() {
  return request(`/auth/session`);
}

/**
 * Check authentication status.
 */
export async function checkAuth() {
  return request(`/auth/check`);
}

/**
 * List decisions with filters.
 */
export async function listDecisions(status = "pending_human_review", limit = 50, offset = 0) {
  const params = new URLSearchParams({
    status,
    limit: String(limit),
    offset: String(offset),
  });
  return request(`/decisions?${params}`);
}

/**
 * Create a new decision gate.
 */
export async function createDecisionGate(payload) {
  return request(`/decision-gates`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Approve a decision.
 */
export async function approveDecision(id, payload) {
  return request(`/decisions/${encodeURIComponent(id)}/approve`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Reject a decision.
 */
export async function rejectDecision(id, payload) {
  return request(`/decisions/${encodeURIComponent(id)}/reject`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Escalate a decision.
 */
export async function escalateDecision(id, payload) {
  return request(`/decisions/${encodeURIComponent(id)}/escalate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Modify a decision.
 */
export async function modifyDecision(id, payload) {
  return request(`/decisions/${encodeURIComponent(id)}/modify`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Evaluate a policy (dry run).
 */
export async function evaluatePolicy(payload) {
  return request(`/policy/evaluate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Health check.
 */
export async function healthCheck() {
  const res = await fetch(`${API_BASE.replace("/api/v2/dcp", "")}/healthz`);
  return res.ok;
}

export default {
  authStorage,
  getSession,
  checkAuth,
  listDecisions,
  createDecisionGate,
  approveDecision,
  rejectDecision,
  escalateDecision,
  modifyDecision,
  evaluatePolicy,
  healthCheck,
  ApiError,
};
