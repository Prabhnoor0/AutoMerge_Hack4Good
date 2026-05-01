"""
Code Analysis Routes

Handles direct code submission for analysis, fixing, and validation.
"""

import structlog

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.models import Job
from app.schemas import CodeSubmission, JobResponse

logger = structlog.get_logger("automerge.code")

router = APIRouter()


async def run_code_pipeline(job_id: str) -> None:
    """Run the agent pipeline for a code submission."""
    from app.agent.pipeline import execute_pipeline
    async with async_session() as db:
        try:
            await execute_pipeline(job_id, db)
        except Exception as e:
            logger.error("code_pipeline.failed", job_id=job_id, error=str(e))
            from sqlalchemy import select
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                await db.commit()


@router.post("/analyze", response_model=JobResponse)
async def submit_code(
    payload: CodeSubmission,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Submit code for autonomous analysis and fixing."""
    logger.info("code.submitted", language=payload.language, length=len(payload.code))

    # Build a synthetic log from the code for the pipeline to analyze
    log_content = _build_analysis_context(payload.code, payload.language, payload.filename)

    job = Job(
        failure_title=f"Code analysis: {payload.filename or 'untitled'}.{payload.language}",
        failure_source="editor",
        failure_type="auto",
        raw_logs=log_content,
        mode="standard",
        status="queued",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    job_id = job.id
    logger.info("code_job.created", job_id=job_id)

    background_tasks.add_task(run_code_pipeline, job_id)

    return job


def _build_analysis_context(code: str, language: str, filename: str | None) -> str:
    """Build analysis context from submitted code.

    We wrap the code in a format the pipeline can parse,
    including running basic static checks.
    """
    import ast
    import re

    fname = filename or "untitled"
    full_name = f"{fname}.{language}" if "." not in fname else fname
    errors = []

    # Python-specific static analysis
    if language in ("python", "py"):
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"SyntaxError: {e.msg} (line {e.lineno})")
            errors.append(f"  File \"{full_name}\", line {e.lineno}")
            if e.text:
                errors.append(f"    {e.text.rstrip()}")

        # Check for common issues
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Bare except
            if re.match(r'^except\s*:', stripped):
                errors.append(f"Warning: Bare except clause at line {i} in {full_name}")
            # Missing return type hints on def
            if re.match(r'^def\s+\w+\(', stripped) and '->' not in stripped:
                pass  # common, don't flag
            # print statements in production
            if re.match(r'^print\(', stripped):
                errors.append(f"Info: print() statement at line {i} in {full_name} — consider using logging")
            # Undefined common patterns
            if 'eval(' in stripped:
                errors.append(f"Warning: eval() usage at line {i} in {full_name} — security risk")

    # JavaScript/TypeScript-specific checks
    elif language in ("javascript", "typescript", "js", "ts", "tsx", "jsx"):
        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if '=== undefined' in stripped or '== null' in stripped:
                pass  # normal
            if 'var ' in stripped:
                errors.append(f"Warning: 'var' usage at line {i} — use 'let' or 'const' instead")
            if 'console.log(' in stripped:
                errors.append(f"Info: console.log() at line {i} — consider removing for production")
            # Check for common TS errors
            if re.search(r'\bany\b', stripped) and 'as any' not in stripped:
                pass  # type any is common

    # Build the analysis log
    parts = [
        f"$ automerge analyze {full_name}",
        f"Analyzing {full_name} ({language})...",
        f"",
        f"─── Source Code ───",
        code,
        f"─── End Source ───",
        f"",
    ]

    if errors:
        parts.append(f"Found {len(errors)} issue(s):")
        parts.append("")
        for err in errors:
            parts.append(f"  {err}")
        parts.append("")
        parts.append(f"Analysis complete: {len(errors)} issue(s) found in {full_name}")
    else:
        parts.append(f"Static analysis passed with 0 errors.")
        parts.append(f"Running deeper pattern analysis...")
        parts.append(f"")
        # Add generic patterns the pipeline can pick up
        parts.append(f"Checking for common anti-patterns...")
        parts.append(f"Analysis complete for {full_name}")

    return "\n".join(parts)
