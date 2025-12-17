/**
 * Validation utilities for frontend forms.
 */

/**
 * Validate a comment field.
 * @param {string} comment - Comment to validate
 * @param {number} maxLength - Maximum allowed length
 * @returns {string|null} Error message or null if valid
 */
export function validateComment(comment, maxLength = 1000) {
  if (!comment) return null;

  if (comment.length > maxLength) {
    return `Comment is too long (max ${maxLength} characters)`;
  }

  return null;
}

/**
 * Validate a flow ID.
 * @param {string} flowId - Flow ID to validate
 * @returns {string|null} Error message or null if valid
 */
export function validateFlowId(flowId) {
  if (!flowId || !flowId.trim()) {
    return "Flow ID is required";
  }

  if (flowId.length > 255) {
    return "Flow ID is too long (max 255 characters)";
  }

  if (!/^[\w\-\.]+$/.test(flowId)) {
    return "Flow ID contains invalid characters";
  }

  return null;
}

/**
 * Validate a node ID.
 * @param {string} nodeId - Node ID to validate
 * @returns {string|null} Error message or null if valid
 */
export function validateNodeId(nodeId) {
  if (!nodeId || !nodeId.trim()) {
    return "Node ID is required";
  }

  if (nodeId.length > 255) {
    return "Node ID is too long (max 255 characters)";
  }

  if (!/^[\w\-\.]+$/.test(nodeId)) {
    return "Node ID contains invalid characters";
  }

  return null;
}

/**
 * Validate a score value (0.0 to 1.0).
 * @param {number|string} score - Score to validate
 * @param {string} fieldName - Name of the field for error messages
 * @returns {string|null} Error message or null if valid
 */
export function validateScore(score, fieldName = "Score") {
  if (score === null || score === undefined || score === "") {
    return null; // Optional field
  }

  const numScore = parseFloat(score);

  if (isNaN(numScore)) {
    return `${fieldName} must be a number`;
  }

  if (numScore < 0 || numScore > 1) {
    return `${fieldName} must be between 0 and 1`;
  }

  return null;
}

/**
 * Validate a cost value.
 * @param {number|string} cost - Cost to validate
 * @returns {string|null} Error message or null if valid
 */
export function validateCost(cost) {
  if (cost === null || cost === undefined || cost === "") {
    return null; // Optional field
  }

  const numCost = parseFloat(cost);

  if (isNaN(numCost)) {
    return "Cost must be a number";
  }

  if (numCost < 0) {
    return "Cost cannot be negative";
  }

  return null;
}

/**
 * Validate a UUID.
 * @param {string} uuid - UUID to validate
 * @returns {boolean} True if valid UUID
 */
export function isValidUUID(uuid) {
  if (!uuid) return false;
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

/**
 * Sanitize a string input.
 * @param {string} input - Input to sanitize
 * @param {number} maxLength - Maximum length
 * @returns {string} Sanitized string
 */
export function sanitizeInput(input, maxLength = 1000) {
  if (!input) return "";

  return input
    .toString()
    .slice(0, maxLength)
    .replace(/[<>]/g, "") // Remove potential XSS chars
    .trim();
}

/**
 * Validate an entire decision form.
 * @param {object} form - Form data
 * @returns {object} Object with errors for each invalid field
 */
export function validateDecisionForm(form) {
  const errors = {};

  const flowIdError = validateFlowId(form.flow_id);
  if (flowIdError) errors.flow_id = flowIdError;

  const nodeIdError = validateNodeId(form.node_id);
  if (nodeIdError) errors.node_id = nodeIdError;

  const riskError = validateScore(form.risk_score, "Risk score");
  if (riskError) errors.risk_score = riskError;

  const confidenceError = validateScore(form.confidence_score, "Confidence score");
  if (confidenceError) errors.confidence_score = confidenceError;

  const costError = validateCost(form.estimated_cost);
  if (costError) errors.estimated_cost = costError;

  return errors;
}
