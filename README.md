# Decision Control Plane (DCP) – v2

Independent, API-first control-plane application that governs, supervises, and orchestrates human- and AI-driven decisions alongside Orchestrator AI. Ships with SSO-only auth, multi-language UX (en default; pt-BR, es), and explicit human-in-the-loop governance.

## Goals
- Introduce explicit human-in-the-loop decision governance with auditability
- Provide pausable/resumable decision points with policy-driven escalation
- Increase enterprise trust in agentic workflows via TRiSM/PRISM signals
- Escalate based on risk, confidence, and cost signals
- Non-goals: run automations, manage identities, replace Orchestrator runtime

## Architecture
- Style: microservices, event-driven, API-first; deployed as a sidecar platform application (control-plane integration pattern).
- Core components: Decision Control API, Decision State Store (PostgreSQL), Policy Engine, I18n Service, Event Publisher, Admin UI.
- Integration with Orchestrator: bidirectional via REST and async events (webhook/event bus). Consumes execution context, agent outputs, TRiSM risk, PRISM cost, and flow metadata. Provides pause/resume/override and human approval events.
- Security: SSO via Orchestrator (OIDC/OAuth2); RBAC derived from Orchestrator claims; encryption in transit/at rest.

## Runtime & Governance
- Decision lifecycle: created → pending_human_review → approved/rejected/modified/escalated → expired → executed.
- Pause/resume: pause orchestration on gate creation; resume via event; idempotent semantics required.
- Policy Engine inputs: risk_score, confidence_score, estimated_cost, impact_level, compliance_flags. Outputs: auto_approve, require_human, force_escalation.
- Human review actions: approve, reject, modify, escalate; SLA-aware.
- Audit & traceability: decision versioning, actor trace, timestamped events, immutable logs.

## API (base path `/api/v2/dcp`)
- REST: POST `/decision-gates`, GET `/decisions?status=pending`, POST `/decisions/{id}/approve|reject|modify|escalate`. See `docs/api/openapi.yaml`.
- Async events: publishes pause/resume/override/human-approval events to Orchestrator; see `docs/api/events.md`.

## Data Model (PostgreSQL)
- decision: id (uuid), execution_id (uuid), flow_id, node_id, status (enum), language, risk_score (float), confidence_score (float), estimated_cost (decimal), created_at, expires_at.
- decision_recommendation: decision_id, summary (text), detailed_explanation (jsonb), model_used, prompt_version.
- decision_action: id, decision_id, action_type (enum), actor_type (enum), actor_id, comment, created_at.
- decision_policy_snapshot: decision_id, policy_version, evaluated_rules (jsonb), result.

## Internationalization
- Key-based i18n with JSON storage; bundles in `i18n/en.json`, `i18n/pt-BR.json`, `i18n/es.json`. Example: key `decision.approve` maps to localized strings.
- Admin UI ships a language switch; backend negotiates via `Accept-Language` with fallback to default (en). See `docs/i18n/README.md`.

## Policy Engine
- JSON-based rule DSL for auto_approve, require_human, force_escalation; see `docs/policy/dsl.md`.
- Inputs: risk_score, confidence_score, estimated_cost, impact_level, compliance_flags, execution metadata.
- Persisted policy snapshots on each gate for audit and replay.

## Events
- Outbound: `dcp.decision.paused`, `dcp.decision.actioned`, `dcp.decision.expired`, `dcp.decision.resumed`.
- Inbound: `orchestrator.execution.context`, `orchestrator.signal.trism`, `orchestrator.signal.prism`, `orchestrator.execution.resume.ack`.
- Contracts and examples in `docs/api/events.md`.

## Deployment (docs container)
- Build and serve docs via Docker/nginx: `docker build -t dcp-docs .` then `docker run -d -p 8080:80 dcp-docs`.
- Compose shortcut: `docker compose up -d` (see `compose.yaml`); override port with `PORT=8081 docker compose up -d` if 8080 is busy.
- Details in `docs/deploy.md`.

## Non-functional & Observability
- Availability: 99.9%. Latency targets: decision creation ≤200 ms, decision action ≤300 ms.
- Scalability: horizontal, stateless services.
- Metrics: pending_decisions, sla_breaches, auto_vs_human_ratio. Logs: decision_events, policy_evaluations.

## Roadmap Alignment
- v2 focus: policy-driven escalation, multi-language UI, TRiSM + PRISM integration.
- v3 outlook: learning from human decisions, approval reduction via confidence modeling, advanced explainability.
