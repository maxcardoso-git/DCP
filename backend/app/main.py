import asyncio
import logging
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Query, Header, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .policy import evaluate_policy
from .events import publish_event
from .config import get_settings
from .database import Base, engine, get_session
from .app_features import router as app_features_router
from .auth import (
    router as auth_router,
    get_current_session,
    get_optional_session,
    get_optional_auth_user,
    get_org_id,
    has_permission,
    current_org_id,
    TAHUserInfo,
)
from .models import UserSession
from .observability.logging import setup_logging
from .observability.metrics import (
    get_metrics,
    get_metrics_content_type,
    record_decision_created,
    record_decision_action,
)
from .observability.middleware import RequestTracingMiddleware, MetricsMiddleware

settings = get_settings()

# Setup structured logging
setup_logging(level=settings.log_level, json_format=settings.environment != "development")

logger = logging.getLogger("dcp.api")

app = FastAPI(
    title="Decision Control Plane API",
    version="2.0.0",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# Add middlewares (order matters - first added is outermost)
app.add_middleware(MetricsMiddleware)
app.add_middleware(RequestTracingMiddleware)

# CORS: When allow_credentials=True, cannot use "*" for origins
# Build explicit origins list from frontend_url and allowed_origins
cors_origins = []
if settings.frontend_url:
    cors_origins.append(settings.frontend_url)
for origin in settings.allowed_origins:
    origin = origin.strip()
    if origin and origin != "*":
        cors_origins.append(origin)

# In development without explicit origins, allow the common local URLs
if not cors_origins or (len(cors_origins) == 0):
    cors_origins = [
        "http://localhost:8100",
        "http://localhost:4173",
        "http://127.0.0.1:8100",
        "http://127.0.0.1:4173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
    logger.info("DCP API started", extra={"version": "2.0.0", "environment": settings.environment})


# Mount TAH routers
app.include_router(auth_router)  # /auth/tah-callback, /auth/session, etc.
app.include_router(app_features_router, prefix="/api/v1/app-features")


@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/readyz")
async def readiness(session: AsyncSession = Depends(get_session)):
    """Readiness check - verifies database connectivity."""
    try:
        await session.execute("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Database not ready")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type(),
    )


async def auth_guard(
    user: Optional[TAHUserInfo] = Depends(get_optional_auth_user),
    authorization: str | None = Header(default=None),
) -> Optional[TAHUserInfo]:
    """
    Hybrid auth guard supporting:
    - TAH JWT token via Authorization header (OrchestratorAI-style)
    - TAH session authentication (cookie-based, legacy)
    - Legacy static bearer token authentication

    Returns TAHUserInfo if authenticated.
    """
    # 1. Check TAH auth (Bearer JWT or session cookie) - handled by get_optional_auth_user
    if user:
        return user

    # 2. Fall back to legacy static bearer token
    if settings.bearer_token:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Unauthorized")
        token = authorization.split(" ", 1)[1]
        if token != settings.bearer_token:
            raise HTTPException(status_code=403, detail="Forbidden")
        # Set default org for bearer token auth
        current_org_id.set("default")
        return None

    # 3. If no auth method configured, allow public access (dev mode)
    if not settings.tah_enabled and not settings.bearer_token:
        current_org_id.set("default")
        return None

    raise HTTPException(status_code=401, detail="Unauthorized")


@app.post(f"{settings.api_prefix}/decision-gates", response_model=schemas.DecisionOut, status_code=201)
async def create_decision_gate(
    payload: schemas.DecisionCreate,
    session: AsyncSession = Depends(get_session),
    _: Optional[TAHUserInfo] = Depends(auth_guard),
):
    try:
        # Get org_id from context (set by auth_guard)
        org_id = current_org_id.get() or "default"

        # If client did not send a policy snapshot, apply a simple heuristic and persist it
        if payload.policy_snapshot is None:
            result = evaluate_policy(
                payload.risk_score, payload.confidence_score, payload.estimated_cost, payload.compliance_flags
            )
            payload.policy_snapshot = schemas.DecisionPolicySnapshotIn(
                policy_version="heuristic-v1", evaluated_rules=[{"id": "heuristic", **result}], result=result["result"]
            )

        decision = await crud.create_decision(session, payload, org_id=org_id)

        # Record metrics
        record_decision_created(
            flow_id=decision.flow_id,
            policy_result=payload.policy_snapshot.result or "unknown",
        )

        await publish_event(
            "dcp.decision.paused",
            {
                "decision_id": str(decision.id),
                "execution_id": str(decision.execution_id),
                "flow_id": decision.flow_id,
                "node_id": decision.node_id,
                "status": decision.status,
                "language": decision.language,
                "org_id": org_id,
            },
        )
        return decision
    except Exception as exc:
        logger.error(f"Error creating decision gate: {exc}")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/decisions", response_model=schemas.DecisionListOut)
async def list_decisions(
    status: str | None = Query(default=None, description="Filter by status, defaults to pending_human_review"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    _: Optional[TAHUserInfo] = Depends(auth_guard),
):
    org_id = current_org_id.get() or "default"
    items, total = await crud.list_decisions(
        session, org_id=org_id, status=status or "pending_human_review", limit=limit, offset=offset
    )
    return {"items": items, "total": total}


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/approve", response_model=schemas.DecisionOut)
async def approve_decision(
    decision_id: str,
    payload: schemas.DecisionActionIn,
    session: AsyncSession = Depends(get_session),
    _: Optional[TAHUserInfo] = Depends(auth_guard),
):
    try:
        org_id = current_org_id.get() or "default"
        decision = await crud.approve_decision(session, decision_id, payload, org_id=org_id)
        record_decision_action(action_type="approve", actor_type=payload.actor_type)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "approve", "org_id": org_id})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/reject", response_model=schemas.DecisionOut)
