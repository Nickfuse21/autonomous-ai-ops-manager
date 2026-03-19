from __future__ import annotations

import logging
import sys
import uuid


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


def get_trace_id() -> str:
    return str(uuid.uuid4())


class TraceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("trace_id", self.extra.get("trace_id", "no-trace"))
        return msg, kwargs


def get_logger(trace_id: str) -> TraceLoggerAdapter:
    return TraceLoggerAdapter(logging.getLogger("ops-manager"), {"trace_id": trace_id})
