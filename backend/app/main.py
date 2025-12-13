import asyncio
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, models, schemas
from .config import get_settings
from .database import Base, engine, get_session

settings = get_settings()

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


@app.post(f"{settings.api_prefix}/decision-gates", response_model=schemas.DecisionOut, status_code=201)
async def create_decision_gate(payload: schemas.DecisionCreate, session: AsyncSession = Depends(get_session)):
    try:
        decision = await crud.create_decision(session, payload)
        return decision
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/decisions", response_model=schemas.DecisionListOut)
async def list_decisions(
    status: str | None = Query(default=None, description="Filter by status, defaults to pending_human_review"),
    session: AsyncSession = Depends(get_session),
):
    decisions = await crud.list_decisions(session, status=status or "pending_human_review")
    return {"items": decisions}


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/approve", response_model=schemas.DecisionOut)
async def approve_decision(decision_id: str, payload: schemas.DecisionActionIn, session: AsyncSession = Depends(get_session)):
    try:
        return await crud.approve_decision(session, decision_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/reject", response_model=schemas.DecisionOut)
async def reject_decision(decision_id: str, payload: schemas.DecisionActionIn, session: AsyncSession = Depends(get_session)):
    try:
        return await crud.reject_decision(session, decision_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/escalate", response_model=schemas.DecisionOut)
async def escalate_decision(decision_id: str, payload: schemas.DecisionActionIn, session: AsyncSession = Depends(get_session)):
    try:
        return await crud.escalate_decision(session, decision_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")


@app.post(f"{settings.api_prefix}/decisions/{{decision_id}}/modify", response_model=schemas.DecisionOut)
async def modify_decision(decision_id: str, payload: schemas.DecisionModifyIn, session: AsyncSession = Depends(get_session)):
    try:
        return await crud.modify_decision(session, decision_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Decision not found")
