import json
import logging

logger = logging.getLogger("dcp.events")


async def publish_event(event_type: str, payload: dict):
    """
    Stub event publisher: log the event type and payload.
    Replace with real bus/webhook integration.
    """
    logger.info("EVENT %s: %s", event_type, json.dumps(payload))
