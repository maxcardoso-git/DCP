"""
Policy loader utilities for loading policies from files or dictionaries.
"""
import json
import logging
from pathlib import Path
from typing import Optional

from .engine import PolicyEngine
from .exceptions import PolicyLoadError

logger = logging.getLogger("dcp.policy")


def load_policy_from_file(path: str | Path) -> PolicyEngine:
    """
    Load a policy from a JSON file.

    Args:
        path: Path to the policy JSON file

    Returns:
        PolicyEngine instance

    Raises:
        PolicyLoadError: If the file cannot be loaded or parsed
    """
    path = Path(path)

    if not path.exists():
        raise PolicyLoadError(f"Policy file not found: {path}")

    if not path.suffix == ".json":
        raise PolicyLoadError(f"Policy file must be JSON: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            policy_dict = json.load(f)
    except json.JSONDecodeError as e:
        raise PolicyLoadError(f"Invalid JSON in policy file {path}: {e}")
    except IOError as e:
        raise PolicyLoadError(f"Cannot read policy file {path}: {e}")

    logger.info(f"Loaded policy from {path}, version: {policy_dict.get('version', 'unknown')}")
    return PolicyEngine(policy_dict)


def load_policy_from_dict(policy_dict: dict) -> PolicyEngine:
    """
    Load a policy from a dictionary.

    Args:
        policy_dict: Policy definition dictionary

    Returns:
        PolicyEngine instance

    Raises:
        PolicyLoadError: If the dictionary is invalid
    """
    if not isinstance(policy_dict, dict):
        raise PolicyLoadError("Policy must be a dictionary")

    return PolicyEngine(policy_dict)


def get_default_policy() -> dict:
    """
    Get the default policy definition.

    This is used when no custom policy is configured.

    Returns:
        Default policy dictionary
    """
    return {
        "version": "2.0.0",
        "description": "Default DCP policy with heuristic rules",
        "rules": [
            {
                "id": "compliance-flag",
                "description": "Force escalation when compliance flags are present",
                "when": {"exists": ["{{compliance_flags}}"]},
                "then": {
                    "result": "force_escalation",
                    "reason": "Compliance flag present"
                }
            },
            {
                "id": "high-risk",
                "description": "Force escalation for high risk scores",
                "when": {"gte": ["{{risk_score}}", 0.8]},
                "then": {
                    "result": "force_escalation",
                    "reason": "High risk score"
                }
            },
            {
                "id": "auto-approve-low-risk",
                "description": "Auto approve low risk, high confidence, low cost",
                "when": {
                    "all": [
                        {"lte": ["{{risk_score}}", 0.2]},
                        {"gte": ["{{confidence_score}}", 0.8]},
                        {
                            "any": [
                                {"missing": ["{{estimated_cost}}"]},
                                {"lte": ["{{estimated_cost}}", 500]}
                            ]
                        }
                    ]
                },
                "then": {
                    "result": "auto_approve",
                    "reason": "Low risk with high confidence"
                }
            }
        ],
        "default": {
            "result": "require_human",
            "reason": "Default: requires human review"
        }
    }


_cached_engine: Optional[PolicyEngine] = None


def get_policy_engine(policy_path: Optional[str] = None, reload: bool = False) -> PolicyEngine:
    """
    Get or create the policy engine singleton.

    Args:
        policy_path: Optional path to custom policy file
        reload: Force reload even if cached

    Returns:
        PolicyEngine instance
    """
    global _cached_engine

    if _cached_engine is not None and not reload:
        return _cached_engine

    if policy_path:
        try:
            _cached_engine = load_policy_from_file(policy_path)
            return _cached_engine
        except PolicyLoadError as e:
            logger.warning(f"Failed to load policy from {policy_path}: {e}, using default")

    # Use default policy
    _cached_engine = load_policy_from_dict(get_default_policy())
    return _cached_engine
