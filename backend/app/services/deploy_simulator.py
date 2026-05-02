"""
AutoDeploy — Deployment Simulation / Dry Run Service

Simulates build and startup checks without actually deploying.
Returns a readiness score with detailed issue breakdown.
"""

from dataclasses import dataclass, field, asdict


@dataclass
class SimulationResult:
    readiness_score: int = 0
    status: str = "unknown"  # ready, warning, not_ready
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)
    predicted_failure_probability: float = 0.0
    missing_packages: list[str] = field(default_factory=list)
    missing_env: list[str] = field(default_factory=list)
    port_risk: bool = False
    build_risk: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def simulate_deployment(
    classification: dict,
    env_scan: dict,
    file_contents: dict[str, str],
    platform_id: str = "",
) -> SimulationResult:
    """
    Run a dry-run deployment simulation based on project classification.

    Args:
        classification: Output from deploy_classifier
        env_scan: Output from env_service
        file_contents: Key file contents
        platform_id: Target platform ID

    Returns:
        SimulationResult with readiness score and detailed checks
    """
    result = SimulationResult()
    score = 100

    project_type = classification.get("project_type", "unknown")
    frontend_type = classification.get("frontend_type")
    backend_type = classification.get("backend_type")
    ml_type = classification.get("ml_type")
    build_cmd = classification.get("build_command")
    start_cmd = classification.get("start_command")
    entry_points = classification.get("entry_points", [])
    missing_vars = env_scan.get("missing_vars", [])

    # ─── Check 1: Entry point ─────────────────────────
    if entry_points:
        result.checks.append({"name": "Entry Point", "status": "pass", "detail": f"Found: {entry_points[0]}"})
    else:
        result.checks.append({"name": "Entry Point", "status": "fail", "detail": "No entry point detected"})
        result.issues.append("No entry point file found (main.py, app.py, index.ts, etc.)")
        score -= 25

    # ─── Check 2: Build command ───────────────────────
    if project_type in ("frontend", "fullstack", "static"):
        if build_cmd:
            result.checks.append({"name": "Build Command", "status": "pass", "detail": build_cmd})
        else:
            result.checks.append({"name": "Build Command", "status": "warn", "detail": "No build command detected"})
            result.warnings.append("No build script found in package.json")
            result.build_risk = True
            score -= 10

    # ─── Check 3: Start command ───────────────────────
    if project_type in ("backend", "fullstack", "ml"):
        if start_cmd:
            result.checks.append({"name": "Start Command", "status": "pass", "detail": start_cmd})
        else:
            result.checks.append({"name": "Start Command", "status": "warn", "detail": "No start command"})
            result.warnings.append("No start script detected — platform may not know how to run your app")
            score -= 15

    # ─── Check 4: Dependencies ────────────────────────
    has_pkg = "package.json" in file_contents
    has_req = "requirements.txt" in file_contents
    has_pyproj = "pyproject.toml" in file_contents
    if has_pkg or has_req or has_pyproj:
        dep_file = "package.json" if has_pkg else ("requirements.txt" if has_req else "pyproject.toml")
        result.checks.append({"name": "Dependencies", "status": "pass", "detail": f"Found {dep_file}"})
    else:
        result.checks.append({"name": "Dependencies", "status": "fail", "detail": "No dependency manifest"})
        result.issues.append("No package.json or requirements.txt found — deployment will fail")
        score -= 30

    # ─── Check 5: Environment variables ───────────────
    if missing_vars:
        result.missing_env = missing_vars
        result.checks.append({"name": "Environment Variables", "status": "warn",
                              "detail": f"{len(missing_vars)} potentially missing: {', '.join(missing_vars[:3])}"})
        result.warnings.append(f"Missing env vars may cause runtime errors: {', '.join(missing_vars[:5])}")
        score -= min(20, len(missing_vars) * 5)
    else:
        result.checks.append({"name": "Environment Variables", "status": "pass", "detail": "All detected vars accounted for"})

    # ─── Check 6: Port configuration ─────────────────
    if project_type in ("backend", "fullstack"):
        port_detected = False
        for content in file_contents.values():
            if "PORT" in content or "port" in content.lower():
                port_detected = True
                break
        if port_detected:
            result.checks.append({"name": "Port Config", "status": "pass", "detail": "PORT usage detected"})
        else:
            result.checks.append({"name": "Port Config", "status": "warn", "detail": "No PORT config found"})
            result.warnings.append("No PORT environment variable usage — some platforms require dynamic port binding")
            result.port_risk = True
            score -= 5

    # ─── Check 7: Framework match ─────────────────────
    if frontend_type:
        result.checks.append({"name": "Frontend Framework", "status": "pass", "detail": frontend_type})
    if backend_type:
        result.checks.append({"name": "Backend Framework", "status": "pass", "detail": backend_type})
    if ml_type:
        result.checks.append({"name": "ML Framework", "status": "pass", "detail": ml_type})

    # ─── Check 8: Platform compatibility ──────────────
    if platform_id:
        compat = _check_platform_compat(platform_id, classification)
        result.checks.append(compat)
        if compat["status"] == "fail":
            score -= 20
            result.issues.append(compat["detail"])

    # ─── Check 9: Dockerfile ──────────────────────────
    if "Dockerfile" in file_contents:
        result.checks.append({"name": "Dockerfile", "status": "pass", "detail": "Custom Dockerfile available"})
        score = min(100, score + 5)
    elif project_type == "backend":
        result.checks.append({"name": "Dockerfile", "status": "info", "detail": "No Dockerfile — platform will use buildpacks"})

    # ─── Check 10: README ─────────────────────────────
    has_readme = any(k.lower() in ("readme.md", "readme.txt", "readme") for k in file_contents)
    if has_readme:
        result.checks.append({"name": "Documentation", "status": "pass", "detail": "README found"})
    else:
        result.checks.append({"name": "Documentation", "status": "info", "detail": "No README — not required but recommended"})

    # ─── Final scoring ────────────────────────────────
    result.readiness_score = max(0, min(100, score))
    result.predicted_failure_probability = max(0.0, min(1.0, (100 - score) / 100.0))

    if result.readiness_score >= 80:
        result.status = "ready"
    elif result.readiness_score >= 50:
        result.status = "warning"
    else:
        result.status = "not_ready"

    return result