async def reject_decision(
    decision_id: str,
    payload: schemas.DecisionActionIn,
    session: AsyncSession = Depends(get_session),
    _: Optional[TAHUserInfo] = Depends(auth_guard),
):
    try:
        org_id = current_org_id.get() or "default"
        decision = await crud.reject_decision(session, decision_id, payload, org_id=org_id)
        record_decision_action(action_type="reject", actor_type=payload.actor_type)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "reject", "org_id": org_id})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/escalate", response_model=schemas.DecisionOut)
async def escalate_decision(
    decision_id: str,
    payload: schemas.DecisionActionIn,
    session: AsyncSession = Depends(get_session),
    _: Optional[TAHUserInfo] = Depends(auth_guard),
):
    try:
        org_id = current_org_id.get() or "default"
        decision = await crud.escalate_decision(session, decision_id, payload, org_id=org_id)
        record_decision_action(action_type="escalate", actor_type=payload.actor_type)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "escalate", "org_id": org_id})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/modify", response_model=schemas.DecisionOut)
async def modify_decision(
    decision_id: str,
    payload: schemas.DecisionModifyIn,
    session: AsyncSession = Depends(get_session),
    _: Optional[TAHUserInfo] = Depends(auth_guard),
):
    try:
        org_id = current_org_id.get() or "default"
        decision = await crud.modify_decision(session, decision_id, payload, org_id=org_id)
        record_decision_action(action_type="modify", actor_type=payload.actor_type)
        await publish_event("dcp.decision.actioned", {"decision_id": str(decision.id), "action": "modify", "org_id": org_id})
        return decision
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/policy/evaluate")
async def policy_evaluate(
    payload: schemas.DecisionCreate,
    _: Optional[TAHUserInfo] = Depends(auth_guard),
):
    result = evaluate_policy(
        payload.risk_score, payload.confidence_score, payload.estimated_cost, payload.compliance_flags
    )
    return {"result": result["result"], "reason": result["reason"]}
