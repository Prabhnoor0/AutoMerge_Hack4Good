"""
Failure Ingestion Routes

Handles incoming failure reports and triggers the agent pipeline.
"""

import asyncio
import structlog

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.models import Job
from app.schemas import FailureInput, JobResponse, DemoTriggerRequest, DemoTriggerResponse

logger = structlog.get_logger("automerge.failures")

router = APIRouter()


async def run_agent_pipeline(job_id: str) -> None:
    """Run the agent pipeline in background. Imported lazily to avoid circular imports."""
    from app.agent.pipeline import execute_pipeline
    async with async_session() as db:
        try:
            await execute_pipeline(job_id, db)
        except Exception as e:
            logger.error("pipeline.failed", job_id=job_id, error=str(e))
            # Mark job as failed
            from sqlalchemy import select
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                await db.commit()


@router.post("/failures", response_model=JobResponse)
async def ingest_failure(
    payload: FailureInput,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a build/test failure and start the agent pipeline."""
    logger.info("failure.ingested", title=payload.title, source=payload.source)

    # Create the job
    job = Job(
        failure_title=payload.title,
        failure_source=payload.source,
        failure_type=payload.failure_type if payload.failure_type != "auto" else "unknown",
        raw_logs=payload.logs,
        mode=payload.mode,
        status="queued",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    job_id = job.id
    logger.info("job.created", job_id=job_id)

    # Trigger pipeline in background
    background_tasks.add_task(run_agent_pipeline, job_id)

    return job


@router.post("/demo/trigger", response_model=DemoTriggerResponse)
async def trigger_demo(
    payload: DemoTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a demo scenario with seeded failure data."""
    from app.demo.sample_failures import get_demo_scenario

    logger.info("demo.triggered", scenario=payload.scenario)

    scenario = get_demo_scenario(payload.scenario)

    # Create job from demo scenario
    job = Job(
        failure_title=scenario["title"],
        failure_source="demo",
        failure_type=scenario["failure_type"],
        raw_logs=scenario["logs"],
        mode="demo",
        status="queued",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    job_id = job.id

    # Trigger pipeline in background
    background_tasks.add_task(run_agent_pipeline, job_id)

    return DemoTriggerResponse(
        job_id=job_id,
        message=f"Demo scenario '{payload.scenario}' triggered successfully",
    )
