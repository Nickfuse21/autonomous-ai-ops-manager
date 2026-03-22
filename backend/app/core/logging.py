from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar, Token
from typing import Any

# Propagated per HTTP request via middleware; falls back to fresh UUID when unset.
_current_trace_id: ContextVar[str | None] = ContextVar("_current_trace_id", default=None)


class TraceIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = "system"
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(TraceIdFilter())

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s trace=%(trace_id)s %(message)s",
        handlers=[handler],
    )


def bind_request_trace_id(trace_id: str) -> Token[Any]:
    """Attach a trace/correlation id for the current async context (HTTP request)."""
    return _current_trace_id.set(trace_id)


def reset_request_trace_id(token: Token[Any]) -> None:
    _current_trace_id.reset(token)


def get_trace_id() -> str:
    existing = _current_trace_id.get()
    if existing:
        return existing
    return str(uuid.uuid4())


class TraceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("trace_id", self.extra.get("trace_id", "no-trace"))
        return msg, kwargs


def get_logger(trace_id: str) -> TraceLoggerAdapter:
    return TraceLoggerAdapter(logging.getLogger("ops-manager"), {"trace_id": trace_id})
