"""
Extension Routes — API endpoints for the AutoMerge Chrome Extension.

All endpoints are isolated. No existing routes are modified.

Endpoints:
  POST /api/extension/analyze       — Full analysis of browser code
  POST /api/extension/explain       — Lightweight explanation only
  GET  /api/extension/history       — Fetch analysis history
  GET  /api/extension/runs/{id}     — Get a specific report
  DELETE /api/extension/runs/{id}   — Delete a report
  GET  /api/extension/health        — Health check
"""

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services import extension_service

logger = structlog.get_logger("automerge.extension.routes")
router = APIRouter()


# ─── Request Schemas ─────────────────────────────────────

class ExtensionAnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100_000)
    language: str = Field(default="")
    filename: str = Field(default="")
    source_type: str = Field(default="selection")  # selection|codeblock|github|web_editor|repo_url
    page_url: str = Field(default="")
    repo_url: str = Field(default="")
    selected_text: str = Field(default="")
    session_id: str = Field(default="")
    extension_version: str = Field(default="1.0")


class ExtensionExplainRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100_000)
    language: str = Field(default="")
    filename: str = Field(default="")
    page_url: str = Field(default="")


# ─── Endpoints ───────────────────────────────────────────

@router.post("/analyze")
async def extension_analyze(req: ExtensionAnalyzeRequest):
    """
    Full analysis of code submitted from the Chrome extension.
    Runs through the Studio pipeline and returns popup-ready structured output.
    """
    result = await extension_service.analyze_browser_code(
        code=req.code,
        language=req.language,
        filename=req.filename,
        source_type=req.source_type,
        page_url=req.page_url,
        repo_url=req.repo_url,
        selected_text=req.selected_text,
        session_id=req.session_id,
        extension_version=req.extension_version,
    )
    if result.get("status") == "error":
        return {"status": "error", "error": result.get("error"), "data": None}
    return {"status": "ok", "data": result}


@router.post("/explain")
async def extension_explain(req: ExtensionExplainRequest):
    """
    Lightweight explanation endpoint — runs debug mode only for quick popup results.
    """
    result = await extension_service.analyze_browser_code(
        code=req.code,
        language=req.language,
        filename=req.filename,
        source_type="selection",
        page_url=req.page_url,
    )
    if result.get("status") == "error":
        return {"status": "error", "error": result.get("error"), "data": None}
    return {"status": "ok", "data": result}


@router.get("/history")
async def extension_history(limit: int = 50):
    """Get extension analysis history."""
    history = extension_service.get_history(limit=min(limit, 100))
    return {"status": "ok", "data": history, "count": len(history)}


@router.get("/runs/{analysis_id}")
async def extension_get_run(analysis_id: str):
    """Get a specific extension analysis report."""
    report = extension_service.get_report(analysis_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"status": "ok", "data": report}


@router.delete("/runs/{analysis_id}")
async def extension_delete_run(analysis_id: str):
    """Delete an extension analysis report."""
    deleted = extension_service.delete_report(analysis_id)
    return {"status": "ok", "data": {"deleted": deleted}}


@router.get("/health")
async def extension_health():
    return {
        "status": "ok",
        "module": "chrome-extension-api",
        "version": "1.0.0",
        "sources": ["selection", "codeblock", "github", "web_editor", "repo_url"],
        "pipeline": "studio-analyzer",
        "devmitra_integration": True,
    }
