"""FastAPI application entry point.

Creates the FastAPI app instance and mounts feature routers as they are
added under app/api. Route handlers stay thin here; business logic
belongs in app/services.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import rooms, ws

app = FastAPI(title="Hostile Ledger API")

# CORS_ORIGINS, if set, is an explicit comma-separated allowlist for a real
# deployment. Without it, allow any port on localhost/127.0.0.1: Vite picks
# its own port and silently bumps to the next free one whenever 5173 is
# already taken (a stale dev server, another project, ...), so pinning a
# single dev port here just means the app breaks with a confusing "could
# not reach the server" the next time that happens.
_explicit_origins = os.environ.get("CORS_ORIGINS")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_explicit_origins.split(",") if _explicit_origins else [],
    allow_origin_regex=None if _explicit_origins else r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(rooms.router)
app.include_router(ws.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Report basic service liveness.

    Returns:
        A status payload confirming the API process is running.
    """
    return {"status": "ok"}
