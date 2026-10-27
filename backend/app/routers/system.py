"""System status, live AI connectivity test and demo reset."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..schemas import AITestResponse, DemoResetResponse, HealthResponse, SystemStatusResponse
from ..seed import reset_database
from ..serializers import iso
from ..service import ticket_counts
from ..utils import utcnow

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> dict:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "version": settings.app_version,
        "database": settings.resolved_database_url.split("?")[0],
    }


@router.get("/system/status", response_model=SystemStatusResponse)
def status(request: Request) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    ai = llm.status()
    ai["last_success_at"] = iso(ai.get("last_success_at"))
    ai["last_error_at"] = iso(ai.get("last_error_at"))

    session_factory = request.app.state.session_factory
    with session_factory() as session:
        counts = ticket_counts(session)

    return {
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "environment": settings.app_env,
        "demo_reset_enabled": settings.demo_reset_enabled,
        "retrieval_top_k": settings.retrieval_top_k,
        "ai": ai,
        "counts": counts,
    }


@router.post("/system/ai/test", response_model=AITestResponse)
async def ai_test(request: Request) -> dict:
    settings = request.app.state.settings
    llm = request.app.state.llm
    result = await llm.ping()
    return {
        "ok": bool(result["ok"]),
        "detail": str(result["detail"]),
        "latency_ms": result.get("latency_ms"),
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "mode": llm.status()["mode"],
    }


@router.post("/system/demo/reset", response_model=DemoResetResponse)
async def demo_reset(request: Request) -> dict:
    settings = request.app.state.settings
    if not settings.demo_reset_enabled:
        raise HTTPException(status_code=403, detail="Demo reset is disabled for this deployment")

    result = await reset_database(
        request.app.state.engine,
        request.app.state.session_factory,
        settings,
    )
    request.app.state.last_reset_at = utcnow()
    return {"reset": True, "tickets": result["tickets"], "articles": result["articles"]}