from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


DecisionStatus = str
ActionType = str
ActorType = str

# Validation constants
MAX_FLOW_ID_LENGTH = 255
MAX_NODE_ID_LENGTH = 255
MAX_LANGUAGE_LENGTH = 10
MAX_COMMENT_LENGTH = 5000
MAX_SUMMARY_LENGTH = 2000
MAX_COMPLIANCE_FLAGS = 50
MAX_ACTOR_ID_LENGTH = 255


class DecisionRecommendationIn(BaseModel):
    summary: Optional[str] = Field(None, max_length=MAX_SUMMARY_LENGTH)
    detailed_explanation: Optional[dict[str, Any]] = None
    model_used: Optional[str] = Field(None, max_length=100)
    prompt_version: Optional[str] = Field(None, max_length=50)
    model_config = ConfigDict(protected_namespaces=())


class DecisionPolicySnapshotIn(BaseModel):
    policy_version: Optional[str] = Field(None, max_length=50)
    evaluated_rules: Optional[list[dict[str, Any]] | dict[str, Any]] = None
    result: Optional[str] = Field(None, max_length=50)


class DecisionCreate(BaseModel):
    execution_id: UUID
    flow_id: str = Field(..., min_length=1, max_length=MAX_FLOW_ID_LENGTH)
    node_id: str = Field(..., min_length=1, max_length=MAX_NODE_ID_LENGTH)
    language: str = Field(default="en", max_length=MAX_LANGUAGE_LENGTH)
    risk_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    estimated_cost: Optional[float] = Field(None, ge=0.0)
    impact_level: Optional[str] = Field(None, max_length=50)
    compliance_flags: Optional[list[str]] = None
    recommendation: DecisionRecommendationIn
    policy_snapshot: Optional[DecisionPolicySnapshotIn] = None
    expires_at: Optional[datetime] = None

    @field_validator("flow_id", "node_id")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate flow_id and node_id contain safe characters."""
        import re
        if not re.match(r"^[\w\-\.]+$", v):
            raise ValueError("Must contain only alphanumeric characters, dashes, underscores, or dots")
        return v

    @field_validator("compliance_flags")
    @classmethod
    def validate_compliance_flags(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate compliance flags list."""
        if v is None:
            return None
        if len(v) > MAX_COMPLIANCE_FLAGS:
            raise ValueError(f"Too many compliance flags (max {MAX_COMPLIANCE_FLAGS})")
        # Sanitize each flag
        return [flag[:100].strip() for flag in v if flag and flag.strip()]

    @field_validator("impact_level")
    @classmethod
    def validate_impact_level(cls, v: Optional[str]) -> Optional[str]:
        """Validate impact level is one of allowed values."""
        if v is None:
            return None
        allowed = {"low", "medium", "high", "critical"}
        if v.lower() not in allowed:
            raise ValueError(f"impact_level must be one of: {', '.join(allowed)}")
        return v.lower()


class DecisionActionIn(BaseModel):
    actor_id: Optional[str] = Field(None, max_length=MAX_ACTOR_ID_LENGTH)
    actor_type: ActorType = Field(default="human", max_length=20)
    comment: Optional[str] = Field(None, max_length=MAX_COMMENT_LENGTH)
    language: Optional[str] = Field(None, max_length=MAX_LANGUAGE_LENGTH)

    @field_validator("actor_type")
    @classmethod
    def validate_actor_type(cls, v: str) -> str:
        """Validate actor type is one of allowed values."""
        allowed = {"human", "system", "policy"}
        if v.lower() not in allowed:
            raise ValueError(f"actor_type must be one of: {', '.join(allowed)}")
        return v.lower()


class DecisionModifyIn(DecisionActionIn):
    modifications: dict[str, Any]


class DecisionRecommendationOut(BaseModel):
    summary: Optional[str] = None
    detailed_explanation: Optional[dict[str, Any]] = None
    model_used: Optional[str] = None
    prompt_version: Optional[str] = None
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)


class DecisionPolicySnapshotOut(BaseModel):
    policy_version: Optional[str] = None
    evaluated_rules: Optional[list[dict[str, Any]] | dict[str, Any]] = None
    result: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DecisionActionOut(BaseModel):
    id: UUID
    action_type: ActionType
    actor_type: ActorType
    actor_id: Optional[str] = None
    comment: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DecisionOut(BaseModel):
    id: UUID
    execution_id: UUID
    flow_id: str
    node_id: str
    status: DecisionStatus
    language: str
    risk_score: Optional[float] = None
    confidence_score: Optional[float] = None
    estimated_cost: Optional[float] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    recommendation: Optional[DecisionRecommendationOut] = None
    policy_snapshot: Optional[DecisionPolicySnapshotOut] = None
    actions: list[DecisionActionOut] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class DecisionListOut(BaseModel):
    items: list[DecisionOut]
    total: int
