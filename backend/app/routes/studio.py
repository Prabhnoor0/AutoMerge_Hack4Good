"""
Code Debug Studio — API Routes

Completely isolated route group for the Code Debug Studio feature.
Does not modify or interfere with any existing routes.
"""

import structlog
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Job
from app.services.studio_service import (
    run_studio_pipeline,
    detect_language,
    get_demo_sample,
    list_demo_samples,
)
from app.services.github import GitHubClient, parse_repo_url
from app.services import llm_service
from app.config import settings

logger = structlog.get_logger("automerge.studio")

router = APIRouter()


# ─── Request / Response Schemas ───────────────────────────

class StudioSubmitRequest(BaseModel):
    """Submit code to the Code Debug Studio."""
    code: str = Field(..., min_length=1, description="Source code to analyze")
    language: str = Field(default="auto", description="Language (auto-detect if blank)")
    filename: str = Field(default="", description="Optional filename")
    logs: str = Field(default="", description="Error logs / console output")
    modes: list[str] = Field(
        default=["debug", "fix"],
        description="Analysis modes: debug, explain, fix, patch, validate, refactor, quality, pr"
    )
    # Optional GitHub
    repo_url: str = Field(default="", description="GitHub repo URL")
    token: str = Field(default="", description="GitHub token")
    branch: str = Field(default="main", description="Branch name")
    file_path: str = Field(default="", description="File path in repo")


class StudioIssue(BaseModel):
    id: str = ""
    line: int = 0
    severity: str = ""
    message: str = ""
    explanation: str = ""
    fix_hint: str = ""
    category: str = ""
    source_line: str = ""
    code_frame: str = ""
    confidence: float = 0.0
    origin: str = ""
    parser_name: str = ""
    backend_name: str = ""


class StudioValidation(BaseModel):
    status: str = ""
    tests_passed: int = 0
    tests_failed: int = 0
    tests_total: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    # New fields from real re-parse validation (backward-compatible)
    re_parse_backend: str = ""
    remaining_issues: list[dict] = []


class StudioRefactorSuggestion(BaseModel):
    line: int = 0
    category: str = ""
    suggestion: str = ""
    example: str = ""
    source_line: str = ""


class StudioQualitySuggestion(BaseModel):
    category: str = ""
    suggestion: str = ""
    severity: str = ""
    line: int | None = None


class StudioPRData(BaseModel):
    pr_title: str = ""
    pr_body: str = ""
    file_path: str = ""


class StudioResponse(BaseModel):
    """Full Code Debug Studio analysis result."""
    job_id: str
    status: str
    language: str
    # Analysis
    issues: list[StudioIssue]
    root_cause: str
    explanation: str = ""
    confidence: float
    reasoning_trace: str
    # Fix
    original_code: str
    fixed_code: str
    diff_text: str
    fix_explanation: str = ""
    changes: list[str] = []
    # Validation
    validation: StudioValidation | None = None
    # Refactor
    refactor_suggestions: list[StudioRefactorSuggestion] = []
    # Quality
    quality_suggestions: list[StudioQualitySuggestion] = []
    # PR
    pr_data: StudioPRData | None = None
    pr_result: dict | None = None
    # Meta
    modes_executed: list[str]
    duration_ms: int
    created_at: str
    # ── AutoMerge Mentor (LLM-enhanced, optional) ──
    ai_explanation: str = ""
    ai_fix_hint: str = ""
    ai_root_cause: str = ""
    ai_test_suggestion: str = ""
    ai_pr_title: str = ""
    ai_pr_summary: str = ""
    ai_enabled: bool = False


class StudioDemoRequest(BaseModel):
    sample: str = Field(default="python_buggy", description="Demo sample name")
    modes: list[str] = Field(default=["debug", "explain", "fix", "validate"])


# ─── Routes ──────────────────────────────────────────────

