"""structlog JSON logging with PII scrubbing processor (Step 5.6, plan §8.1)."""

import logging
import re
from collections.abc import MutableMapping
from typing import Any

import structlog

EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_REGEX = re.compile(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}")
SENSITIVE_KEYS = {
    "api_key",
    "gemini_api_key",
    "secret",
    "password",
    "token",
    "access_token",
    "authorization",
}


def scrub_pii(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Structlog processor scrubbing emails, phone numbers, and secrets from log events."""

    def _scrub_value(val: Any) -> Any:
        if isinstance(val, str):
            val = EMAIL_REGEX.sub("[EMAIL REDACTED]", val)
            val = PHONE_REGEX.sub("[PHONE REDACTED]", val)
            return val
        if isinstance(val, dict):
            return {
                k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else _scrub_value(v))
                for k, v in val.items()
            }
        if isinstance(val, list):
            return [_scrub_value(item) for item in val]
        return val

    for key, val in list(event_dict.items()):
        if key.lower() in SENSITIVE_KEYS:
            event_dict[key] = "[REDACTED]"
        else:
            event_dict[key] = _scrub_value(val)
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog logging with ISO timestamps, JSON formatting, and PII scrubbing."""
    logging.basicConfig(format="%(message)s", level=level.upper())
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            scrub_pii,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )
