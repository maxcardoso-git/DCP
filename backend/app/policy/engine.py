"""
Policy Engine for evaluating JSON-based DSL rules.

Supports:
- Comparison operators: gt, gte, lt, lte, eq, neq
- Logical operators: all, any
- Collection operators: includes, in, missing, exists
- Template variable substitution: {{variable_name}}
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .operators import get_operator, is_operator
from .exceptions import PolicyEvaluationError, InvalidConditionError

logger = logging.getLogger("dcp.policy")

# Pattern to match template variables like {{risk_score}}
TEMPLATE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


@dataclass
class PolicyResult:
    """Result of policy evaluation."""

    result: str  # auto_approve, require_human, force_escalation
    reason: str
    matched_rule_id: Optional[str] = None
    evaluated_rules: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "result": self.result,
            "reason": self.reason,
            "matched_rule_id": self.matched_rule_id,
            "evaluated_rules": self.evaluated_rules,
        }


class PolicyEngine:
    """
    Engine for evaluating JSON-based policy rules.

    Rules are evaluated top-down, first match wins.

    Example policy:
    {
        "version": "2.0.0",
        "rules": [
            {
                "id": "high-risk",
                "when": {"gte": ["{{risk_score}}", 0.8]},
                "then": {"result": "force_escalation", "reason": "High risk"}
            }
        ],
        "default": {"result": "require_human", "reason": "No rule matched"}
    }
    """

    def __init__(self, policy: dict):
        """
        Initialize the policy engine.

        Args:
            policy: Policy definition dictionary
        """
        self.version = policy.get("version", "1.0.0")
        self.rules = policy.get("rules", [])
        self.default = policy.get("default", {
            "result": "require_human",
            "reason": "No rule matched",
        })

    def evaluate(self, context: dict) -> PolicyResult:
        """
        Evaluate the policy against the given context.

        Args:
            context: Dictionary of values to evaluate against (e.g., risk_score, confidence_score)

        Returns:
            PolicyResult with the evaluation outcome
        """
        evaluated_rules = []

        for rule in self.rules:
            rule_id = rule.get("id", "unknown")
            condition = rule.get("when", {})
            then = rule.get("then", {})

            try:
                matched = self._evaluate_condition(condition, context)
                evaluated_rules.append({
                    "id": rule_id,
                    "matched": matched,
                    "outcome": then.get("result") if matched else None,
                })

                if matched:
                    logger.debug(f"Rule {rule_id} matched for context {context}")
                    return PolicyResult(
                        result=then.get("result", "require_human"),
                        reason=then.get("reason", f"Rule {rule_id} matched"),
                        matched_rule_id=rule_id,
                        evaluated_rules=evaluated_rules,
                    )

            except PolicyEvaluationError as e:
                logger.warning(f"Error evaluating rule {rule_id}: {e}")
                evaluated_rules.append({
                    "id": rule_id,
                    "matched": False,
                    "error": str(e),
                })
                continue

        # No rule matched, return default
        logger.debug(f"No rule matched for context {context}, using default")
        return PolicyResult(
            result=self.default.get("result", "require_human"),
            reason=self.default.get("reason", "No rule matched"),
            matched_rule_id=None,
            evaluated_rules=evaluated_rules,
        )

    def _evaluate_condition(self, condition: dict, context: dict) -> bool:
        """
        Recursively evaluate a condition against the context.

        Args:
            condition: Condition dictionary (e.g., {"gte": ["{{risk_score}}", 0.8]})
            context: Context dictionary with values

        Returns:
            True if condition is satisfied, False otherwise
        """
        if not condition:
            return True

        if not isinstance(condition, dict):
            raise InvalidConditionError(condition, "Condition must be a dictionary")

        # Handle logical operators
        if "all" in condition:
            subconditions = condition["all"]
            if not isinstance(subconditions, list):
                raise InvalidConditionError(condition, "'all' requires a list of conditions")
            return all(self._evaluate_condition(c, context) for c in subconditions)

        if "any" in condition:
            subconditions = condition["any"]
            if not isinstance(subconditions, list):
                raise InvalidConditionError(condition, "'any' requires a list of conditions")
            return any(self._evaluate_condition(c, context) for c in subconditions)

        # Handle comparison/collection operators
        for op_name, args in condition.items():
            if not is_operator(op_name):
                raise InvalidConditionError(condition, f"Unknown operator: {op_name}")

            operator = get_operator(op_name)

            # Handle unary operators (missing, exists)
            if op_name in ("missing", "exists"):
                if isinstance(args, str):
                    value = self._resolve_value(args, context)
                elif isinstance(args, list) and len(args) >= 1:
                    value = self._resolve_value(args[0], context)
                else:
                    value = args
                return operator(value, None)

            # Handle binary operators
            if not isinstance(args, list) or len(args) < 2:
                raise InvalidConditionError(
                    condition,
                    f"Operator {op_name} requires a list of [left, right] operands"
                )

            left = self._resolve_value(args[0], context)
            right = self._resolve_value(args[1], context)

            return operator(left, right)

        return True

    def _resolve_value(self, value: Any, context: dict) -> Any:
        """
        Resolve a value, substituting template variables.

        Args:
            value: Value to resolve (may contain {{variable}} templates)
            context: Context dictionary for variable substitution

        Returns:
            Resolved value
        """
        if not isinstance(value, str):
            return value

        # Check for template pattern
        match = TEMPLATE_PATTERN.match(value)
        if match:
            var_name = match.group(1)
            return context.get(var_name)

        # Check for partial template in string
        def replace_var(m):
            var_name = m.group(1)
            val = context.get(var_name, "")
            return str(val) if val is not None else ""

        if TEMPLATE_PATTERN.search(value):
            return TEMPLATE_PATTERN.sub(replace_var, value)

        return value


def create_engine_from_dict(policy: dict) -> PolicyEngine:
    """Create a PolicyEngine from a dictionary."""
    return PolicyEngine(policy)
