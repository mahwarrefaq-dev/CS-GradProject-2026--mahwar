"""FastAPI application of «محور». Serves the API under /api and, after
`npm run build`, the built frontend (ARC-01: one backend on one machine)."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import health

app = FastAPI(title="Mahwar API", version="0.1.0")

app.include_router(health.router, prefix="/api")
# Routers of API-01..API-16 are added here release by release (Chapter 4, Table 4.3).

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
