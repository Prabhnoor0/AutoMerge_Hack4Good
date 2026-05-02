"""
AutoDeploy — Deployment Orchestrator Service

Ties together classification, env scanning, simulation, and deployment.
Manages deployment runs with persistent JSON storage.
"""

import hashlib
import json
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path

import structlog
import httpx

from app.services.deploy_classifier import classify_repository, ProjectClassification
from app.services.env_service import scan_env_vars
from app.services.deploy_simulator import simulate_deployment
from app.services.deploy_adapters import DeployResult
from app.services.deploy_adapters.vercel import VercelAdapter
from app.services.deploy_adapters.render import RenderAdapter
from app.services.deploy_adapters.huggingface import HuggingFaceAdapter
from app.services.deploy_adapters.supabase import SupabaseAdapter

logger = structlog.get_logger("autodeploy")

DATA_DIR = Path("./data/autodeploy")
RUNS_DIR = DATA_DIR / "runs"
MEMORY_FILE = DATA_DIR / "failure_memory.json"

ADAPTERS = {
    "vercel": VercelAdapter(),
    "render": RenderAdapter(),
    "huggingface": HuggingFaceAdapter(),
    "supabase": SupabaseAdapter(),
}

SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".next", "dist", "build", "venv", ".venv", "vendor"}
SKIP_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".webm", ".zip", ".tar", ".gz", ".lock"}


# ─── GitHub Helpers ───────────────────────────────────────

async def _fetch_repo_tree(owner: str, repo: str, token: str = "") -> list[dict]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1", headers=headers)
        if r.status_code == 200:
            return r.json().get("tree", [])
    return []


async def _fetch_file(owner: str, repo: str, path: str, token: str = "") -> str:
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"https://api.github.com/repos/{owner}/{repo}/contents/{path}", headers=headers)
        if r.status_code == 200:
            return r.text[:10000]
    return ""


def _parse_url(repo_url: str) -> tuple[str, str]:
    parts = repo_url.rstrip("/").split("/")
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "", ""


# ─── Persistence ──────────────────────────────────────────

def _ensure_dirs():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _save_run(run: dict):
    _ensure_dirs()
    (RUNS_DIR / f"{run['id']}.json").write_text(json.dumps(run, indent=2, default=str))


def _load_run(run_id: str) -> dict | None:
    p = RUNS_DIR / f"{run_id}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


def _list_runs() -> list[dict]:
    _ensure_dirs()
    runs = []
    for f in sorted(RUNS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            runs.append({
                "id": data["id"],
                "repo_url": data.get("repo_url", ""),
                "repo_name": data.get("repo_name", ""),
                "platform": data.get("platform", ""),
                "project_type": data.get("project_type", ""),
                "status": data.get("status", ""),
                "deploy_url": data.get("deploy_url", ""),
                "readiness_score": data.get("readiness_score", 0),
                "created_at": data.get("created_at", ""),
            })
        except Exception:
            pass
    return runs[:50]


# ─── Failure Memory ──────────────────────────────────────

def _load_failure_memory() -> list[dict]:
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text())
    return []


def _save_failure(failure: dict):
    _ensure_dirs()
    mem = _load_failure_memory()
    mem.insert(0, failure)
    mem = mem[:100]
    MEMORY_FILE.write_text(json.dumps(mem, indent=2, default=str))


