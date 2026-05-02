"""
AutoDeploy — API Routes

All deployment endpoints under /api/deploy/*.
Fully isolated from existing routes.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services import deploy_service

router = APIRouter()


# ─── Request Models ───────────────────────────────────────

class AnalyzeRequest(BaseModel):
    repo_url: str
    token: str = ""

class PreviewRequest(BaseModel):
    repo_url: str
    platform_id: str = ""
    token: str = ""

class DeployRequest(BaseModel):
    repo_url: str
    platform_id: str
    token: str = ""
    platform_token: str = ""
    env_vars: dict | None = None

class AutoDeployRequest(BaseModel):
    platform_token: str = ""

class RetryRequest(BaseModel):
    platform_token: str = ""
    env_vars: dict | None = None


# ─── Endpoints ────────────────────────────────────────────

@router.post("/analyze")
async def analyze_repo(req: AnalyzeRequest):
    """Classify repository and detect deployment targets."""
    try:
        result = await deploy_service.analyze_for_deploy(req.repo_url, req.token)
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/env-scan")
async def env_scan(req: AnalyzeRequest):
    """Scan repository for environment variable usage."""
    try:
        result = await deploy_service.analyze_for_deploy(req.repo_url, req.token)
        return {"status": "ok", "data": result.get("env_scan", {})}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preview")
async def preview(req: PreviewRequest):
    """Run deployment simulation / dry run."""
    try:
        result = await deploy_service.preview_deploy(req.repo_url, req.platform_id, req.token)
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.post("/start")
async def start_deploy(req: DeployRequest):
    """Execute actual deployment to chosen platform."""
    try:
        result = await deploy_service.start_deploy(
            req.repo_url, req.platform_id, req.token, req.platform_token, req.env_vars
        )
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deploy failed: {str(e)}")


@router.get("/runs")
async def list_runs():
    """List all deployment runs."""
    return {"status": "ok", "data": deploy_service.get_runs()}


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get a specific deployment run."""
    run = deploy_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"status": "ok", "data": run}


@router.post("/runs/{run_id}/retry")
async def retry_run(run_id: str, req: RetryRequest):
    """Retry a failed deployment."""
    try:
        result = await deploy_service.retry_deploy(run_id, req.platform_token, req.env_vars)
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/runs/{run_id}/auto-deploy")
async def enable_auto(run_id: str, req: AutoDeployRequest):
    """Enable auto-deploy on push for a run."""
    try:
        result = await deploy_service.enable_auto_deploy(run_id, req.platform_token)
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/platforms")
async def list_platforms():
    """List all supported deployment platforms."""
    from app.services.deploy_classifier import PLATFORMS
    return {"status": "ok", "data": PLATFORMS}
