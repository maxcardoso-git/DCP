"""
TAH App Features Integration Module.

Provides endpoints for TAH (Tenant Access Hub) to discover
and manage application features for permission management.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .models import AppFeature
from .config import get_settings

logger = logging.getLogger("dcp.app_features")
settings = get_settings()

router = APIRouter(tags=["app-features"])

# App Configuration
APP_ID = "dcp"
APP_NAME = "Decision Control Plane"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Human-in-the-loop decision management system for AI orchestration"


# Pydantic Schemas
class AppFeatureIn(BaseModel):
    id: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    module: str = Field(..., max_length=100)
    path: Optional[str] = Field(None, max_length=255)
    icon: Optional[str] = Field(None, max_length=100)
    actions: list[str] = Field(default_factory=list)
    is_public: bool = False
    requires_org: bool = True
    metadata: Optional[dict[str, Any]] = None


class AppFeatureOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    module: str
    path: Optional[str]
    icon: Optional[str]
    actions: list[str]
    isPublic: bool
    requiresOrg: bool
    metadata: Optional[dict[str, Any]]

    class Config:
        from_attributes = True


class ModuleInfo(BaseModel):
    id: str
    name: str
    featureCount: int


class ManifestStats(BaseModel):
    totalFeatures: int
    totalModules: int
    publicFeatures: int


class AppManifest(BaseModel):
    appId: str
    appName: str
    version: str
    description: str
    modules: list[ModuleInfo]
    features: list[AppFeatureOut]
    stats: ManifestStats


# Default Features for DCP
DEFAULT_FEATURES = [
    {
        "id": "dcp.dashboard",
        "name": "Dashboard",
        "description": "Main dashboard with decision overview and metrics",
        "module": "core",
        "path": "/",
        "icon": "LayoutDashboard",
        "actions": ["read"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.decisions",
        "name": "Decisions",
        "description": "View and manage pending decisions",
        "module": "core",
        "path": "/decisions",
        "icon": "CheckCircle",
        "actions": ["read", "update"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.decisions.approve",
        "name": "Approve Decisions",
        "description": "Approve pending decisions",
        "module": "actions",
        "path": "/decisions/:id/approve",
        "icon": "Check",
        "actions": ["execute"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.decisions.reject",
        "name": "Reject Decisions",
        "description": "Reject pending decisions",
        "module": "actions",
        "path": "/decisions/:id/reject",
        "icon": "X",
        "actions": ["execute"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.decisions.escalate",
        "name": "Escalate Decisions",
        "description": "Escalate decisions to higher authority",
        "module": "actions",
        "path": "/decisions/:id/escalate",
        "icon": "ArrowUp",
        "actions": ["execute"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.decisions.modify",
        "name": "Modify Decisions",
        "description": "Modify decision parameters before approval",
        "module": "actions",
        "path": "/decisions/:id/modify",
        "icon": "Edit",
        "actions": ["execute"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.policy",
        "name": "Policy Management",
        "description": "Configure and manage decision policies",
        "module": "admin",
        "path": "/policy",
        "icon": "Shield",
        "actions": ["read", "create", "update", "delete"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.policy.evaluate",
        "name": "Policy Evaluation",
        "description": "Test policy evaluation without persisting",
        "module": "admin",
        "path": "/policy/evaluate",
        "icon": "PlayCircle",
        "actions": ["execute"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.api.gates",
        "name": "Decision Gates API",
        "description": "Create decision gates via API",
        "module": "api",
        "path": "/api/v2/dcp/decision-gates",
        "icon": "Zap",
        "actions": ["create"],
        "is_public": "false",
        "requires_org": "true",
    },
    {
        "id": "dcp.metrics",
        "name": "Metrics",
        "description": "View application metrics and health",
        "module": "observability",
        "path": "/metrics",
        "icon": "BarChart",
        "actions": ["read"],
        "is_public": "true",
        "requires_org": "false",
    },
    {
        "id": "dcp.health",
        "name": "Health Check",
        "description": "Application health endpoints",
        "module": "observability",
        "path": "/healthz",
        "icon": "Heart",
        "actions": ["read"],
        "is_public": "true",
        "requires_org": "false",
    },
]


def feature_to_out(feature: AppFeature) -> AppFeatureOut:
    """Convert AppFeature model to output schema."""
    return AppFeatureOut(
        id=feature.id,
        name=feature.name,
        description=feature.description,
        module=feature.module,
        path=feature.path,
        icon=feature.icon,
        actions=feature.actions or [],
        isPublic=feature.is_public == "true",
        requiresOrg=feature.requires_org == "true",
        metadata=feature.extra_data,
    )


@router.get("/manifest", response_model=AppManifest)
async def get_manifest(session: AsyncSession = Depends(get_session)):
    """
    Get the complete application manifest with all features.
    This endpoint is PUBLIC and used by TAH to discover app features.
    """
    result = await session.execute(select(AppFeature))
    features = result.scalars().all()

    # If no features, seed with defaults
    if not features:
        await seed_features_internal(session)
        result = await session.execute(select(AppFeature))
        features = result.scalars().all()

    feature_outs = [feature_to_out(f) for f in features]

    # Group by module
    modules_dict: dict[str, int] = {}
    public_count = 0
    for f in feature_outs:
        modules_dict[f.module] = modules_dict.get(f.module, 0) + 1
        if f.isPublic:
            public_count += 1

    modules = [
        ModuleInfo(id=m, name=m.title(), featureCount=c)
        for m, c in modules_dict.items()
    ]

    return AppManifest(
        appId=APP_ID,
        appName=APP_NAME,
        version=APP_VERSION,
        description=APP_DESCRIPTION,
        modules=modules,
        features=feature_outs,
        stats=ManifestStats(
            totalFeatures=len(feature_outs),
            totalModules=len(modules),
            publicFeatures=public_count,
        ),
    )


@router.get("/", response_model=list[AppFeatureOut])
async def list_features(session: AsyncSession = Depends(get_session)):
    """List all app features."""
    result = await session.execute(select(AppFeature))
    features = result.scalars().all()
    return [feature_to_out(f) for f in features]


@router.get("/{feature_id}", response_model=AppFeatureOut)
async def get_feature(feature_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific feature by ID."""
    result = await session.execute(select(AppFeature).where(AppFeature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")
    return feature_to_out(feature)


@router.post("/", response_model=AppFeatureOut, status_code=201)
async def create_feature(
    payload: AppFeatureIn,
    session: AsyncSession = Depends(get_session),
):
    """Create a new app feature."""
    # Check if exists
    existing = await session.execute(select(AppFeature).where(AppFeature.id == payload.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Feature already exists")

    feature = AppFeature(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        module=payload.module,
        path=payload.path,
        icon=payload.icon,
        actions=payload.actions,
        is_public="true" if payload.is_public else "false",
        requires_org="true" if payload.requires_org else "false",
        extra_data=payload.metadata,
    )
    session.add(feature)
    await session.commit()
    await session.refresh(feature)
    logger.info(f"Created app feature: {feature.id}")
    return feature_to_out(feature)


@router.put("/{feature_id}", response_model=AppFeatureOut)
async def update_feature(
    feature_id: str,
    payload: AppFeatureIn,
    session: AsyncSession = Depends(get_session),
):
    """Update an existing app feature."""
    result = await session.execute(select(AppFeature).where(AppFeature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    feature.name = payload.name
    feature.description = payload.description
    feature.module = payload.module
    feature.path = payload.path
    feature.icon = payload.icon
    feature.actions = payload.actions
    feature.is_public = "true" if payload.is_public else "false"
    feature.requires_org = "true" if payload.requires_org else "false"
    feature.extra_data = payload.metadata
    feature.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(feature)
    logger.info(f"Updated app feature: {feature.id}")
    return feature_to_out(feature)


@router.delete("/{feature_id}", status_code=204)
async def delete_feature(feature_id: str, session: AsyncSession = Depends(get_session)):
    """Delete an app feature."""
    result = await session.execute(select(AppFeature).where(AppFeature.id == feature_id))
    feature = result.scalar_one_or_none()
    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    await session.delete(feature)
    await session.commit()
    logger.info(f"Deleted app feature: {feature_id}")


async def seed_features_internal(session: AsyncSession):
    """Internal function to seed default features."""
    for feat_data in DEFAULT_FEATURES:
        existing = await session.execute(
            select(AppFeature).where(AppFeature.id == feat_data["id"])
        )
        if not existing.scalar_one_or_none():
            feature = AppFeature(**feat_data)
            session.add(feature)

    await session.commit()
    logger.info(f"Seeded {len(DEFAULT_FEATURES)} default features")


@router.post("/seed", status_code=201)
async def seed_features(session: AsyncSession = Depends(get_session)):
    """Seed default features for the application."""
    await seed_features_internal(session)
    return {"message": f"Seeded {len(DEFAULT_FEATURES)} features", "features": len(DEFAULT_FEATURES)}


@router.delete("/", status_code=204)
async def clear_features(session: AsyncSession = Depends(get_session)):
    """Clear all features (admin only - use with caution)."""
    await session.execute(delete(AppFeature))
    await session.commit()
    logger.warning("Cleared all app features")
