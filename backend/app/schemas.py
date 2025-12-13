from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


DecisionStatus = str
ActionType = str
ActorType = str


class DecisionRecommendationIn(BaseModel):
    summary: Optional[str] = None
    detailed_explanation: Optional[dict[str, Any]] = None
    model_used: Optional[str] = None
    prompt_version: Optional[str] = None


class DecisionPolicySnapshotIn(BaseModel):
    policy_version: Optional[str] = None
    evaluated_rules: Optional[dict[str, Any]] = None
    result: Optional[str] = None


class DecisionCreate(BaseModel):
    execution_id: UUID
    flow_id: str
    node_id: str
    language: str = "en"
    risk_score: Optional[float] = None
    confidence_score: Optional[float] = None
    estimated_cost: Optional[float] = None
    impact_level: Optional[str] = None
    compliance_flags: Optional[list[str]] = None
    recommendation: DecisionRecommendationIn
    policy_snapshot: Optional[DecisionPolicySnapshotIn] = None
    expires_at: Optional[datetime] = None


class DecisionActionIn(BaseModel):
    actor_id: Optional[str] = None
    actor_type: ActorType = "human"
    comment: Optional[str] = None
    language: Optional[str] = None


class DecisionModifyIn(DecisionActionIn):
    modifications: dict[str, Any]


class DecisionRecommendationOut(BaseModel):
    summary: Optional[str] = None
    detailed_explanation: Optional[dict[str, Any]] = None
    model_used: Optional[str] = None
    prompt_version: Optional[str] = None

    class Config:
        from_attributes = True


class DecisionPolicySnapshotOut(BaseModel):
    policy_version: Optional[str] = None
    evaluated_rules: Optional[dict[str, Any]] = None
    result: Optional[str] = None

    class Config:
        from_attributes = True


class DecisionActionOut(BaseModel):
    id: UUID
    action_type: ActionType
    actor_type: ActorType
    actor_id: Optional[str] = None
    comment: Optional[str] = None
    payload: Optional[dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class DecisionListOut(BaseModel):
    items: list[DecisionOut]
