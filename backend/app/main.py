from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.logging import configure_logging

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
