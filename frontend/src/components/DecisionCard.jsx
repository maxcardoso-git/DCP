import { useState } from "react";

/**
 * Card component for displaying a single decision.
 */
function DecisionCard({
  decision,
  onApprove,
  onReject,
  onEscalate,
  onModify,
  statusText,
  t,
}) {
  const [actionLoading, setActionLoading] = useState(null);
  const [comment, setComment] = useState("");

  const handleAction = async (action, actionFn) => {
    setActionLoading(action);
    try {
      await actionFn(decision.id, { comment });
      setComment("");
    } finally {
      setActionLoading(null);
    }
  };

  const isLoading = actionLoading !== null;

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <p className="eyebrow">
            Flow: {decision.flow_id} · Node: {decision.node_id}
          </p>
          <h3>{decision.recommendation?.summary || t("decision.details")}</h3>
        </div>
        <span className={`badge status-${decision.status}`}>
          {statusText(decision.status)}
        </span>
      </div>

      <div className="meta">
        <span title="Risk Score">
          Risk: {decision.risk_score?.toFixed(2) ?? "—"}
        </span>
        <span title="Confidence Score">
          Conf: {decision.confidence_score?.toFixed(2) ?? "—"}
        </span>
        <span title="Estimated Cost">
          Cost: {decision.estimated_cost != null ? `$${decision.estimated_cost}` : "—"}
        </span>
        <span title="Language">Lang: {decision.language}</span>
      </div>

      {decision.recommendation?.detailed_explanation && (
        <details className="explanation-details">
          <summary>View explanation</summary>
          <pre className="explanation">
            {JSON.stringify(decision.recommendation.detailed_explanation, null, 2)}
          </pre>
        </details>
      )}

      <div className="card-comment">
        <input
          type="text"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder={t("action.comment.placeholder")}
          disabled={isLoading}
          maxLength={1000}
        />
      </div>

      <div className="actions">
        <button
          onClick={() => handleAction("approve", onApprove)}
          disabled={isLoading}
          className="btn-approve"
        >
          {actionLoading === "approve" ? "..." : t("decision.approve")}
        </button>
        <button
          onClick={() => handleAction("reject", onReject)}
          disabled={isLoading}
          className="btn-reject"
        >
          {actionLoading === "reject" ? "..." : t("decision.reject")}
        </button>
        <button
          onClick={() => handleAction("escalate", onEscalate)}
          disabled={isLoading}
          className="btn-escalate"
        >
          {actionLoading === "escalate" ? "..." : t("decision.escalate")}
        </button>
        <button
          onClick={() =>
            handleAction("modify", (id, payload) =>
              onModify(id, { ...payload, modifications: { note: "modified" } })
            )
          }
          disabled={isLoading}
          className="btn-modify"
        >
          {actionLoading === "modify" ? "..." : t("decision.modify")}
        </button>
      </div>

      <div className="timeline">
        <h4>Action History</h4>
        {decision.actions?.length ? (
          decision.actions.map((action) => (
            <div key={action.id} className="timeline-item">
              <span className="badge ghost">{action.action_type}</span>
              <span className="muted">
                {action.actor_type}
                {action.actor_id ? ` · ${action.actor_id}` : ""} ·{" "}
                {new Date(action.created_at).toLocaleString()}
              </span>
              {action.comment && <p className="action-comment">{action.comment}</p>}
            </div>
          ))
        ) : (
          <p className="muted">No actions yet.</p>
        )}
      </div>
    </div>
  );
}

export default DecisionCard;
