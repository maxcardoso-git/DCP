# Policy DSL & Evaluation – DCP v2

Lightweight JSON-based DSL to decide when to auto-approve, require human review, or force escalation. Inputs are the policy engine fields: `risk_score`, `confidence_score`, `estimated_cost`, `impact_level`, `compliance_flags`, and any execution metadata from Orchestrator (e.g., `business_unit`, `customer_tier`).

## Rule shape
```json
{
  "version": "2.0.0",
  "rules": [
    {
      "id": "risk-high",
      "description": "Escalate when risk is high",
      "when": {"any": [{"gte": ["{{risk_score}}", 0.8]}, {"in": ["critical", "{{impact_level}}"]}]},
      "then": {"result": "force_escalation", "reason": "High risk/impact"}
    },
    {
      "id": "low-risk-high-confidence",
      "description": "Auto-approve low risk + high confidence",
      "when": {"all": [{"lte": ["{{risk_score}}", 0.2]}, {"gte": ["{{confidence_score}}", 0.8]}]},
      "then": {"result": "auto_approve"}
    },
    {
      "id": "cost-guardrail",
      "description": "Require human if estimated cost exceeds threshold",
      "when": {"gt": ["{{estimated_cost}}", 1000]},
      "then": {"result": "require_human", "reason": "High cost"}
    },
    {
      "id": "compliance-flag",
      "description": "Force escalation on compliance hits",
      "when": {"includes": ["{{compliance_flags}}", "aml"]},
      "then": {"result": "force_escalation", "reason": "AML flagged"}
    }
  ],
  "default": {"result": "require_human", "reason": "No rule matched"}
}
```

## Operators
- `all`: every condition true.
- `any`: at least one condition true.
- Comparators: `gt`, `gte`, `lt`, `lte`, `eq`, `neq`.
- Collections: `includes` (array contains value), `missing` (null/undefined).

## Evaluation semantics
- Evaluate rules top-down; first match wins.
- `result` values map to engine outputs: `auto_approve`, `require_human`, `force_escalation`.
- Persist the evaluated rule set as `decision_policy_snapshot` for audit and replay.
- If a later human action occurs, optionally re-evaluate rules with updated inputs and log the new snapshot.

## Examples
### Risk + confidence gate
```
if risk_score >= 0.8 -> force_escalation
else if risk_score <= 0.2 and confidence_score >= 0.8 -> auto_approve
else -> require_human
```

### Cost + impact composite
```
if estimated_cost > 10_000 or impact_level in [high, critical] -> force_escalation
else if estimated_cost < 500 and impact_level == low -> auto_approve
else -> require_human
```

### Compliance guardrail
```
if compliance_flags contains aml or privacy_high -> force_escalation
```

## Data contract (policy_snapshot)
- `policy_version`: semantic version of the rule set.
- `evaluated_rules`: array of `{ id, outcome, reason }`.
- `result`: final decision outcome.
