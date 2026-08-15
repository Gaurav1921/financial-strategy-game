"""FastAPI application entry point.

Creates the FastAPI app instance and mounts feature routers as they are
added under app/api. Route handlers stay thin here; business logic
belongs in app/services.
"""

from fastapi import FastAPI

app = FastAPI(title="Consortium API")


@app.get("/health")
def health() -> dict[str, str]:
    """Report basic service liveness.

    Returns:
        A status payload confirming the API process is running.
    """
    return {"status": "ok"}
