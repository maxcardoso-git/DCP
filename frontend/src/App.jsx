import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { approveDecision, authStorage, createDecisionGate, escalateDecision, getSession, listDecisions, modifyDecision, rejectDecision } from "./api";
import { getTranslation, supportedLangs } from "./i18n";

/**
 * TAH Callback Handler Component
 * Handles the redirect from TAH after SSO authentication.
 */
function TahCallback() {
  const [status, setStatus] = useState("processing"); // processing, success, error
  const [error, setError] = useState("");

  useEffect(() => {
    const processCallback = async () => {
      try {
        // Get token from URL
        const params = new URLSearchParams(window.location.search);
        const token = params.get("token");

        if (!token) {
          setStatus("error");
          setError("Token not found in URL");
          setTimeout(() => {
            window.location.href = "/";
          }, 3000);
          return;
        }

        console.log("TAH callback - token received");

        // Store the TAH token
        authStorage.setToken(token);

        setStatus("success");

        // Validate token by calling session endpoint
        try {
          await getSession();
          console.log("TAH session validated");
        } catch (e) {
          console.warn("Session validation failed, but token stored:", e.message);
        }

        // Redirect to main page
        setTimeout(() => {
          window.location.href = "/";
        }, 1000);
      } catch (err) {
        console.error("TAH callback error:", err);
        setStatus("error");
        setError(err.message || "Authentication error");

        // Clear any partial auth state
        authStorage.clearToken();

        setTimeout(() => {
          window.location.href = "/";
        }, 3000);
      }
    };

    processCallback();
  }, []);

  return (
    <div className="tah-callback-page">
      <div className="tah-callback-content">
        {status === "processing" && (
          <div className="tah-status">
            <div className="spinner"></div>
            <h2>Authenticating...</h2>
            <p>Processing TAH login</p>
          </div>
        )}

        {status === "success" && (
          <div className="tah-status success">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h2>Authenticated!</h2>
            <p>Redirecting...</p>
          </div>
        )}

        {status === "error" && (
          <div className="tah-status error">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M15 9l-6 6M9 9l6 6" />
            </svg>
            <h2>Authentication Error</h2>
            <p className="error-message">{error}</p>
            <p>Redirecting to login...</p>
          </div>
        )}
      </div>
    </div>
  );
}

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

function HowItWorksModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>How it Works</h2>
          <button className="modal-close" onClick={onClose}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="modal-body">
          <section className="modal-section">
            <h3>Decision Control Plane (DCP)</h3>
            <p>
              O DCP e um sistema de controle de decisoes que permite implementar <strong>human-in-the-loop</strong> em
              fluxos automatizados. Ele atua como um "gate" que pausa a execucao ate que uma decisao seja tomada
              por um humano ou pelo sistema de politicas.
            </p>
          </section>

          <section className="modal-section">
            <h3>Conceitos Principais</h3>
            <div className="concept-grid">
              <div className="concept-item">
                <div className="concept-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <strong>Decision Gate</strong>
                  <p>Ponto de pausa no fluxo onde uma decisao e necessaria</p>
                </div>
              </div>
              <div className="concept-item">
                <div className="concept-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <div>
                  <strong>Policy Engine</strong>
                  <p>Motor de regras que avalia automaticamente se uma decisao pode ser auto-aprovada</p>
                </div>
              </div>
              <div className="concept-item">
                <div className="concept-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <strong>Actions</strong>
                  <p>Approve, Reject, Escalate ou Modify - acoes disponiveis para cada decisao</p>
                </div>
              </div>
              <div className="concept-item">
                <div className="concept-icon">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                </div>
                <div>
                  <strong>Events</strong>
                  <p>Notificacoes em tempo real via Redis Pub/Sub quando decisoes sao criadas ou alteradas</p>
                </div>
              </div>
            </div>
          </section>

          <section className="modal-section">
            <h3>Integracao com OrchestratorAI</h3>
            <p>
              O DCP foi projetado para integrar perfeitamente com o <strong>OrchestratorAI</strong>,
              permitindo que agentes de IA pausem sua execucao em pontos criticos para revisao humana.
            </p>

            <div className="integration-flow">
              <div className="flow-step">
                <div className="step-number">1</div>
                <div className="step-content">
                  <strong>Agente Executa</strong>
                  <p>O agente do OrchestratorAI processa uma tarefa e identifica um ponto de decisao</p>
                </div>
              </div>
              <div className="flow-arrow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </div>
              <div className="flow-step">
                <div className="step-number">2</div>
                <div className="step-content">
                  <strong>Cria Decision Gate</strong>
                  <p>POST /api/v2/dcp/decision-gates com contexto da decisao</p>
                </div>
              </div>
              <div className="flow-arrow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </div>
              <div className="flow-step">
                <div className="step-number">3</div>
                <div className="step-content">
                  <strong>Humano Decide</strong>
                  <p>Revisao e acao via esta interface ou API</p>
                </div>
              </div>
              <div className="flow-arrow">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </div>
              <div className="flow-step">
                <div className="step-number">4</div>
                <div className="step-content">
                  <strong>Agente Continua</strong>
                  <p>Webhook ou polling notifica o agente para continuar</p>
                </div>
              </div>
            </div>
          </section>

          <section className="modal-section">
            <h3>API Endpoints</h3>
            <div className="api-list">
              <div className="api-item">
                <code className="api-method post">POST</code>
                <code className="api-path">/api/v2/dcp/decision-gates</code>
                <span className="api-desc">Criar nova decisao pendente</span>
              </div>
              <div className="api-item">
                <code className="api-method get">GET</code>
                <code className="api-path">/api/v2/dcp/decisions</code>
                <span className="api-desc">Listar decisoes</span>
              </div>
              <div className="api-item">
                <code className="api-method post">POST</code>
                <code className="api-path">/api/v2/dcp/decisions/{"{id}"}/approve</code>
                <span className="api-desc">Aprovar decisao</span>
              </div>
              <div className="api-item">
                <code className="api-method post">POST</code>
                <code className="api-path">/api/v2/dcp/decisions/{"{id}"}/reject</code>
                <span className="api-desc">Rejeitar decisao</span>
              </div>
              <div className="api-item">
                <code className="api-method post">POST</code>
                <code className="api-path">/api/v2/dcp/decisions/{"{id}"}/escalate</code>
                <span className="api-desc">Escalar decisao</span>
              </div>
              <div className="api-item">
                <code className="api-method post">POST</code>
                <code className="api-path">/api/v2/dcp/decisions/{"{id}"}/modify</code>
                <span className="api-desc">Modificar decisao</span>
              </div>
            </div>
          </section>

          <section className="modal-section">
            <h3>Exemplo de Integracao</h3>
            <pre className="code-block">
{`// OrchestratorAI - Criar Decision Gate
const response = await fetch('/api/v2/dcp/decision-gates', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    execution_id: "uuid-da-execucao",
    flow_id: "payment-approval",
    node_id: "high-value-check",
    risk_score: 0.75,
    confidence_score: 0.82,
    estimated_cost: 5000.00,
    recommendation: {
      summary: "Transacao de alto valor requer aprovacao",
      detailed_explanation: {
        reasoning: ["Valor acima do limite", "Cliente novo"]
      }
    }
  })
});

const decision = await response.json();
// decision.id -> usar para polling ou webhook`}
            </pre>
          </section>
        </div>
      </div>
    </div>
  );
}

function DecisionInbox() {
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
  const [showHowItWorks, setShowHowItWorks] = useState(false);

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
            <button className="btn-how-it-works" onClick={() => setShowHowItWorks(true)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3" />
                <path d="M12 17h.01" />
              </svg>
              How it Works
            </button>
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

      <HowItWorksModal isOpen={showHowItWorks} onClose={() => setShowHowItWorks(false)} />

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

function App() {
  // Simple routing based on pathname
  const path = window.location.pathname;

  // TAH Callback route
  if (path === "/tah-callback") {
    return <TahCallback />;
  }

  // Main app
  return <DecisionInbox />;
}

export default App;
