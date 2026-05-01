"""
GitHub Integration Routes

Handles the full GitHub workflow:
  - Validate token + repo access
  - Analyze repo code (fetch file → run pipeline → return results)
  - Create PR (branch → commit fix → open PR)
  - Merge PR (with confirmation)
  - Legacy status/connect/disconnect for backward compat
"""

import re
import structlog

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session
from app.models import Job
from app.schemas import (
    RepoValidateRequest,
    RepoAnalysisRequest,
    PRCreateRequest,
    PRMergeRequest,
    JobResponse,
)
from app.services.github import GitHubClient, create_github_client, parse_repo_url

logger = structlog.get_logger("automerge.github_routes")

router = APIRouter()


# ─── Repo Validation ──────────────────────────────────────

@router.post("/repo/validate")
async def validate_repo(payload: RepoValidateRequest):
    """Validate GitHub token and repo access."""
    try:
        client = create_github_client(payload.token, payload.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Step 1: Validate token
    token_result = await client.validate_token()
    if not token_result.get("valid"):
        return {
            "valid": False,
            "stage": "token",
            "error": token_result.get("error", "Token validation failed"),
        }

    # Step 2: Validate repo access
    repo_result = await client.validate_repo()
    if not repo_result.get("valid"):
        return {
            "valid": False,
            "stage": "repo",
            "error": repo_result.get("error", "Repo validation failed"),
        }

    return {
        "valid": True,
        "username": token_result.get("username", ""),
        "repo": repo_result.get("full_name", ""),
        "default_branch": repo_result.get("default_branch", "main"),
        "private": repo_result.get("private", False),
        "permissions": repo_result.get("permissions", {}),
        "is_mock": client.is_mock,
    }


# ─── Repo Analysis ────────────────────────────────────────

async def run_repo_pipeline(job_id: str) -> None:
    """Run the agent pipeline for a repo analysis job."""
    from app.agent.pipeline import execute_pipeline
    async with async_session() as db:
        try:
            await execute_pipeline(job_id, db)
        except Exception as e:
            logger.error("repo_pipeline.failed", job_id=job_id, error=str(e))
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if job:
                job.status = "failed"
                await db.commit()


@router.post("/repo/analyze", response_model=JobResponse)
async def analyze_repo(
    payload: RepoAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Analyze a GitHub repository: fetch file → run pipeline → return job."""
    # Parse repo URL
    try:
        owner, repo_name = parse_repo_url(payload.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(
        "repo.analyze_start",
        owner=owner,
        repo=repo_name,
        file_path=payload.file_path or "(auto-detect)",
    )

    client = GitHubClient(payload.token, owner, repo_name)

    # If file path is provided, fetch the file
    fetched_code = ""
    target_file = payload.file_path

    if target_file:
        file_result = await client.get_file_contents(target_file, payload.base_branch)
        if file_result.get("success"):
            fetched_code = file_result["content"]
        else:
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {target_file} — {file_result.get('error', '')}"
            )
    elif payload.logs:
        # Try to auto-detect file path from logs
        detected_path = _extract_file_path_from_logs(payload.logs)
        if detected_path:
            target_file = detected_path
            file_result = await client.get_file_contents(target_file, payload.base_branch)
            if file_result.get("success"):
                fetched_code = file_result["content"]
            else:
                logger.warning("repo.file_detect_failed", path=detected_path)

    # Detect language
    language = payload.language
    if language == "auto" and target_file:
        language = _detect_language_from_path(target_file)

    # Build analysis context
    log_content = _build_repo_analysis_context(
        code=fetched_code,
        logs=payload.logs,
        language=language,
        file_path=target_file,
        owner=owner,
        repo_name=repo_name,
    )

    # Create job
    job = Job(
        failure_title=f"Repo analysis: {owner}/{repo_name}" + (f" — {target_file}" if target_file else ""),
        failure_source="github",
        failure_type="auto",
        raw_logs=log_content,
        mode="standard",
        status="queued",
        repo_url=payload.repo_url,
        repo_owner=owner,
        repo_name=repo_name,
        base_branch=payload.base_branch,
        target_file_path=target_file or "",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    job_id = job.id
    logger.info("repo_job.created", job_id=job_id, owner=owner, repo=repo_name)

    background_tasks.add_task(run_repo_pipeline, job_id)

    return job


# ─── PR Creation ──────────────────────────────────────────

@router.post("/pr/create")
async def create_pr_for_job(
    payload: PRCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Full workflow: create branch → commit fix → open PR for a completed job."""
    # Fetch job
    result = await db.execute(select(Job).where(Job.id == payload.job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job must be completed before creating a PR")

    await db.refresh(job, ["patches", "summary"])

    if not job.patches:
        raise HTTPException(status_code=400, detail="No patches available for this job")

    patch = job.patches[0]
    summary = job.summary

    # Determine repo info — use job's stored info or parse from token
    owner = job.repo_owner
    repo_name = job.repo_name
    base_branch = payload.base_branch or job.base_branch or "main"

    if not owner or not repo_name:
        # Fall back: if no repo info on job, use mock mode
        owner = owner or "automerge"
        repo_name = repo_name or "demo-repo"

    client = GitHubClient(payload.token, owner, repo_name)

    # Generate branch name
    branch_name = f"automerge/fix-{job.id}"
    pr_title = summary.pr_title if summary else f"fix: {job.failure_title}"
    pr_body = summary.pr_body if summary else f"AutoMerge fix for: {job.failure_title}"
    file_path = patch.file_path or job.target_file_path or "fix.py"

    logger.info("github.pr_workflow_start", job_id=job.id, branch=branch_name)

    # Step 1: Create branch
    branch_result = await client.create_branch(branch_name, base_branch)
    if not branch_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Branch creation failed: {branch_result.get('error')}"
        )

    # Step 2: Commit the fix
    commit_message = (
        f"{pr_title}\n\n"
        f"Confidence: {job.confidence_score:.0%}\n"
        f"Root cause: {job.root_cause[:100] if job.root_cause else 'N/A'}"
    )
    commit_result = await client.commit_file(
        branch_name, file_path, patch.fixed_code, commit_message
    )
    if not commit_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Commit failed: {commit_result.get('error')}"
        )

    # Step 3: Create PR
    pr_result = await client.create_pr(branch_name, pr_title, pr_body, base_branch)
    if not pr_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"PR creation failed: {pr_result.get('error')}"
        )

    # Update job with GitHub info
    job.github_branch_name = branch_name
    job.github_commit_sha = commit_result.get("commit_sha", "")
    job.github_pr_url = pr_result.get("pr_url", "")
    job.github_pr_number = pr_result.get("pr_number")
    await db.commit()

    logger.info(
        "github.pr_workflow_complete",
        job_id=job.id,
        pr_number=pr_result.get("pr_number"),
    )

    return {
        "success": True,
        "branch": branch_result,
        "commit": commit_result,
        "pr": pr_result,
        "is_mock": client.is_mock,
    }


# ─── PR Merge ────────────────────────────────────────────

@router.post("/pr/merge")
async def merge_pr(
    payload: PRMergeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Merge a PR (requires explicit confirmation)."""
    result = await db.execute(select(Job).where(Job.id == payload.job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.github_pr_number:
        raise HTTPException(status_code=400, detail="No PR exists for this job — create one first")

    owner = job.repo_owner or "automerge"
    repo_name = job.repo_name or "demo-repo"

    client = GitHubClient(payload.token, owner, repo_name)

    merge_result = await client.merge_pr(job.github_pr_number, payload.merge_method)
    if not merge_result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=f"Merge failed: {merge_result.get('error')}"
        )

    logger.info("github.pr_merged", job_id=job.id, pr_number=job.github_pr_number)

    return {
        "success": True,
        "merged": merge_result.get("merged"),
        "sha": merge_result.get("sha"),
        "is_mock": client.is_mock,
    }


# ─── Legacy endpoints (backward compat) ──────────────────

@router.get("/status")
async def get_github_status():
    """Get GitHub integration status (legacy)."""
    from app.config import settings
    return {
        "connected": settings.has_github,
        "mode": "live" if settings.has_github else "mock",
        "owner": settings.GITHUB_OWNER or "(not configured)",
        "repo": settings.GITHUB_REPO or "(not configured)",
    }


@router.post("/connect")
async def connect_github():
    """Legacy connect endpoint — tokens now passed per-request."""
    return {
        "success": True,
        "message": "GitHub tokens are now passed per-request. Use the workspace form.",
        "mode": "per-request",
    }


@router.post("/disconnect")
async def disconnect_github():
    """Legacy disconnect endpoint."""
    return {"success": True, "mode": "mock"}


# ─── Helpers ──────────────────────────────────────────────

def _extract_file_path_from_logs(logs: str) -> str | None:
    """Try to find a file path mentioned in error logs."""
    # Common patterns: "File 'src/utils.py', line 15"
    patterns = [
        r'File\s+"([^"]+\.(?:py|ts|js|tsx|jsx|java|go|rs|cpp|c|rb))"',
        r'File\s+\'([^\']+\.(?:py|ts|js|tsx|jsx|java|go|rs|cpp|c|rb))\'',
        r'at\s+(?:\w+\s+)?\(?([^\s:()]+\.(?:py|ts|js|tsx|jsx|java|go|rs|cpp|c|rb))[\s:)]',
        r'([a-zA-Z_][\w/\\.-]+\.(?:py|ts|js|tsx|jsx|java|go|rs|cpp|c|rb))(?::\d+)',
        r'(?:in|at|from)\s+([a-zA-Z_][\w/\\.-]+\.(?:py|ts|js|tsx|jsx|java|go|rs|cpp|c|rb))',
    ]
    for pattern in patterns:
        match = re.search(pattern, logs)
        if match:
            path = match.group(1)
            # Clean up path
            path = path.lstrip("./")
            if "/" in path or "\\" in path:
                return path
            return path
    return None


def _detect_language_from_path(file_path: str) -> str:
    """Detect programming language from file extension."""
    ext_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
    }
    for ext, lang in ext_map.items():
        if file_path.endswith(ext):
            return lang
    return "python"


def _build_repo_analysis_context(
    code: str, logs: str, language: str, file_path: str,
    owner: str, repo_name: str
) -> str:
    """Build the analysis context string for the pipeline."""
    fname = file_path or "unknown"
    parts = [
        f"$ automerge analyze {owner}/{repo_name} — {fname}",
        f"Repository: {owner}/{repo_name}",
        f"File: {fname} ({language})",
        "",
    ]

    if code:
        parts.extend([
            "─── Source Code ───",
            code,
            "─── End Source ───",
            "",
        ])

    if logs:
        parts.extend([
            "─── Error Logs ───",
            logs,
            "─── End Logs ───",
            "",
        ])

    if not code and not logs:
        parts.append("No source code or logs provided — running shallow analysis.")

    parts.append(f"Analysis complete for {fname}")
    return "\n".join(parts)
