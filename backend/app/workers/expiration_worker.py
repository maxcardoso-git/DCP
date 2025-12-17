"""
Worker for processing expired decisions.

Runs periodically to:
1. Find decisions that have exceeded their expires_at time
2. Update their status to 'expired'
3. Publish expiration events
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import Decision
from ..events.publisher import publish_event, get_publisher
from ..events.schemas import EventTypes

logger = logging.getLogger("dcp.worker.expiration")


class ExpirationWorker:
    """
    Background worker that processes expired decisions.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        interval_seconds: int = 60,
        redis_url: Optional[str] = None,
    ):
        """
        Initialize the expiration worker.

        Args:
            session_factory: Async session factory for database access
            interval_seconds: How often to check for expired decisions
            redis_url: Redis URL for event publishing
        """
        self.session_factory = session_factory
        self.interval = interval_seconds
        self.redis_url = redis_url
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the worker loop."""
        if self._running:
            logger.warning("Worker already running")
            return

        self._running = True
        logger.info(f"Starting expiration worker with interval {self.interval}s")

        # Initialize event publisher
        get_publisher(self.redis_url)

        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the worker loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Expiration worker stopped")

    async def _run_loop(self) -> None:
        """Main worker loop."""
        while self._running:
            try:
                expired_count = await self.process_expired_decisions()
                if expired_count > 0:
                    logger.info(f"Processed {expired_count} expired decisions")
            except Exception as e:
                logger.error(f"Error processing expired decisions: {e}")

            await asyncio.sleep(self.interval)

    async def process_expired_decisions(self) -> int:
        """
        Find and process all expired decisions.

        Returns:
            Number of decisions processed
        """
        async with self.session_factory() as session:
            # Find expired decisions that are still pending
            now = datetime.utcnow()
            stmt = (
                select(Decision)
                .where(Decision.status == "pending_human_review")
                .where(Decision.expires_at.isnot(None))
                .where(Decision.expires_at < now)
                .with_for_update(skip_locked=True)  # Avoid race conditions with other workers
            )

            result = await session.execute(stmt)
            expired_decisions = result.scalars().all()

            if not expired_decisions:
                return 0

            # Process each expired decision
            for decision in expired_decisions:
                await self._expire_decision(session, decision)

            await session.commit()
            return len(expired_decisions)

    async def _expire_decision(self, session: AsyncSession, decision: Decision) -> None:
        """
        Mark a single decision as expired and publish event.

        Args:
            session: Database session
            decision: Decision to expire
        """
        # Update status
        decision.status = "expired"

        # Publish expiration event
        await publish_event(
            EventTypes.DECISION_EXPIRED,
            {
                "decision_id": str(decision.id),
                "execution_id": str(decision.execution_id),
                "flow_id": decision.flow_id,
                "node_id": decision.node_id,
                "status": "expired",
                "expires_at": decision.expires_at.isoformat() if decision.expires_at else None,
                "expired_at": datetime.utcnow().isoformat(),
            },
            subject=str(decision.id),
        )

        logger.debug(f"Decision {decision.id} marked as expired")


async def run_expiration_worker(
    session_factory: async_sessionmaker[AsyncSession],
    interval_seconds: int = 60,
    redis_url: Optional[str] = None,
) -> None:
    """
    Run the expiration worker until interrupted.

    Args:
        session_factory: Async session factory
        interval_seconds: Check interval
        redis_url: Redis URL for events
    """
    worker = ExpirationWorker(
        session_factory=session_factory,
        interval_seconds=interval_seconds,
        redis_url=redis_url,
    )

    await worker.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(3600)  # Sleep for an hour, loop handles actual work
    except asyncio.CancelledError:
        await worker.stop()
