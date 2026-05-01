"""
Job Routes

CRUD operations for agent fix jobs.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Job
from app.schemas import JobResponse, JobDetailResponse

router = APIRouter()


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all jobs, optionally filtered by status."""
    query = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if status:
        query = query.where(Job.status == status)

    result = await db.execute(query)
    jobs = result.scalars().all()
    return jobs


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get full job details including steps, patches, and validation."""
    query = (
        select(Job)
        .options(
            selectinload(Job.steps),
            selectinload(Job.patches),
            selectinload(Job.validation),
            selectinload(Job.summary),
        )
        .where(Job.id == job_id)
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return job


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a job and all related data."""
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    await db.delete(job)
    return {"message": f"Job {job_id} deleted"}
