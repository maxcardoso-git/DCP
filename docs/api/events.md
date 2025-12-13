# Event Contracts – Decision Control Plane v2

Channel: Orchestrator event bus or signed webhooks. Envelope: CloudEvents 1.0 recommended (`id`, `type`, `source`, `specversion`, `time`, `datacontenttype`, `traceparent`, `data`). Idempotency via `id` + `traceparent` + `idempotency_key` (in `data.meta`).

## Outbound events (DCP → Orchestrator)

### `dcp.decision.paused`
- Emitted when a decision gate is created and orchestration is paused.
- `data`:
  - `decision_id`, `execution_id`, `flow_id`, `node_id`
  - `status`: `pending_human_review`
  - `language`
  - `risk_score`, `confidence_score`, `estimated_cost`, `impact_level`, `compliance_flags`
  - `recommendation.summary`, `recommendation.detailed_explanation`
  - `policy.result`, `policy.policy_version`, `policy.evaluated_rules`
  - `sla.expires_at`
  - `meta.idempotency_key`, `meta.trace_id`

Example:
```json
{
  "id": "c9c8f8cb-51b7-4e0c-9e1e-bb9d1c5a28ea",
  "type": "dcp.decision.paused",
  "source": "dcp",
  "specversion": "1.0",
  "time": "2024-12-13T20:10:00Z",
  "datacontenttype": "application/json",
  "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
  "data": {
    "decision_id": "d3c891da-6e3b-4b84-b6c9-5ee2dddb4c35",
    "execution_id": "1f3c9c77-2b2c-4b62-97f2-0b2b12ec11f0",
    "flow_id": "customer-onboarding",
    "node_id": "kyc-check",
    "status": "pending_human_review",
    "language": "en",
    "risk_score": 0.82,
    "confidence_score": 0.64,
    "estimated_cost": 12.5,
    "impact_level": "high",
    "compliance_flags": ["aml", "pep"],
    "recommendation": {
      "summary": "Block onboarding pending AML review.",
      "detailed_explanation": {"reasoning": ["Detected PEP match", "Low model confidence"]},
      "model_used": "orchestrator-guard-v5",
      "prompt_version": "2024-12-01"
    },
    "policy": {
      "result": "require_human",
      "policy_version": "v2.0.0",
      "evaluated_rules": [{"id": "aml-pep", "outcome": "require_human"}]
    },
    "sla": {"expires_at": "2024-12-13T20:40:00Z"},
    "meta": {
      "idempotency_key": "execution:1f3c9c77-kyc-check",
      "trace_id": "0af7651916cd43dd8448eb211c80319c"
    }
  }
}
```

### `dcp.decision.actioned`
- Emitted when a human/system/policy takes an action.
- `data`:
  - `decision_id`, `execution_id`, `flow_id`, `node_id`
  - `action`: `approve` | `reject` | `modify` | `escalate` | `override`
  - `actor.type`: `human` | `system` | `policy`
  - `actor.id`
  - `comment`
  - `modifications` (when action is `modify` or `override`)
  - `policy.result` (if re-evaluated)
  - `resume_token` (idempotent resume key to unblock orchestration)
  - `meta.idempotency_key`, `meta.trace_id`

Example:
```json
{
  "id": "e7c1993d-9c81-4d1e-a4eb-68724a86118a",
  "type": "dcp.decision.actioned",
  "source": "dcp",
  "specversion": "1.0",
  "time": "2024-12-13T20:20:00Z",
  "traceparent": "00-0af7651916cd43dd8448eb211c80319c-1111b67169203331-01",
  "data": {
    "decision_id": "d3c891da-6e3b-4b84-b6c9-5ee2dddb4c35",
    "execution_id": "1f3c9c77-2b2c-4b62-97f2-0b2b12ec11f0",
    "flow_id": "customer-onboarding",
    "node_id": "kyc-check",
    "action": "approve",
    "actor": {"type": "human", "id": "user-42"},
    "comment": "Verified PEP match is false positive.",
    "resume_token": "resume-1f3c9c77-kyc-check-001",
    "meta": {"idempotency_key": "decision-action:d3c891da:approve"}
  }
}
```

### `dcp.decision.expired`
- Emitted when `expires_at` is reached without action.
- `data`: `decision_id`, `execution_id`, `flow_id`, `node_id`, `status`: `expired`, `sla.expires_at`, `meta.idempotency_key`.

### `dcp.decision.resumed`
- Emitted after Orchestrator acknowledges resume and continues execution.
- `data`: `decision_id`, `execution_id`, `flow_id`, `node_id`, `resume_token`, `previous_action`.

## Inbound events (Orchestrator → DCP)
- `orchestrator.execution.context` — execution metadata, agent outputs, flow metadata required for policy evaluation.
- `orchestrator.signal.trism` — risk signals; fields `execution_id`, `flow_id`, `risk_score`, `impact_level`, `compliance_flags`, `trace_id`.
- `orchestrator.signal.prism` — cost signals; fields `execution_id`, `estimated_cost`, `currency`, `trace_id`.
- `orchestrator.execution.resume.ack` — acknowledgement that orchestration resumed using provided `resume_token`.

## Delivery & idempotency
- Deduplicate by `id` or `meta.idempotency_key`; treat replays as no-ops.
- All events must carry `traceparent` for distributed tracing.
- Webhooks: sign payload (e.g., HMAC-SHA256) with shared secret; include `X-DCP-Signature`, `X-DCP-Timestamp`.

## Topics/paths (suggested)
- Bus topics: `dcp.decision.*` (outbound), `orchestrator.execution.*`, `orchestrator.signal.*` (inbound).
- Webhook paths (if Orchestrator hosts): `/hooks/dcp/decision` (receives outbound events), `/hooks/orchestrator/*` (sends inbound events to DCP).
