"""
Classroom Routes

API endpoints for the developer learning classroom.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ClassroomReport
from app.schemas import (
    ClassroomReportResponse,
    ClassroomReportUpdate,
    ClassroomSummary,
    ResourceItem,
)
from app.services.classroom_service import generate_reports

router = APIRouter()


def _serialize_report(report: ClassroomReport) -> dict:
    """Convert a ClassroomReport ORM instance to a response-ready dict."""
    try:
        evidence = json.loads(report.evidence) if report.evidence else []
    except (json.JSONDecodeError, TypeError):
        evidence = []

    try:
        resources_raw = json.loads(report.resources) if report.resources else []
        resources = [ResourceItem(**r) for r in resources_raw]
    except (json.JSONDecodeError, TypeError):
        resources = []

    return {
        "id": report.id,
        "title": report.title,
        "topic_name": report.topic_name,
        "topic_category": report.topic_category,
        "weakness_summary": report.weakness_summary,
        "why_it_matters": report.why_it_matters,
        "evidence": evidence,
        "resources": [r.model_dump() for r in resources],
        "occurrence_count": report.occurrence_count,
        "severity_score": report.severity_score,
        "status": report.status,
        "revision_done": report.revision_done,
        "notes": report.notes or "",
        "report_date": report.report_date,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }


@router.get("/reports", response_model=list[ClassroomReportResponse])
async def list_reports(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all classroom reports, optionally filtered by status."""
    query = select(ClassroomReport).order_by(
        ClassroomReport.severity_score.desc(),
        ClassroomReport.occurrence_count.desc(),
    )
    if status:
        query = query.where(ClassroomReport.status == status)

    result = await db.execute(query)
    reports = result.scalars().all()
    return [_serialize_report(r) for r in reports]


@router.get("/summary", response_model=ClassroomSummary)
async def classroom_summary(db: AsyncSession = Depends(get_db)):
    """Get high-level classroom stats."""
    total = (await db.execute(select(func.count(ClassroomReport.id)))).scalar() or 0
    open_count = (
        await db.execute(
            select(func.count(ClassroomReport.id)).where(ClassroomReport.status == "open")
        )
    ).scalar() or 0
    revision_done = (
        await db.execute(
            select(func.count(ClassroomReport.id)).where(ClassroomReport.revision_done == True)
        )
    ).scalar() or 0
    completed = (
        await db.execute(
            select(func.count(ClassroomReport.id)).where(ClassroomReport.status == "completed")
        )
    ).scalar() or 0

    return ClassroomSummary(
        total_reports=total,
        open_reports=open_count,
        revision_done_count=revision_done,
        completed_count=completed,
    )


@router.get("/reports/{report_id}", response_model=ClassroomReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single classroom report by ID."""
    result = await db.execute(
        select(ClassroomReport).where(ClassroomReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize_report(report)


@router.post("/reports/refresh", response_model=list[ClassroomReportResponse])
async def refresh_reports(db: AsyncSession = Depends(get_db)):
    """Generate or refresh classroom reports from current job/pattern data."""
    await generate_reports(db)

    # Return all current reports
    result = await db.execute(
        select(ClassroomReport).order_by(
            ClassroomReport.severity_score.desc(),
            ClassroomReport.occurrence_count.desc(),
        )
    )
    reports = result.scalars().all()
    return [_serialize_report(r) for r in reports]


@router.patch("/reports/{report_id}", response_model=ClassroomReportResponse)
async def update_report(
    report_id: str,
    update: ClassroomReportUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a classroom report's status, revision_done, or notes."""
    result = await db.execute(
        select(ClassroomReport).where(ClassroomReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if update.status is not None:
        report.status = update.status
    if update.revision_done is not None:
        report.revision_done = update.revision_done
    if update.notes is not None:
        report.notes = update.notes

    await db.commit()
    await db.refresh(report)
    return _serialize_report(report)


@router.delete("/reports/{report_id}")
async def delete_report(report_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a classroom report."""
    result = await db.execute(
        select(ClassroomReport).where(ClassroomReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    await db.delete(report)
    await db.commit()
    return {"message": "Report deleted"}