@router.post("/submit", response_model=StudioResponse)
async def studio_submit(
    payload: StudioSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit code to the Code Debug Studio for analysis.

    Runs the full pipeline synchronously and returns results immediately.
    """
    logger.info(
        "studio.submit",
        language=payload.language,
        modes=payload.modes,
        code_len=len(payload.code),
    )

    # Run analysis pipeline
    result = run_studio_pipeline(
        code=payload.code,
        language=payload.language,
        filename=payload.filename,
        logs=payload.logs,
        modes=payload.modes,
    )

    # ── AutoMerge Mentor: LLM enhancement (non-blocking) ──
    mentor = {}
    if settings.has_llm and result.get("issues"):
        try:
            import asyncio
            ai_explanation, ai_fix_hint, ai_root_cause, ai_test = await asyncio.gather(
                llm_service.generate_explanation(payload.code, result["issues"], result["language"]),
                llm_service.generate_fix_hint(payload.code, result["issues"], result["language"]),
                llm_service.generate_root_cause_summary(payload.code, result["issues"], result["language"]),
                llm_service.generate_test_suggestion(payload.code, result["issues"], result["language"]),
                return_exceptions=True,
            )
            mentor["ai_explanation"] = ai_explanation if isinstance(ai_explanation, str) else ""
            mentor["ai_fix_hint"] = ai_fix_hint if isinstance(ai_fix_hint, str) else ""
            mentor["ai_root_cause"] = ai_root_cause if isinstance(ai_root_cause, str) else ""
            mentor["ai_test_suggestion"] = ai_test if isinstance(ai_test, str) else ""
            mentor["ai_enabled"] = True

            # Enhance PR data with LLM if available
            if result.get("pr_data") and result.get("changes"):
                ai_pr = await llm_service.generate_pr_body(
                    result["root_cause"], result["changes"], result["language"], result["confidence"]
                )
                if ai_pr and isinstance(ai_pr, dict):
                    mentor["ai_pr_title"] = ai_pr.get("title", "") or ""
                    mentor["ai_pr_summary"] = ai_pr.get("summary", "") or ""
        except Exception as e:
            logger.warning("studio.mentor_failed", error=str(e)[:200])

    # Save as a Job for history
    job = Job(
        failure_title=f"Studio: {payload.filename or 'untitled'}.{result['language']}",
        failure_source="studio",
        failure_type=_classify_type(result["issues"]),
        raw_logs=payload.logs or payload.code[:500],
        mode="studio",
        status="completed",
        confidence_score=result["confidence"],
        root_cause=result["root_cause"],
        reasoning_trace=result["reasoning_trace"],
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    # Save patch if fix was generated
    if result.get("diff_text"):
        from app.models import Patch
        patch = Patch(
            job_id=job.id,
            file_path=payload.filename or f"code.{result['language']}",
            original_code=result["original_code"],
            fixed_code=result["fixed_code"],
            diff_text=result["diff_text"],
            explanation=result.get("fix_explanation", ""),
            language=result["language"],
        )
        db.add(patch)

    # Save validation if present
    if result.get("validation"):
        from app.models import ValidationResult
        v = result["validation"]
        validation = ValidationResult(
            job_id=job.id,
            status=v["status"],
            stdout=v["stdout"],
            stderr=v.get("stderr", ""),
            tests_passed=v["tests_passed"],
            tests_failed=v["tests_failed"],
            tests_total=v["tests_total"],
            duration_seconds=v["duration_seconds"],
        )
        db.add(validation)

    # Save summary if PR data present
    if result.get("pr_data"):
        from app.models import Summary
        pd = result["pr_data"]
        summary = Summary(
            job_id=job.id,
            title=job.failure_title,
            root_cause=result["root_cause"],
            fix_description=result.get("fix_explanation", ""),
            pr_title=pd["pr_title"],
            pr_body=pd["pr_body"],
            reasoning_trace=result["reasoning_trace"],
            impact_assessment="Low risk" if result["confidence"] > 0.8 else "Medium risk — review recommended",
        )
        db.add(summary)

    await db.commit()

    # Handle GitHub PR creation if requested
    pr_result = None
    if "pr" in payload.modes and payload.token and payload.repo_url:
        pr_result = await _create_studio_pr(
            job_id=job.id,
            token=payload.token,
            repo_url=payload.repo_url,
            branch=payload.branch,
            file_path=payload.file_path or payload.filename,
            fixed_code=result["fixed_code"],
            pr_data=result.get("pr_data", {}),
            db=db,
        )

    # Build response
    return StudioResponse(
        job_id=job.id,
        status="completed",
        language=result["language"],
        issues=[StudioIssue(**{k: i.get(k, "") for k in StudioIssue.model_fields}) for i in result["issues"][:20]],
        root_cause=result["root_cause"],
        explanation=result.get("explanation", ""),
        confidence=result["confidence"],
        reasoning_trace=result["reasoning_trace"],
        original_code=result["original_code"],
        fixed_code=result["fixed_code"],
        diff_text=result["diff_text"],
        fix_explanation=result.get("fix_explanation", ""),
        changes=result.get("changes", []),
        validation=StudioValidation(**result["validation"]) if result.get("validation") else None,
        refactor_suggestions=[StudioRefactorSuggestion(**s) for s in result.get("refactor_suggestions", [])],
        quality_suggestions=[StudioQualitySuggestion(**s) for s in result.get("quality_suggestions", [])],
        pr_data=StudioPRData(**result["pr_data"]) if result.get("pr_data") else None,
        pr_result=pr_result,
        modes_executed=result["modes_executed"],
        duration_ms=result["duration_ms"],
        created_at=job.created_at.isoformat() if job.created_at else "",
        # AutoMerge Mentor
        ai_explanation=mentor.get("ai_explanation", ""),
        ai_fix_hint=mentor.get("ai_fix_hint", ""),
        ai_root_cause=mentor.get("ai_root_cause", ""),
        ai_test_suggestion=mentor.get("ai_test_suggestion", ""),
        ai_pr_title=mentor.get("ai_pr_title", ""),
        ai_pr_summary=mentor.get("ai_pr_summary", ""),
        ai_enabled=mentor.get("ai_enabled", False),
    )


@router.get("/{job_id}", response_model=StudioResponse)
async def studio_get_result(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get a saved Studio analysis result by job ID."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Studio result not found")

    if job.mode != "studio" and job.failure_source != "studio":
        raise HTTPException(status_code=404, detail="Not a Studio result")

    await db.refresh(job, ["patches", "validation", "summary"])

    patch = job.patches[0] if job.patches else None
    validation = job.validation

    return StudioResponse(
        job_id=job.id,
        status=job.status,
        language=patch.language if patch else "unknown",
        issues=[],  # Issues not stored in DB — only in live response
        root_cause=job.root_cause or "",
        explanation="",
        confidence=job.confidence_score,
        reasoning_trace=job.reasoning_trace or "",
        original_code=patch.original_code if patch else "",
        fixed_code=patch.fixed_code if patch else "",
        diff_text=patch.diff_text if patch else "",
        fix_explanation=patch.explanation if patch else "",
        changes=[],
        validation=StudioValidation(
            status=validation.status,
            tests_passed=validation.tests_passed,
            tests_failed=validation.tests_failed,
            tests_total=validation.tests_total,
            stdout=validation.stdout,
            stderr=validation.stderr,
            duration_seconds=validation.duration_seconds,
        ) if validation else None,
        refactor_suggestions=[],
        quality_suggestions=[],
        pr_data=None,
        pr_result=None,
        modes_executed=[],
        duration_ms=0,
        created_at=job.created_at.isoformat() if job.created_at else "",
    )


@router.get("/history/list")
async def studio_history(db: AsyncSession = Depends(get_db)):
    """List all Studio analysis results."""
    result = await db.execute(
        select(Job)
        .where(Job.failure_source == "studio")
        .order_by(Job.created_at.desc())
        .limit(50)
    )
    jobs = result.scalars().all()

    return [
        {
            "job_id": j.id,
            "title": j.failure_title,
            "status": j.status,
            "confidence": j.confidence_score,
            "root_cause": (j.root_cause or "")[:100],
            "created_at": j.created_at.isoformat() if j.created_at else "",
        }
        for j in jobs
    ]


@router.post("/demo")
async def studio_demo(
    payload: StudioDemoRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a demo analysis with pre-loaded sample code."""
    sample = get_demo_sample(payload.sample)
    if not sample:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown demo sample. Available: {', '.join(list_demo_samples())}"
        )

    # Run as a normal submission
    result = run_studio_pipeline(
        code=sample["code"],
        language=sample["language"],
        filename=sample["filename"],
        logs=sample.get("logs", ""),
        modes=payload.modes,
    )

    # Save to DB
    job = Job(
        failure_title=f"Studio Demo: {sample['filename']}",
        failure_source="studio",
        failure_type=_classify_type(result["issues"]),
        raw_logs=sample.get("logs", ""),
        mode="studio",
        status="completed",
        confidence_score=result["confidence"],
        root_cause=result["root_cause"],
        reasoning_trace=result["reasoning_trace"],
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    if result.get("diff_text"):
        from app.models import Patch
        patch = Patch(
            job_id=job.id,
            file_path=sample["filename"],
            original_code=result["original_code"],
            fixed_code=result["fixed_code"],
            diff_text=result["diff_text"],
            explanation=result.get("fix_explanation", ""),
            language=result["language"],
        )
        db.add(patch)

    await db.commit()

    return {
        "job_id": job.id,
        "language": result["language"],
        "issues_count": len(result["issues"]),
        "root_cause": result["root_cause"],
        "confidence": result["confidence"],
        "has_fix": bool(result["diff_text"]),
        "modes_executed": result["modes_executed"],
        "sample_code": sample["code"],
        "sample_logs": sample.get("logs", ""),
        "sample_filename": sample["filename"],
    }


@router.get("/demos/list")
async def studio_list_demos():
    """List available demo samples."""
    samples = list_demo_samples()
    result = []
    for name in samples:
        sample = get_demo_sample(name)
        if sample:
            result.append({
                "name": name,
                "language": sample["language"],
                "filename": sample["filename"],
                "has_logs": bool(sample.get("logs")),
            })
    return result


@router.get("/health/check")
async def studio_health():
    """Health check for the Studio module."""
    return {
        "status": "ok",
        "module": "code-debug-studio",
        "version": "1.0.0",
        "modes": ["debug", "explain", "fix", "patch", "validate", "refactor", "quality", "pr"],
        "languages": ["python", "javascript", "typescript", "java", "go", "rust", "cpp"],
    }


@router.post("/pr/create")
async def studio_create_pr(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """Create a PR for a Studio result."""
    job_id = payload.get("job_id", "")
    token = payload.get("token", "")
    repo_url = payload.get("repo_url", "")
    branch = payload.get("branch", "main")
    file_path = payload.get("file_path", "")

    if not job_id or not token or not repo_url:
        raise HTTPException(status_code=400, detail="job_id, token, and repo_url are required")

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Studio result not found")

    await db.refresh(job, ["patches", "summary"])

    if not job.patches:
        raise HTTPException(status_code=400, detail="No fix available for this result")

    patch = job.patches[0]
    summary = job.summary

    pr_result = await _create_studio_pr(
        job_id=job.id,
        token=token,
        repo_url=repo_url,
        branch=branch,
        file_path=file_path or patch.file_path,
        fixed_code=patch.fixed_code,
        pr_data={
            "pr_title": summary.pr_title if summary else f"fix: {job.failure_title}",
            "pr_body": summary.pr_body if summary else f"AutoMerge fix for: {job.root_cause}",
            "file_path": file_path or patch.file_path,
        },
        db=db,
    )

    return pr_result


# ─── Internal helpers ─────────────────────────────────────

async def _create_studio_pr(
    job_id: str,
    token: str,
    repo_url: str,
    branch: str,
    file_path: str,
    fixed_code: str,
    pr_data: dict,
    db: AsyncSession,
) -> dict:
    """Create a GitHub PR for a studio fix."""
    try:
        owner, repo_name = parse_repo_url(repo_url)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    client = GitHubClient(token, owner, repo_name)
    branch_name = f"automerge/studio-fix-{job_id}"

    # Step 1: Create branch
    branch_result = await client.create_branch(branch_name, branch)
    if not branch_result.get("success"):
        return {"success": False, "error": f"Branch failed: {branch_result.get('error')}"}

    # Step 2: Commit
    commit_result = await client.commit_file(
        branch_name,
        file_path or "fix.py",
        fixed_code,
        pr_data.get("pr_title", f"fix: studio fix for {job_id}"),
    )
    if not commit_result.get("success"):
        return {"success": False, "error": f"Commit failed: {commit_result.get('error')}"}

    # Step 3: Create PR
    pr_result = await client.create_pr(
        branch_name,
        pr_data.get("pr_title", "AutoMerge Studio Fix"),
        pr_data.get("pr_body", ""),
        branch,
    )
    if not pr_result.get("success"):
        return {"success": False, "error": f"PR failed: {pr_result.get('error')}"}

    # Update job
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job:
        job.github_branch_name = branch_name
        job.github_commit_sha = commit_result.get("commit_sha", "")
        job.github_pr_url = pr_result.get("pr_url", "")
        job.github_pr_number = pr_result.get("pr_number")
        await db.commit()

    return {
        "success": True,
        "branch": branch_result,
        "commit": commit_result,
        "pr": pr_result,
        "is_mock": client.is_mock,
    }


def _classify_type(issues: list[dict]) -> str:
    """Classify failure type from issues."""
    if any(i["severity"] == "error" for i in issues):
        return "build_error"
    if any(i["severity"] == "security" for i in issues):
        return "security"
    if any(i["severity"] == "bug" for i in issues):
        return "runtime_error"
    if any(i["severity"] == "warning" for i in issues):
        return "code_quality"
    return "clean"
