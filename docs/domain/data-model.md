# Data Model – Decision Control Plane v2

Primary store: PostgreSQL. Designed for immutable auditing and idempotent pause/resume semantics.

## Entities
- `decision` — root aggregate keyed by `id` (uuid) and external `execution_id`.
  - Fields: `id`, `execution_id`, `flow_id`, `node_id`, `status`, `language`, `risk_score` (float), `confidence_score` (float), `estimated_cost` (numeric/decimal), `created_at`, `expires_at`.
  - Indexing: unique `(execution_id, node_id)` for idempotent gate creation; secondary indexes on `status`, `expires_at`, and `(language, status)` for inbox filtering.
- `decision_recommendation` — AI-generated recommendation stored as JSON for explainability.
  - Fields: `decision_id` (fk), `summary` (text), `detailed_explanation` (jsonb), `model_used`, `prompt_version`.
  - Indexing: `gin` on `detailed_explanation` for trace queries.
- `decision_action` — append-only log of human/policy actions.
  - Fields: `id` (uuid), `decision_id` (fk), `action_type` (enum), `actor_type` (enum), `actor_id`, `comment`, `payload` (jsonb for structured modifications), `created_at`.
  - Indexing: `(decision_id, created_at)` for timeline queries.
- `decision_policy_snapshot` — captures rules evaluated at gate time for auditability.
  - Fields: `decision_id` (fk), `policy_version`, `evaluated_rules` (jsonb), `result`.
  - Indexing: `gin` on `evaluated_rules`.

## Enums
- `decision.status`: `created`, `pending_human_review`, `approved`, `rejected`, `modified`, `escalated`, `expired`, `executed`.
- `decision_action.action_type`: `approve`, `reject`, `modify`, `escalate`.
- `decision_action.actor_type`: `human`, `system`, `policy`.

## Relationships & Behaviors
- `decision` 1—1 `decision_recommendation`; `decision` 1—N `decision_action`; `decision` 1—1 `decision_policy_snapshot`.
- Immutable append-only `decision_action` enables full trace; `decision.status` reflects latest durable state.
- Language stored on `decision` for consistent rendering; responses may localize via `Accept-Language`.
- Expiration (`expires_at`) supports SLA enforcement; background jobs or Orchestrator callbacks can mark `expired`.

## Governance Considerations
- Use row-level security tied to Orchestrator claims (RBAC).
- Store all timestamps in UTC; rely on database-managed `created_at` defaults.
- Ensure audit logs emitted on every state transition and action insert.
