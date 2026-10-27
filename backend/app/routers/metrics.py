"""Dashboard metrics endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..metrics import compute_metrics
from ..schemas import MetricsResponse

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsResponse)
def metrics_endpoint(session: Session = Depends(get_db)) -> dict:
    return compute_metrics(session)