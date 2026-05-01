"""
Health and System Routes

Provides health check and diagnostics endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Job, BugPattern
from app.schemas import HealthResponse, SystemDiagnostics, BugPatternResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        database="connected",
        demo_mode=settings.DEMO_MODE,
        integrations={
            "llm": settings.has_llm,
            "github": settings.has_github,
            "slack": settings.has_slack,
        },
    )


@router.get("/diagnostics", response_model=SystemDiagnostics)
async def system_diagnostics(db: AsyncSession = Depends(get_db)):
    """System diagnostics and statistics."""
    # Total jobs
    total_result = await db.execute(select(func.count(Job.id)))
    total_jobs = total_result.scalar() or 0

    # Jobs by status
    status_result = await db.execute(
        select(Job.status, func.count(Job.id)).group_by(Job.status)
    )
    jobs_by_status = {row[0]: row[1] for row in status_result.fetchall()}

    # Total bug patterns
    pattern_result = await db.execute(select(func.count(BugPattern.id)))
    total_patterns = pattern_result.scalar() or 0

    # Average confidence
    avg_result = await db.execute(select(func.avg(Job.confidence_score)))
    avg_confidence = round(avg_result.scalar() or 0.0, 2)

    # Success rate
    completed = jobs_by_status.get("completed", 0)
    success_rate = round(completed / total_jobs * 100, 1) if total_jobs > 0 else 0.0

    return SystemDiagnostics(
        total_jobs=total_jobs,
        jobs_by_status=jobs_by_status,
        total_patterns=total_patterns,
        avg_confidence=avg_confidence,
        success_rate=success_rate,
    )


@router.get("/patterns", response_model=list[BugPatternResponse])
async def list_patterns(db: AsyncSession = Depends(get_db)):
    """List all known bug patterns from agent memory."""
    result = await db.execute(
        select(BugPattern).order_by(BugPattern.occurrence_count.desc()).limit(50)
    )
    return result.scalars().all()
