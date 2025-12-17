"""
Worker entry point for running background tasks.

Usage:
    python -m app.worker
"""
import asyncio
import logging
import signal
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from .config import get_settings
from .database import Base
from .workers.expiration_worker import ExpirationWorker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("dcp.worker")


async def main():
    """Main worker entry point."""
    settings = get_settings()

    # Set log level from settings
    logging.getLogger().setLevel(settings.log_level)

    logger.info("Starting DCP Worker")
    logger.info(f"Database: {settings.database_url.split('@')[-1]}")  # Hide credentials
    logger.info(f"Redis: {settings.redis_url or 'disabled'}")
    logger.info(f"Interval: {settings.worker_interval}s")

    # Create database engine and session factory
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create and start worker
    worker = ExpirationWorker(
        session_factory=session_factory,
        interval_seconds=settings.worker_interval,
        redis_url=settings.redis_url,
    )

    # Handle shutdown signals
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Start worker
    await worker.start()

    try:
        # Wait for shutdown signal
        await shutdown_event.wait()
    finally:
        # Cleanup
        logger.info("Shutting down worker...")
        await worker.stop()
        await engine.dispose()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
        sys.exit(0)
