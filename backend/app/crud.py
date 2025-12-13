from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


async def create_decision(session: AsyncSession, payload: schemas.DecisionCreate) -> models.Decision:
    # Idempotent on (execution_id, node_id)
    existing = await session.execute(
        select(models.Decision).where(
            models.Decision.execution_id == payload.execution_id,
            models.Decision.node_id == payload.node_id,
        )
    )
    decision = existing.scalar_one_or_none()
    if decision:
        return decision

    decision = models.Decision(
        execution_id=payload.execution_id,
        flow_id=payload.flow_id,
        node_id=payload.node_id,
        status="pending_human_review",
        language=payload.language,
        risk_score=payload.risk_score,
        confidence_score=payload.confidence_score,
        estimated_cost=payload.estimated_cost,
        expires_at=payload.expires_at,
    )
    session.add(decision)
    await session.flush()  # to get decision.id

    recommendation = models.DecisionRecommendation(
        decision_id=decision.id,
        summary=payload.recommendation.summary,
        detailed_explanation=payload.recommendation.detailed_explanation,
        model_used=payload.recommendation.model_used,
        prompt_version=payload.recommendation.prompt_version,
    )
    session.add(recommendation)

    if payload.policy_snapshot:
        snap = payload.policy_snapshot
        snapshot = models.DecisionPolicySnapshot(
            decision_id=decision.id,
            policy_version=snap.policy_version,
            evaluated_rules=snap.evaluated_rules,
            result=snap.result,
        )
        session.add(snapshot)

    await session.commit()
    await session.refresh(decision)
    return decision


async def list_decisions(
    session: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[models.Decision], int]:
    stmt = select(models.Decision)
    if status:
        stmt = stmt.where(models.Decision.status == status)
    stmt = stmt.order_by(models.Decision.created_at.desc())
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().unique().all(), total or 0


async def _add_action_and_update_status(
    session: AsyncSession,
    decision_id: UUID,
    status: str,
    action_type: str,
    action: schemas.DecisionActionIn,
    payload: Optional[dict] = None,
) -> models.Decision:
    result = await session.execute(select(models.Decision).where(models.Decision.id == decision_id))
    decision = result.scalar_one_or_none()
    if not decision:
        raise ValueError("Decision not found")

    decision.status = status
    action_row = models.DecisionAction(
        decision_id=decision.id,
        action_type=action_type,
        actor_type=action.actor_type,
        actor_id=action.actor_id,
        comment=action.comment,
        payload=payload,
    )
    session.add(action_row)
    await session.commit()
    await session.refresh(decision)
    return decision


async def approve_decision(session: AsyncSession, decision_id: UUID, action: schemas.DecisionActionIn):
    return await _add_action_and_update_status(session, decision_id, "approved", "approve", action)


async def reject_decision(session: AsyncSession, decision_id: UUID, action: schemas.DecisionActionIn):
    return await _add_action_and_update_status(session, decision_id, "rejected", "reject", action)


async def escalate_decision(session: AsyncSession, decision_id: UUID, action: schemas.DecisionActionIn):
    return await _add_action_and_update_status(session, decision_id, "escalated", "escalate", action)


async def modify_decision(session: AsyncSession, decision_id: UUID, payload: schemas.DecisionModifyIn):
    return await _add_action_and_update_status(
        session,
        decision_id,
        "modified",
        "modify",
        payload,
        payload=payload.modifications,
    )
