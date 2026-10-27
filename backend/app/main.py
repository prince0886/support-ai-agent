"""FastAPI application factory for SupportPilot AI."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .analysis import SupportAnalyst
from .config import Settings, get_settings
from .database import Base, build_engine, build_session_factory
from .llm import LLMClient
from .routers import knowledge, metrics, system, tickets
from .seed import seed_database

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )

    engine = build_engine(settings.resolved_database_url)
    session_factory = build_session_factory(engine)
    llm = LLMClient(settings)
    analyst = SupportAnalyst(settings, llm)

    Base.metadata.create_all(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ARG001
        if settings.seed_on_startup:
            try:
                result = await seed_database(session_factory, settings)
                if result["seeded"]:
                    logger.info("Demo data ready: %s tickets, %s articles", result["tickets"], result["articles"])
            except Exception:  # noqa: BLE001
                logger.exception("Seeding demo data failed; the API will start with an empty database")

        # Probe the model once so the dashboard never claims a live engine that
        # is not actually reachable.
        if llm.enabled:
            try:
                probe = await asyncio.wait_for(llm.ping(), timeout=15)
                if probe["ok"]:
                    logger.info("LLM reachable: %s", probe["detail"])
                else:
                    logger.warning("LLM unavailable, using the deterministic analyst: %s", probe["detail"])
            except Exception:  # noqa: BLE001
                logger.warning("LLM probe timed out; the deterministic analyst will handle requests")

        logger.info(
            "SupportPilot AI %s ready · AI mode: %s · model: %s",
            settings.app_version,
            llm.status()["mode"],
            settings.llm_model if llm.enabled else "built-in analyst",
        )
        yield
        engine.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Autonomous customer support teammate: classification, priority, grounded drafting and "
            "human-in-the-loop escalation."
        ),
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.llm = llm
    app.state.analyst = analyst
    app.state.last_reset_at = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (tickets.router, knowledge.router, metrics.router, system.router):
        app.include_router(router, prefix="/api")

    if FRONTEND_DIST.is_dir():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str, request: Request):
            candidate = (FRONTEND_DIST / full_path).resolve()
            if full_path and FRONTEND_DIST.resolve() in candidate.parents and candidate.is_file():
                return FileResponse(candidate)
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            if "." in Path(full_path).name:
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            return FileResponse(FRONTEND_DIST / "index.html")

    else:

        @app.get("/", include_in_schema=False)
        async def api_root() -> dict:
            return {
                "app": settings.app_name,
                "version": settings.app_version,
                "docs": "/docs",
                "health": "/api/health",
                "message": "Frontend build not found. Run `npm run dev` in ./frontend for the dashboard.",
            }

    return app


app = create_app()