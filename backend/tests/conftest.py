"""
Global pytest fixtures for DCP backend tests.
"""
import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.config import get_settings, Settings


# Test database URL (SQLite in-memory for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def async_engine():
    """Create async engine for tests using SQLite in-memory."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    async_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_settings() -> Settings:
    """Test settings with bearer token enabled."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        bearer_token="test-token-12345",
        allowed_origins=["*"],
    )


@pytest.fixture
def auth_headers() -> dict:
    """Headers with valid bearer token for authenticated requests."""
    return {"Authorization": "Bearer test-token-12345"}


@pytest.fixture
def invalid_auth_headers() -> dict:
    """Headers with invalid bearer token."""
    return {"Authorization": "Bearer invalid-token"}


@pytest.fixture
async def client(async_engine, test_settings) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    async_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_session():
        async with async_session_factory() as session:
            yield session

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = override_get_settings

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def client_no_auth(async_engine) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client without auth requirement."""
    async_session_factory = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_session():
        async with async_session_factory() as session:
            yield session

    def override_get_settings():
        return Settings(
            database_url=TEST_DATABASE_URL,
            bearer_token=None,  # No auth required
            allowed_origins=["*"],
        )

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings] = override_get_settings

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# Factory helpers for creating test data
class DecisionFactory:
    """Factory for creating decision test data."""

    @staticmethod
    def create_payload(
        execution_id: str | None = None,
        flow_id: str = "test-flow",
        node_id: str = "test-node",
        language: str = "en",
        risk_score: float | None = 0.5,
        confidence_score: float | None = 0.7,
        estimated_cost: float | None = 100.0,
        compliance_flags: list[str] | None = None,
    ) -> dict:
        """Create a decision gate payload for API testing."""
        return {
            "execution_id": execution_id or str(uuid4()),
            "flow_id": flow_id,
            "node_id": node_id,
            "language": language,
            "risk_score": risk_score,
            "confidence_score": confidence_score,
            "estimated_cost": estimated_cost,
            "compliance_flags": compliance_flags,
            "recommendation": {
                "summary": "Test recommendation",
                "detailed_explanation": {"reason": "Test reason"},
                "model_used": "test-model",
                "prompt_version": "v1",
            },
            "policy_snapshot": {
                "policy_version": "v2.0.0",
                "evaluated_rules": [{"id": "test-rule", "outcome": "require_human"}],
                "result": "require_human",
            },
        }


@pytest.fixture
def decision_factory() -> DecisionFactory:
    """Provide decision factory for tests."""
    return DecisionFactory()
