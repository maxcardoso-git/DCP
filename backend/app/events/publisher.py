"""
Event publisher abstraction with multiple backend support.
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

from .schemas import CloudEvent, create_cloud_event

logger = logging.getLogger("dcp.events")

# Global publisher instance
_publisher: Optional["EventPublisher"] = None


class EventPublisher(ABC):
    """Abstract base class for event publishers."""

    @abstractmethod
    async def publish(self, event: CloudEvent) -> None:
        """
        Publish a CloudEvent.

        Args:
            event: The CloudEvent to publish
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the publisher and release resources."""
        pass


class LogEventPublisher(EventPublisher):
    """
    Event publisher that logs events.

    Used as fallback when no other publisher is configured.
    """

    async def publish(self, event: CloudEvent) -> None:
        """Log the event."""
        logger.info(
            "EVENT %s: %s",
            event.type,
            json.dumps(event.to_json_dict(), default=str),
        )

    async def close(self) -> None:
        """No-op for log publisher."""
        pass


class RedisEventPublisher(EventPublisher):
    """
    Event publisher using Redis Pub/Sub.

    Publishes events to Redis channels based on event type.
    """

    def __init__(self, redis_url: str):
        """
        Initialize Redis publisher.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
        """
        self.redis_url = redis_url
        self._redis = None
        self._connected = False

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is established."""
        if self._connected and self._redis is not None:
            return

        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._connected = False
            raise

    async def publish(self, event: CloudEvent) -> None:
        """
        Publish event to Redis.

        Events are published to a channel named after the event type.
        """
        try:
            await self._ensure_connected()

            channel = event.type  # e.g., "dcp.decision.paused"
            message = json.dumps(event.to_json_dict(), default=str)

            await self._redis.publish(channel, message)
            logger.debug(f"Published event {event.id} to channel {channel}")

        except Exception as e:
            logger.error(f"Failed to publish event to Redis: {e}")
            # Fall back to logging
            logger.info(
                "EVENT (fallback) %s: %s",
                event.type,
                json.dumps(event.to_json_dict(), default=str),
            )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.close()
            self._connected = False
            logger.info("Redis connection closed")


class CompositeEventPublisher(EventPublisher):
    """
    Publisher that sends events to multiple backends.
    """

    def __init__(self, publishers: list[EventPublisher]):
        """
        Initialize with multiple publishers.

        Args:
            publishers: List of publishers to send events to
        """
        self.publishers = publishers

    async def publish(self, event: CloudEvent) -> None:
        """Publish to all configured publishers."""
        for publisher in self.publishers:
            try:
                await publisher.publish(event)
            except Exception as e:
                logger.error(f"Publisher {type(publisher).__name__} failed: {e}")

    async def close(self) -> None:
        """Close all publishers."""
        for publisher in self.publishers:
            try:
                await publisher.close()
            except Exception as e:
                logger.error(f"Error closing publisher {type(publisher).__name__}: {e}")


def get_publisher(redis_url: Optional[str] = None) -> EventPublisher:
    """
    Get or create the event publisher singleton.

    Args:
        redis_url: Optional Redis URL. If provided, enables Redis publishing.

    Returns:
        EventPublisher instance
    """
    global _publisher

    if _publisher is not None:
        return _publisher

    publishers = [LogEventPublisher()]  # Always log events

    if redis_url:
        try:
            redis_publisher = RedisEventPublisher(redis_url)
            publishers.append(redis_publisher)
            logger.info("Redis event publishing enabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis publisher: {e}")

    if len(publishers) == 1:
        _publisher = publishers[0]
    else:
        _publisher = CompositeEventPublisher(publishers)

    return _publisher


async def publish_event(
    event_type: str,
    payload: dict,
    subject: Optional[str] = None,
    traceparent: Optional[str] = None,
) -> None:
    """
    Convenience function to publish an event.

    Args:
        event_type: Event type (e.g., "dcp.decision.paused")
        payload: Event data payload
        subject: Optional subject identifier
        traceparent: Optional trace context
    """
    publisher = get_publisher()
    event = create_cloud_event(
        event_type=event_type,
        data=payload,
        subject=subject,
        traceparent=traceparent,
    )
    await publisher.publish(event)
