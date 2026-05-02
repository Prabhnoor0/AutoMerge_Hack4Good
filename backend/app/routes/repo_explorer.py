"""
Devमित्र Repo Explorer — API Routes

New route group for repo ingestion, analysis, Q&A, and history.
Completely separate from existing Devमित्र chat routes.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.repo_explorer_service import (
    analyze_repository,
    ask_repo_question,
    get_history,
    get_report,
    delete_history_item,
)

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────

class AnalyzeRepoRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    token: str = Field(default="", description="Optional GitHub token")

class AskQuestionRequest(BaseModel):
    report_id: str = Field(..., description="Report ID from analysis")
    question: str = Field(..., description="Question about the repo")


# ─── Routes ───────────────────────────────────────────────

@router.post("/analyze")
async def analyze_repo(payload: AnalyzeRepoRequest):
    """Ingest and analyze a GitHub repository."""
    try:
        result = await analyze_repository(payload.repo_url, payload.token)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/ask")
async def ask_question(payload: AskQuestionRequest):
    """Ask a question about a previously analyzed repo."""
    result = await ask_repo_question(payload.report_id, payload.question)
    return {"status": "success", "data": result}


@router.get("/history")
async def list_history():
    """Get all past repo analysis sessions."""
    return {"status": "success", "data": get_history()}


@router.get("/report/{report_id}")
async def fetch_report(report_id: str):
    """Get a specific repo report by ID."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "success", "data": report}


@router.delete("/history/{report_id}")
async def remove_history(report_id: str):
    """Delete a history item and its report."""
    delete_history_item(report_id)
    return {"status": "success", "message": "Deleted"}


@router.get("/health")
async def explorer_health():
    """Health check for Repo Explorer module."""
    return {"status": "ok", "module": "repo_explorer", "version": "1.0.0"}
