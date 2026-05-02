"""
AR Debug Explorer — API Routes

Endpoints to generate AR scenes from existing structured data.
Fully isolated — does not modify any existing routes or services.
"""

import structlog
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.database import get_db
from app.models import Job
from app.services import ar_visualizer_service as ar_viz
from app.services.repo_explorer_service import _load_report as load_repo_report
from app.services.battle_service import get_session as get_battle_session, get_result as get_battle_result
from app.services.deploy_service import get_run as get_deploy_run

logger = structlog.get_logger("automerge.ar.routes")

router = APIRouter()


# ─── Studio Scene ─────────────────────────────────────────

@router.get("/scene/studio/{job_id}")
async def ar_studio_scene(job_id: str, db: AsyncSession = Depends(get_db)):
    """Generate an AR scene from a Studio analysis result."""
    try:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return {"status": "ok", "data": ar_viz.error_scene("studio", job_id, "Job not found")}

        await db.refresh(job, ["patches", "validation", "summary"])

        # Build a result dict from the stored job
        patch = job.patches[0] if job.patches else None
        validation = job.validation

        studio_result = {
            "language": patch.language if patch else "unknown",
            "root_cause": job.root_cause or "",
            "confidence": job.confidence_score or 0,
            "issues": [],  # Not persisted in DB — would need live re-analysis
            "explanation": "",
            "reasoning_trace": job.reasoning_trace or "",
            "original_code": patch.original_code if patch else "",
            "fixed_code": patch.fixed_code if patch else "",
            "diff_text": patch.diff_text if patch else "",
            "fix_explanation": patch.explanation if patch else "",
            "changes": [],
            "duration_ms": 0,
            "validation": {
                "status": validation.status,
                "tests_passed": validation.tests_passed,
                "tests_failed": validation.tests_failed,
                "tests_total": validation.tests_total,
                "stdout": validation.stdout,
                "re_parse_backend": "",
            } if validation else None,
            "refactor_suggestions": [],
            "quality_suggestions": [],
        }

        scene = ar_viz.studio_to_scene(job_id, studio_result)
        return {"status": "ok", "data": scene}
    except Exception as e:
        logger.warning("ar.studio_scene_failed", error=str(e)[:200])
        return {"status": "ok", "data": ar_viz.error_scene("studio", job_id, str(e)[:200])}


# ─── Repo Scene ───────────────────────────────────────────

@router.get("/scene/repo/{report_id}")
async def ar_repo_scene(report_id: str):
    """Generate an AR scene from a Repo Explorer report."""
    try:
        data = load_repo_report(report_id)
        if not data:
            return {"status": "ok", "data": ar_viz.error_scene("repo", report_id, "Report not found")}
        scene = ar_viz.repo_to_scene(report_id, data)
        return {"status": "ok", "data": scene}
    except Exception as e:
        logger.warning("ar.repo_scene_failed", error=str(e)[:200])
        return {"status": "ok", "data": ar_viz.error_scene("repo", report_id, str(e)[:200])}


# ─── Deploy Scene ─────────────────────────────────────────

@router.get("/scene/deploy/{run_id}")
async def ar_deploy_scene(run_id: str):
    """Generate an AR scene from a Deploy run."""
    try:
        run = get_deploy_run(run_id)
        if not run:
            return {"status": "ok", "data": ar_viz.error_scene("deploy", run_id, "Run not found")}
        scene = ar_viz.deploy_to_scene(run_id, run, analysis=None)
        return {"status": "ok", "data": scene}
    except Exception as e:
        logger.warning("ar.deploy_scene_failed", error=str(e)[:200])
        return {"status": "ok", "data": ar_viz.error_scene("deploy", run_id, str(e)[:200])}


# ─── Battle Scene ─────────────────────────────────────────

@router.get("/scene/battle/{session_id}")
async def ar_battle_scene(session_id: str):
    """Generate an AR scene from a Battle session."""
    try:
        session = get_battle_result(session_id) or get_battle_session(session_id)
        if not session:
            return {"status": "ok", "data": ar_viz.error_scene("battle", session_id, "Session not found")}
        scene = ar_viz.battle_to_scene(session_id, session)
        return {"status": "ok", "data": scene}
    except Exception as e:
        logger.warning("ar.battle_scene_failed", error=str(e)[:200])
        return {"status": "ok", "data": ar_viz.error_scene("battle", session_id, str(e)[:200])}


# ─── Live Studio Scene (from POST payload) ────────────────

@router.post("/scene/studio/live")
async def ar_studio_scene_live(payload: dict):
    """Generate an AR scene from a live Studio result (without DB lookup)."""
    try:
        job_id = payload.get("job_id", "live")
        scene = ar_viz.studio_to_scene(job_id, payload)
        return {"status": "ok", "data": scene}
    except Exception as e:
        logger.warning("ar.studio_live_failed", error=str(e)[:200])
        return {"status": "ok", "data": ar_viz.error_scene("studio", "live", str(e)[:200])}


# ─── History ──────────────────────────────────────────────

@router.get("/history")
async def ar_history():
    """Get AR scene view history."""
    return {"status": "ok", "data": ar_viz.get_history()}


@router.delete("/history/{scene_id}")
async def ar_delete_history(scene_id: str):
    """Delete an AR history entry."""
    deleted = ar_viz.delete_history_item(scene_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="History entry not found")
    return {"status": "ok", "message": "Deleted"}


# ─── Health ───────────────────────────────────────────────

@router.get("/health")
async def ar_health():
    return {
        "status": "ok",
        "module": "ar-debug-explorer",
        "version": "1.0.0",
        "sources": ["studio", "repo", "deploy", "battle"],
    }
