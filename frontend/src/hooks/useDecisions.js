import { useCallback, useEffect, useState } from "react";
import {
  listDecisions,
  approveDecision,
  rejectDecision,
  escalateDecision,
  modifyDecision,
  createDecisionGate,
} from "../api";

/**
 * Custom hook for managing decisions state and operations.
 *
 * @param {string} initialStatus - Initial status filter
 * @param {number} initialLimit - Initial page size
 * @returns {object} Decision state and operations
 */
export function useDecisions(initialStatus = "pending_human_review", initialLimit = 20) {
  const [decisions, setDecisions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState(initialStatus);
  const [limit] = useState(initialLimit);
  const [offset, setOffset] = useState(0);

  // Fetch decisions from API
  const fetchDecisions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listDecisions(statusFilter, limit, offset);
      setDecisions(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message || "Failed to fetch decisions");
      setDecisions([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, limit, offset]);

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchDecisions();
  }, [fetchDecisions]);

  // Refresh decisions
  const refresh = useCallback(() => {
    setOffset(0);
    fetchDecisions();
  }, [fetchDecisions]);

  // Change status filter
  const changeStatus = useCallback((newStatus) => {
    setStatusFilter(newStatus);
    setOffset(0);
  }, []);

  // Pagination
  const nextPage = useCallback(() => {
    if (offset + limit < total) {
      setOffset((prev) => prev + limit);
    }
  }, [offset, limit, total]);

  const prevPage = useCallback(() => {
    if (offset > 0) {
      setOffset((prev) => Math.max(0, prev - limit));
    }
  }, [offset, limit]);

  // Action handlers
  const handleAction = useCallback(
    async (decisionId, actionFn, payload = {}) => {
      setError(null);
      try {
        await actionFn(decisionId, payload);
        await fetchDecisions();
        return { success: true };
      } catch (err) {
        const errorMessage = err.message || "Action failed";
        setError(errorMessage);
        return { success: false, error: errorMessage };
      }
    },
    [fetchDecisions]
  );

  const approve = useCallback(
    (decisionId, payload) => handleAction(decisionId, approveDecision, payload),
    [handleAction]
  );

  const reject = useCallback(
    (decisionId, payload) => handleAction(decisionId, rejectDecision, payload),
    [handleAction]
  );

  const escalate = useCallback(
    (decisionId, payload) => handleAction(decisionId, escalateDecision, payload),
    [handleAction]
  );

  const modify = useCallback(
    (decisionId, payload) => handleAction(decisionId, modifyDecision, payload),
    [handleAction]
  );

  // Create sample gate
  const createSample = useCallback(
    async (payload) => {
      setError(null);
      try {
        await createDecisionGate(payload);
        await fetchDecisions();
        return { success: true };
      } catch (err) {
        const errorMessage = err.message || "Failed to create decision gate";
        setError(errorMessage);
        return { success: false, error: errorMessage };
      }
    },
    [fetchDecisions]
  );

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    // State
    decisions,
    total,
    loading,
    error,
    statusFilter,
    offset,
    limit,

    // Pagination info
    hasNextPage: offset + limit < total,
    hasPrevPage: offset > 0,
    currentPage: Math.floor(offset / limit) + 1,
    totalPages: Math.ceil(total / limit),

    // Operations
    refresh,
    changeStatus,
    nextPage,
    prevPage,
    approve,
    reject,
    escalate,
    modify,
    createSample,
    clearError,
  };
}

export default useDecisions;
