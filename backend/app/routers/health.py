"""Environment check endpoints (not part of API-01..API-16)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # database not reachable or wrong credentials
        raise HTTPException(status_code=503, detail="تعذر الاتصال بقاعدة البيانات") from exc
    return {"database": "ok"}
