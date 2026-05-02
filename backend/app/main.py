"""
AutoMerge — Main Application Entry Point

FastAPI app with CORS, lifecycle management, and route registration.
"""

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.failures import router as failures_router
from app.routes.code import router as code_router
from app.routes.github import router as github_router
from app.routes.studio import router as studio_router
from app.routes.devmitra import router as devmitra_router
from app.routes.classroom import router as classroom_router
from app.routes.repo_explorer import router as repo_explorer_router
from app.routes.deploy import router as deploy_router
from app.routes.battle import router as battle_router
from app.routes.ar import router as ar_router
from app.routes.sandbox import router as sandbox_router
from app.routes.extension import router as extension_router
from app.routes.auth import router as auth_router


# ─── Structured Logging Setup ─────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("automerge")


# ─── Application Lifecycle ────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("automerge.starting", version="1.0.0", demo_mode=settings.DEMO_MODE)

    # Initialize database
    await init_db()
    logger.info("automerge.database_ready")

    # Log integration status
    logger.info(
        "automerge.integrations",
        llm=settings.has_llm,
        github=settings.has_github,
        slack=settings.has_slack,
    )

    yield

    logger.info("automerge.shutdown")


# ─── FastAPI App ──────────────────────────────────────────

app = FastAPI(
    title="AutoMerge",
    description="Autonomous debugging and code-fixing platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router, prefix="/api", tags=["system"])
app.include_router(jobs_router, prefix="/api", tags=["jobs"])
app.include_router(failures_router, prefix="/api", tags=["failures"])
app.include_router(code_router, prefix="/api/code", tags=["code"])
app.include_router(github_router, prefix="/api/github", tags=["github"])
app.include_router(studio_router, prefix="/api/studio", tags=["studio"])
app.include_router(devmitra_router, prefix="/api/devmitra", tags=["devmitra"])
app.include_router(classroom_router, prefix="/api/classroom", tags=["classroom"])
app.include_router(repo_explorer_router, prefix="/api/repo-explorer", tags=["repo-explorer"])
app.include_router(deploy_router, prefix="/api/deploy", tags=["deploy"])
app.include_router(battle_router, prefix="/api/battle", tags=["battle"])
app.include_router(ar_router, prefix="/api/ar", tags=["ar-debug-explorer"])
app.include_router(sandbox_router, prefix="/api/sandbox", tags=["sandbox"])
app.include_router(extension_router, prefix="/api/extension", tags=["extension"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
