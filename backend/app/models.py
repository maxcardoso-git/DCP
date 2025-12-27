import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship

from .database import Base


DecisionStatusEnum = Enum(
    "created",
    "pending_human_review",
    "approved",
    "rejected",
    "modified",
    "escalated",
    "expired",
    "executed",
    name="decision_status",
)

ActionTypeEnum = Enum("approve", "reject", "modify", "escalate", name="decision_action_type")

ActorTypeEnum = Enum("human", "system", "policy", name="decision_actor_type")


class Decision(Base):
    __tablename__ = "decision"
    __table_args__ = (
        UniqueConstraint("execution_id", "node_id", name="uq_decision_execution_node"),
        Index("idx_decision_org", "org_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(String(100), nullable=False, default="default")  # TAH org_id - NO FK
    execution_id = Column(UUID(as_uuid=True), nullable=False)
    flow_id = Column(String, nullable=False)
    node_id = Column(String, nullable=False)
    status = Column(DecisionStatusEnum, nullable=False, default="pending_human_review")
    language = Column(String, nullable=False, default="en")
    risk_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    estimated_cost = Column(Numeric(12, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    recommendation = relationship(
        "DecisionRecommendation",
        back_populates="decision",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    actions = relationship(
        "DecisionAction",
        back_populates="decision",
        cascade="all, delete-orphan",
        order_by="DecisionAction.created_at",
        lazy="selectin",
    )
    policy_snapshot = relationship(
        "DecisionPolicySnapshot",
        back_populates="decision",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DecisionRecommendation(Base):
    __tablename__ = "decision_recommendation"

    decision_id = Column(UUID(as_uuid=True), ForeignKey("decision.id", ondelete="CASCADE"), primary_key=True)
    summary = Column(String, nullable=True)
    detailed_explanation = Column(JSON, nullable=True)
    model_used = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)

    decision = relationship("Decision", back_populates="recommendation")


class DecisionAction(Base):
    __tablename__ = "decision_action"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision_id = Column(UUID(as_uuid=True), ForeignKey("decision.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(ActionTypeEnum, nullable=False)
    actor_type = Column(ActorTypeEnum, nullable=False, default="human")
    actor_id = Column(String, nullable=True)
    comment = Column(String, nullable=True)
    payload = Column(JSON, nullable=True)  # optional structured modifications/override context
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    decision = relationship("Decision", back_populates="actions")


class DecisionPolicySnapshot(Base):
    __tablename__ = "decision_policy_snapshot"

    decision_id = Column(UUID(as_uuid=True), ForeignKey("decision.id", ondelete="CASCADE"), primary_key=True)
    policy_version = Column(String, nullable=True)
    evaluated_rules = Column(JSON, nullable=True)
    result = Column(String, nullable=True)

    decision = relationship("Decision", back_populates="policy_snapshot")


class AppFeature(Base):
    """TAH App Features for permission management."""
    __tablename__ = "app_feature"

    id = Column(String(100), primary_key=True)  # format: appId.featureName
    name = Column(String(255), nullable=False)
    description = Column(String, nullable=True)
    module = Column(String(100), nullable=False)
    path = Column(String(255), nullable=True)
    icon = Column(String(100), nullable=True)
    actions = Column(JSON, default=list)  # ["read", "create", "update", "delete", "execute"]
    is_public = Column(String(10), default="false")  # stored as string for compatibility
    requires_org = Column(String(10), default="true")
    extra_data = Column(JSON, nullable=True)  # renamed from metadata (reserved by SQLAlchemy)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class User(Base):
    """TAH User - JIT provisioned from TAH tokens."""
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tah_user_id", "org_id", name="uq_user_tah_org"),
        Index("idx_users_tah_user_id", "tah_user_id"),
        Index("idx_users_org_id", "org_id"),
        Index("idx_users_email", "email"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tah_user_id = Column(UUID(as_uuid=True), nullable=False)  # 'sub' from JWT
    org_id = Column(String(100), nullable=False)  # From JWT - NO FK
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """User session for TAH authenticated users."""
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_token", "token_hash"),
        Index("idx_sessions_org", "org_id"),
        Index("idx_sessions_expires", "expires_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    org_id = Column(String(100), nullable=False)  # From JWT - NO FK
    token_hash = Column(String(255), nullable=False)
    tah_token_exp = Column(DateTime(timezone=True), nullable=True)
    tah_permissions = Column(JSON, default=list)
    tah_roles = Column(JSON, default=list)
    tenant_id = Column(String(100), nullable=True)  # TAH tenant_id for API calls
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")
