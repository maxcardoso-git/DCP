"""
Event schemas following CloudEvents 1.0 specification.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class CloudEvent(BaseModel):
    """
    CloudEvents 1.0 compliant event envelope.

    See: https://cloudevents.io/
    """

    # Required attributes
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    source: str = "dcp"
    specversion: str = "1.0"

    # Optional attributes
    time: datetime = Field(default_factory=datetime.utcnow)
    datacontenttype: str = "application/json"
    subject: Optional[str] = None
    traceparent: Optional[str] = None

    # Event data
    data: dict[str, Any] = Field(default_factory=dict)

    # DCP-specific metadata
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z",
        }

    def to_json_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "specversion": self.specversion,
            "time": self.time.isoformat() + "Z",
            "datacontenttype": self.datacontenttype,
            "subject": self.subject,
            "traceparent": self.traceparent,
            "data": self.data,
        }


def create_cloud_event(
    event_type: str,
    data: dict[str, Any],
    source: str = "dcp",
    subject: Optional[str] = None,
    traceparent: Optional[str] = None,
) -> CloudEvent:
    """
    Create a CloudEvent with the given parameters.

    Args:
        event_type: Event type (e.g., "dcp.decision.paused")
        data: Event payload data
        source: Event source identifier
        subject: Optional subject (e.g., decision_id)
        traceparent: Optional trace context for distributed tracing

    Returns:
        CloudEvent instance
    """
    return CloudEvent(
        type=event_type,
        source=source,
        subject=subject,
        traceparent=traceparent,
        data=data,
    )


# Event type constants
class EventTypes:
    """DCP event type constants."""

    DECISION_PAUSED = "dcp.decision.paused"
    DECISION_ACTIONED = "dcp.decision.actioned"
    DECISION_EXPIRED = "dcp.decision.expired"
    DECISION_RESUMED = "dcp.decision.resumed"