def get_failure_warnings(classification: dict) -> list[str]:
    """Generate warnings based on past failure patterns."""
    warnings = []
    mem = _load_failure_memory()
    project_type = classification.get("project_type", "")

    categories = {}
    for f in mem:
        cat = f.get("failure_category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    if categories.get("auth", 0) > 0:
        warnings.append("⚠️ Past failures due to missing API tokens — ensure all platform tokens are set")
    if categories.get("build", 0) > 0:
        warnings.append("⚠️ Past build failures detected — verify build command and dependencies")
    if categories.get("env", 0) > 0:
        warnings.append("⚠️ Past failures from missing environment variables — double-check all required vars")
    if categories.get("port", 0) > 0 and project_type in ("backend", "fullstack"):
        warnings.append("⚠️ Past port binding failures — ensure PORT env var is used for server listen")

    return warnings


# ─── Core Pipeline ────────────────────────────────────────

async def analyze_for_deploy(repo_url: str, token: str = "") -> dict:
    """Phase 1+2: Classify repo and scan env vars."""
    owner, repo = _parse_url(repo_url)
    if not owner or not repo:
        raise ValueError("Invalid GitHub URL")

    logger.info("autodeploy.analyzing", repo=f"{owner}/{repo}")

    tree = await _fetch_repo_tree(owner, repo, token)
    if not tree:
        raise ValueError("Could not fetch repository. Check URL and access permissions.")

    # Filter relevant files
    relevant = []
    for f in tree:
        if f.get("type") != "blob":
            continue
        parts = f["path"].split("/")
        if any(p in SKIP_DIRS for p in parts):
            continue
        ext = os.path.splitext(f["path"])[1].lower()
        if ext in SKIP_EXTS:
            continue
        relevant.append(f)

    # Fetch key files
    priority_names = {
        "package.json", "requirements.txt", "pyproject.toml", "tsconfig.json",
        "README.md", "main.py", "app.py", "index.ts", "index.js", "server.py",
        "next.config.js", "next.config.mjs", "vite.config.ts", "Dockerfile",
        "docker-compose.yml", ".env.example", ".env.sample", "manage.py",
        "config.py", "settings.py",
    }
    fetch_paths = [f["path"] for f in relevant if f["path"].split("/")[-1] in priority_names][:20]

    file_contents = {}
    tasks = [_fetch_file(owner, repo, p, token) for p in fetch_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for path, content in zip(fetch_paths, results):
        if isinstance(content, str) and content:
            file_contents[path] = content
            file_contents[path.split("/")[-1]] = content  # Also key by filename

    # Classify
    classification = classify_repository(relevant, file_contents)

    # Env scan
    env_scan = scan_env_vars(file_contents)

    # Failure warnings
    failure_warnings = get_failure_warnings(classification.to_dict())

    return {
        "repo_url": repo_url,
        "owner": owner,
        "repo_name": repo,
        "classification": classification.to_dict(),
        "env_scan": env_scan.to_dict(),
        "failure_warnings": failure_warnings,
    }


async def preview_deploy(repo_url: str, platform_id: str = "", token: str = "") -> dict:
    """Phase 3: Run simulation / dry run."""
    analysis = await analyze_for_deploy(repo_url, token)
    classification = analysis["classification"]
    env_scan = analysis["env_scan"]

    # Get file contents for simulation
    owner, repo = _parse_url(repo_url)
    tree = await _fetch_repo_tree(owner, repo, token)
    priority_names = {"package.json", "requirements.txt", "Dockerfile", "main.py", "app.py"}
    fetch_paths = [f["path"] for f in tree if f.get("type") == "blob" and f["path"].split("/")[-1] in priority_names][:10]
    file_contents = {}
    tasks = [_fetch_file(owner, repo, p, token) for p in fetch_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for path, content in zip(fetch_paths, results):
        if isinstance(content, str) and content:
            file_contents[path.split("/")[-1]] = content

    sim = simulate_deployment(classification, env_scan, file_contents, platform_id)

    return {
        **analysis,
        "simulation": sim.to_dict(),
        "platform_id": platform_id or (classification.get("recommended_platforms", [{}])[0].get("id", "") if classification.get("recommended_platforms") else ""),
    }


async def start_deploy(repo_url: str, platform_id: str, token: str = "",
                       platform_token: str = "", env_vars: dict | None = None) -> dict:
    """Phase 5: Execute actual deployment."""
    run_id = hashlib.md5(f"{repo_url}:{platform_id}:{datetime.now().isoformat()}".encode()).hexdigest()[:12]

    # Get analysis
    analysis = await analyze_for_deploy(repo_url, token)
    classification = analysis["classification"]

    adapter = ADAPTERS.get(platform_id)
    if not adapter:
        run = {
            "id": run_id, "repo_url": repo_url, "repo_name": analysis.get("repo_name", ""),
            "platform": platform_id, "project_type": classification.get("project_type", ""),
            "status": "failed", "error": f"Unknown platform: {platform_id}",
            "failure_category": "config", "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_run(run)
        return run

    # Validate
    validation = await adapter.validate(repo_url, platform_token, env_vars)
    if not validation.get("valid"):
        run = {
            "id": run_id, "repo_url": repo_url, "repo_name": analysis.get("repo_name", ""),
            "platform": platform_id, "project_type": classification.get("project_type", ""),
            "status": "failed", "error": validation.get("error", "Validation failed"),
            "failure_category": "auth", "logs": [], "readiness_score": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_failure({"category": "auth", "platform": platform_id, "ts": run["created_at"]})
        _save_run(run)
        return run

    # Deploy
    result = await adapter.deploy(repo_url, platform_token, env_vars)

    run = {
        "id": run_id,
        "repo_url": repo_url,
        "repo_name": analysis.get("repo_name", ""),
        "owner": analysis.get("owner", ""),
        "platform": platform_id,
        "platform_name": adapter.platform_name,
        "project_type": classification.get("project_type", ""),
        "frontend_type": classification.get("frontend_type"),
        "backend_type": classification.get("backend_type"),
        "status": "deployed" if result.success else "failed",
        "deploy_url": result.deploy_url,
        "logs": result.logs,
        "error": result.error,
        "failure_category": result.failure_category,
        "readiness_score": 0,
        "env_summary": {"count": len(env_vars) if env_vars else 0, "keys": list((env_vars or {}).keys())},
        "classification": classification,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if not result.success:
        _save_failure({"category": result.failure_category, "platform": platform_id,
                       "error": result.error, "ts": run["created_at"]})

    _save_run(run)
    logger.info("autodeploy.completed", run_id=run_id, status=run["status"])
    return run


async def enable_auto_deploy(run_id: str, platform_token: str = "") -> dict:
    """Enable auto-deploy for a deployment run."""
    run = _load_run(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    adapter = ADAPTERS.get(run.get("platform", ""))
    if not adapter:
        return {"enabled": False, "error": "Unknown platform"}

    result = await adapter.enable_auto_deploy(run["repo_url"], platform_token)
    run["auto_deploy"] = result
    _save_run(run)
    return result


async def retry_deploy(run_id: str, platform_token: str = "", env_vars: dict | None = None) -> dict:
    """Retry a failed deployment."""
    run = _load_run(run_id)
    if not run:
        raise ValueError(f"Run {run_id} not found")

    return await start_deploy(
        run["repo_url"], run["platform"], platform_token=platform_token, env_vars=env_vars
    )


def get_run(run_id: str) -> dict | None:
    return _load_run(run_id)


def get_runs() -> list[dict]:
    return _list_runs()
