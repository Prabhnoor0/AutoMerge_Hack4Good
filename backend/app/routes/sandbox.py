"""
Sandbox Routes — API endpoints for container-based code execution.

Endpoints:
  POST /api/sandbox/run     — Execute code in sandbox
  POST /api/sandbox/test    — Run tests in sandbox
  GET  /api/sandbox/runs    — List run history
  GET  /api/sandbox/runs/{id} — Get specific run
  DELETE /api/sandbox/runs/{id} — Delete a run
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services import sandbox_service

router = APIRouter()


# ─── Request / Response Schemas ───────────────────────────

class SandboxRunRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100_000)
    language: str = Field(default="python")
    test_code: str = Field(default="")
    filename: str = Field(default="")
    mode: str = Field(default="run")          # run | test | validate
    timeout: int = Field(default=30, ge=5, le=120)
    memory_limit: str = Field(default="128m")
    cpu_limit: str = Field(default="0.5")
    network_disabled: bool = Field(default=True)
    source_feature: str = Field(default="")   # battle | studio | manual


# ─── Endpoints ────────────────────────────────────────────

@router.post("/run")
async def sandbox_run(req: SandboxRunRequest):
    """Execute user code in an isolated container."""
    result = sandbox_service.run_code(
        code=req.code,
        language=req.language,
        test_code=req.test_code,
        filename=req.filename,
        mode=req.mode,
        timeout=req.timeout,
        memory_limit=req.memory_limit,
        cpu_limit=req.cpu_limit,
        network_disabled=req.network_disabled,
        source_feature=req.source_feature,
    )
    return {"data": result}


@router.post("/test")
async def sandbox_test(req: SandboxRunRequest):
    """Run tests against user code in an isolated container."""
    result = sandbox_service.run_code(
        code=req.code,
        language=req.language,
        test_code=req.test_code,
        filename=req.filename,
        mode="test",
        timeout=req.timeout,
        memory_limit=req.memory_limit,
        cpu_limit=req.cpu_limit,
        network_disabled=req.network_disabled,
        source_feature=req.source_feature,
    )
    return {"data": result}


@router.get("/runs")
async def list_runs(limit: int = 50):
    """Get sandbox run history."""
    runs = sandbox_service.get_runs(limit=min(limit, 100))
    return {"data": runs, "count": len(runs)}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific sandbox run."""
    run = sandbox_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"data": run}


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    """Delete a sandbox run."""
    deleted = sandbox_service.delete_run(run_id)
    return {"data": {"deleted": deleted}}
