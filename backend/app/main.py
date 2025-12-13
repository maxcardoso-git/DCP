import asyncio
import logging
from fastapi import Depends, FastAPI, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .policy import evaluate_policy
from .events import publish_event
from .config import get_settings
from .database import Base, engine, get_session

settings = get_settings()
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Decision Control Plane API", version="2.0.0", openapi_url=f"{settings.api_prefix}/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("startup")
async def on_startup():
    await init_models()


@app.get("/healthz")
async def health():
    return {"status": "ok"}


def auth_guard(authorization: str | None = Header(default=None)):
    if settings.bearer_token:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ", 1)[1]
        if token != settings.bearer_token:
            raise HTTPException(status_code=403, detail="Forbidden")
    return True


@app.post(f"{settings.api_prefix}/decision-gates", response_model=schemas.DecisionOut, status_code=201)
async def create_decision_gate(
    payload: schemas.DecisionCreate,
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(auth_guard),
):
    try:
        # If client did not send a policy snapshot, apply a simple heuristic and persist it
        if payload.policy_snapshot is None:
            result = evaluate_policy(
                payload.risk_score, payload.confidence_score, payload.estimated_cost, payload.compliance_flags
            )
            payload.policy_snapshot = schemas.DecisionPolicySnapshotIn(
                policy_version="heuristic-v1", evaluated_rules=[result], result=result["result"]
            )
        decision = await crud.create_decision(session, payload)
        await publish_event(
            "dcp.decision.paused",
            {
                "decision_id": str(decision.id),
                "execution_id": str(decision.execution_id),
                "flow_id": decision.flow_id,
                "node_id": decision.node_id,
                "status": decision.status,
                "language": decision.language,
            },
        )
        return decision
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/decisions", response_model=schemas.DecisionListOut)
async def list_decisions(
    status: str | None = Query(default=None, description="Filter by status, defaults to pending_human_review"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: bool = Depends(auth_guard),
):
    items, total = await crud.list_decisions(session, status=status or "pending_human_review", limit=limit, offset=offset)
    return {"items": items, "total": total}


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/approve", response_model=schemas.DecisionOut)
async def approve_decision(
    decision_id: str, payload: schemas.DecisionActionIn, session: AsyncSession = Depends(get_session), _: bool = Depends(auth_guard)
):
    try:
        decision = await crud.approve_decision(session, decision_id, payload)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "approve"})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/reject", response_model=schemas.DecisionOut)
async def reject_decision(
    decision_id: str, payload: schemas.DecisionActionIn, session: AsyncSession = Depends(get_session), _: bool = Depends(auth_guard)
):
    try:
        decision = await crud.reject_decision(session, decision_id, payload)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "reject"})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/escalate", response_model=schemas.DecisionOut)
async def escalate_decision(
    decision_id: str, payload: schemas.DecisionActionIn, session: AsyncSession = Depends(get_session), _: bool = Depends(auth_guard)
):
    try:
        decision = await crud.escalate_decision(session, decision_id, payload)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "escalate"})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/modify", response_model=schemas.DecisionOut)
async def modify_decision(
    decision_id: str, payload: schemas.DecisionModifyIn, session: AsyncSession = Depends(get_session), _: bool = Depends(auth_guard)
):
    try:
        decision = await crud.modify_decision(session, decision_id, payload)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "modify"})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/policy/evaluate")
async def policy_evaluate(payload: schemas.DecisionCreate, _: bool = Depends(auth_guard)):
    result = evaluate_policy(
        payload.risk_score, payload.confidence_score, payload.estimated_cost, payload.compliance_flags
    )
    return {"result": result["result"], "reason": result["reason"]}