def _check_platform_compat(platform_id: str, classification: dict) -> dict:
    """Check if chosen platform supports the detected project type."""
    project_type = classification.get("project_type", "")
    backend_type = classification.get("backend_type", "")
    frontend_type = classification.get("frontend_type", "")

    compat_map = {
        "vercel": {"types": ["frontend", "fullstack", "static"], "note": "Best for Next.js and React"},
        "netlify": {"types": ["frontend", "static"], "note": "Best for static sites and SPAs"},
        "render": {"types": ["backend", "fullstack"], "note": "Supports Python, Node.js, Docker"},
        "koyeb": {"types": ["backend"], "note": "Supports Python and Node.js containers"},
        "huggingface": {"types": ["ml"], "note": "Best for Gradio/Streamlit ML demos"},
        "cloudflare_pages": {"types": ["frontend", "static"], "note": "Edge-deployed static sites"},
        "github_pages": {"types": ["static"], "note": "Static HTML/Jekyll only"},
        "supabase": {"types": ["database"], "note": "PostgreSQL database hosting"},
    }

    info = compat_map.get(platform_id, {"types": [], "note": "Unknown platform"})
    if project_type in info["types"]:
        return {"name": "Platform Compatibility", "status": "pass", "detail": f"{platform_id}: {info['note']}"}
    else:
        return {"name": "Platform Compatibility", "status": "fail",
                "detail": f"{platform_id} may not support {project_type} projects — {info['note']}"}
