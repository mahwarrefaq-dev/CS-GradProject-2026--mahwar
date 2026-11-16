"""FastAPI application of «محور». Serves the API under /api and, after
`npm run build`, the built frontend (ARC-01: one backend on one machine)."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.errors import register_error_handlers
from app.routers import auth, health, projects, tasks, users

app = FastAPI(title="Mahwar API", version="0.1.0")
register_error_handlers(app)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")    # API-01
app.include_router(users.router, prefix="/api")   # API-02
app.include_router(projects.router, prefix="/api")  # API-03, API-04, API-05
app.include_router(tasks.router, prefix="/api")     # API-06 + my tasks (SCR-05)
# Routers of API-01..API-16 are added here release by release (Chapter 4, Table 4.3).

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
