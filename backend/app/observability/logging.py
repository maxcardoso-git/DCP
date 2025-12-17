"""
Structured logging configuration for DCP.

Provides JSON-formatted logs for better observability and log aggregation.
"""
import logging
import sys
from typing import Optional

from pythonjsonlogger import jsonlogger


class DCPJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for DCP logs.

    Adds standard fields and renames some for consistency.
    """

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = log_record.pop("asctime", None)
        log_record["level"] = log_record.pop("levelname", record.levelname)
        log_record["logger"] = record.name
        log_record["service"] = "dcp"

        # Add trace context if available
        if hasattr(record, "trace_id"):
            log_record["trace_id"] = record.trace_id
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        # Add extra fields
        if hasattr(record, "decision_id"):
            log_record["decision_id"] = record.decision_id
        if hasattr(record, "flow_id"):
            log_record["flow_id"] = record.flow_id
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (True) or plain text (False)
        log_file: Optional log file path
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    if json_format:
        formatter = DCPJsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name (typically module name)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding extra fields to log records.

    Usage:
        with LogContext(decision_id="123", flow_id="flow-1"):
            logger.info("Processing decision")
    """

    def __init__(self, **kwargs):
        self.extra = kwargs
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()

        extra = self.extra

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in extra.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)
        return False
