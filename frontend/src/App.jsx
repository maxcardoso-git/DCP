import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { approveDecision, createDecisionGate, escalateDecision, listDecisions, modifyDecision, rejectDecision } from "./api";
import { getTranslation, supportedLangs } from "./i18n";

const genUuid = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

// Counter for sample gates
let sampleGateCounter = 0;

const createSamplePayload = (lang, counter) => ({
  flow_id: "demo-flow",
  node_id: `checkpoint-${counter}`,
  language: lang,
  execution_id: genUuid(),
  risk_score: parseFloat((0.1 + Math.random() * 0.3).toFixed(2)),
  confidence_score: parseFloat((0.5 + Math.random() * 0.1).toFixed(2)),
  estimated_cost: parseFloat((100 + counter * 0.1).toFixed(1)),
  recommendation: {
    summary: `Sample gate ${counter}`,
    detailed_explanation: { reasoning: ["sample", `gate ${counter}`] },
    model_used: "demo-model",
    prompt_version: "v0",
  },
  policy_snapshot: {
    policy_version: "v2.0.0",
    evaluated_rules: [{ id: "demo", outcome: "require_human" }],
    result: "require_human",
  },
});

function App() {
  const [decisions, setDecisions] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lang, setLang] = useState("en");
  const [statusFilter, setStatusFilter] = useState("pending_human_review");
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);
  const [creating, setCreating] = useState(false);
  const [comment, setComment] = useState("");

  const t = (key) => getTranslation(lang, key);
  const statusText = (status) => t(`status.${status}`) || status.replace(/_/g, " ");

  const fetchDecisions = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listDecisions(statusFilter, limit, offset);
      setDecisions(data.items || []);
      setTotal(data.total || 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, [statusFilter, offset]);

  const handleAction = async (id, actionFn, extraPayload = {}) => {
    try {
      await actionFn(id, { comment, ...extraPayload });
      setComment("");
      fetchDecisions();
    } catch (e) {
      setError(e.message);
    }
  };

  const createSampleGate = async () => {
    setCreating(true);
    setError("");
    try {
      sampleGateCounter++;
      const payload = createSamplePayload(lang, sampleGateCounter);
      await createDecisionGate(payload);
      await fetchDecisions();
    } catch (e) {
      setError(e.message);
    } finally {
      setCreating(false);
    }
  };

  const sorted = useMemo(
    () => decisions.slice().sort((a, b) => new Date(b.created_at) - new Date(a.created_at)),
    [decisions]
  );

  return (
    <div className="page">
      <header>
        <div className="brand">
          <img src="/logo.png" alt="DCP logo" className="logo" />
          <div>
            <p className="eyebrow">Decision Control Plane · v2</p>
            <h1>{t("decision.inbox")}</h1>
            <p className="muted">
              API-connected inbox for human-in-the-loop decisions. Use the sample gate to simulate incoming pauses or call the API directly.
            </p>
          </div>
        </div>
        <div className="controls">
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            {supportedLangs.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            {["pending_human_review", "approved", "rejected", "modified", "escalated", "expired", "executed"].map((s) => (
              <option key={s} value={s}>
                {statusText(s)}
              </option>
            ))}
          </select>
          <button onClick={() => { setOffset(0); fetchDecisions(); }} disabled={loading}>
            Refresh
          </button>
          <button onClick={createSampleGate} disabled={creating}>
            {creating ? "Creating..." : "Create sample gate"}
          </button>
        </div>
      </header>

      {error && <div className="banner error">{error}</div>}

      <div className="comment-box">
        <label>Add a comment (optional)</label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Add a comment (optional)"
        />
      </div>

      <div className="pagination">
        <span className="muted">
          Showing {decisions.length} of {total} ({statusText(statusFilter)})
        </span>
        <div className="controls">
          <button disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - limit))}>
            Prev
          </button>
          <button disabled={offset + limit >= total || loading} onClick={() => setOffset(offset + limit)}>
            Next
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-text">Loading decisions...</div>
      ) : (
        <div className="cards">
          {sorted.length === 0 ? (
            <div className="empty-state">No decisions yet.</div>
          ) : (
            sorted.map((d) => (
              <div key={d.id} className="card">
                <div className="card-header">
                  <div>
                    <p className="eyebrow">
                      Flow: {d.flow_id} · Node: {d.node_id}
                    </p>
                    <h3>{d.recommendation?.summary || t("decision.details")}</h3>
                  </div>
                  <span className={`badge status-${d.status}`}>{statusText(d.status)}</span>
                </div>

                <div className="meta">
                  <span>Risk: {d.risk_score ?? "—"}</span>
                  <span>Confidence: {d.confidence_score ?? "—"}</span>
                  <span>Cost: {d.estimated_cost ?? "—"}</span>
                  <span>Lang: {d.language}</span>
                </div>

                <pre className="explanation">
                  {JSON.stringify(d.recommendation?.detailed_explanation || {}, null, 2)}
                </pre>

                <div className="actions">
                  <button onClick={() => handleAction(d.id, approveDecision)}>
                    {t("decision.approve")}
                  </button>
                  <button onClick={() => handleAction(d.id, rejectDecision)}>
                    {t("decision.reject")}
                  </button>
                  <button onClick={() => handleAction(d.id, escalateDecision)}>
                    {t("decision.escalate")}
                  </button>
                  <button onClick={() => handleAction(d.id, modifyDecision, { modifications: { note: "modified", comment } || {} })}>
                    {t("decision.modify")}
                  </button>
                </div>

                <div className="timeline">
                  {d.actions?.length ? (
                    d.actions.map((a) => (
                      <div key={a.id} className="timeline-item">
                        <span className="badge ghost">{a.action_type}</span>
                        <span className="muted">
                          {a.actor_type} {a.actor_id ? `· ${a.actor_id}` : ""} · {new Date(a.created_at).toLocaleString()}
                        </span>
                        {a.comment && <p className="action-comment">{a.comment}</p>}
                      </div>
                    ))
                  ) : (
                    <p className="muted">No actions yet.</p>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default App;
