import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { approveDecision, createDecisionGate, escalateDecision, listDecisions, modifyDecision, rejectDecision } from "./api";
import { getTranslation, supportedLangs } from "./i18n";

const initialGate = {
  flow_id: "sample-flow",
  node_id: "checkpoint-1",
  language: "en",
  risk_score: 0.42,
  confidence_score: 0.68,
  estimated_cost: 12.5,
  recommendation: {
    summary: "Sample recommendation (replace with real payload).",
    detailed_explanation: { reasoning: ["Example only"] },
    model_used: "demo-model",
    prompt_version: "v0",
  },
  policy_snapshot: {
    policy_version: "v2.0.0",
    evaluated_rules: [{ id: "demo", outcome: "require_human" }],
    result: "require_human",
  },
};

function App() {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lang, setLang] = useState("en");
  const [creating, setCreating] = useState(false);
  const [comment, setComment] = useState("");

  const t = (key) => getTranslation(lang, key);

  const statusText = (status) => t(`status.${status}`) || status;

  const fetchDecisions = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listDecisions();
      setDecisions(data.items || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDecisions();
  }, []);

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
      const payload = {
        ...initialGate,
        language: lang,
        execution_id: crypto.randomUUID(),
      };
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
        <div>
          <p className="eyebrow">Decision Control Plane · v2</p>
          <h1>{t("decision.inbox")}</h1>
          <p className="muted">
            API-connected inbox for human-in-the-loop decisions. Use the sample gate to simulate incoming pauses or call the
            API directly.
          </p>
        </div>
        <div className="controls">
          <select value={lang} onChange={(e) => setLang(e.target.value)}>
            {supportedLangs.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          <button onClick={fetchDecisions} disabled={loading}>
            Refresh
          </button>
          <button onClick={createSampleGate} disabled={creating}>
            {creating ? "Creating…" : "Create sample gate"}
          </button>
        </div>
      </header>

      {error && <div className="banner error">{error}</div>}

      <div className="comment-box">
        <label>{t("action.comment.placeholder")}</label>
        <textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder={t("action.comment.placeholder")} />
      </div>

      {loading ? (
        <div className="muted">Loading decisions…</div>
      ) : (
        <div className="cards">
          {sorted.length === 0 ? (
            <div className="muted">No decisions yet.</div>
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
                  <button onClick={() => handleAction(d.id, approveDecision)}>{t("decision.approve")}</button>
                  <button onClick={() => handleAction(d.id, rejectDecision)}>{t("decision.reject")}</button>
                  <button onClick={() => handleAction(d.id, escalateDecision)}>{t("decision.escalate")}</button>
                  <button
                    onClick={() =>
                      handleAction(d.id, modifyDecision, { modifications: { note: "modified", comment } || {} })
                    }
                  >
                    {t("decision.modify")}
                  </button>
                </div>
                <div className="timeline">
                  {d.actions?.length ? (
                    d.actions.map((a) => (
                      <div key={a.id} className="timeline-item">
                        <span className="badge ghost">{a.action_type}</span>
                        <span className="muted">
                          {a.actor_type} {a.actor_id ? `· ${a.actor_id}` : ""} ·{" "}
                          {new Date(a.created_at).toLocaleString()}
                        </span>
                        {a.comment && <p>{a.comment}</p>}
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
