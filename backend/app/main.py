from __future__ import annotations

import os
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from app.api.routes import router
from app.core.logging import bind_request_trace_id, configure_logging, reset_request_trace_id

configure_logging()

_origins_raw = os.environ.get("CORS_ORIGINS", "*").strip()
if _origins_raw == "*":
    _cors_origins: list[str] = ["*"]
else:
    _cors_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
    if not _cors_origins:
        _cors_origins = ["*"]

app = FastAPI(title="Autonomous AI Ops Manager", version="0.1.0")
app.include_router(router)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    raw = request.headers.get("x-request-id") or request.headers.get("x-correlation-id")
    tid = (raw or "").strip() or str(uuid.uuid4())
    token = bind_request_trace_id(tid)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = tid
        return response
    finally:
        reset_request_trace_id(token)


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
