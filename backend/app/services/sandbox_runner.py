"""
Sandbox Runner — Container-based code execution engine.

Executes untrusted user code inside isolated Docker containers with:
- CPU / memory limits
- Network isolation
- Timeout enforcement
- Automatic cleanup
- Structured result capture

SAFETY: Never executes user code on the host. If Docker is unavailable,
returns a safe failure result instead of falling back to host execution.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
import hashlib
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger("sandbox.runner")

# ─── Language Configs ─────────────────────────────────────

LANGUAGE_CONFIGS = {
    "python": {
        "image": "python:3.12-slim",
        "file_ext": ".py",
        "run_cmd": ["python", "/workspace/main.py"],
        "test_cmd": ["python", "-m", "pytest", "/workspace/", "-v", "--tb=short", "--no-header"],
    },
    "javascript": {
        "image": "node:20-slim",
        "file_ext": ".js",
        "run_cmd": ["node", "/workspace/main.js"],
        "test_cmd": ["node", "/workspace/main.js"],
    },
    "typescript": {
        "image": "node:20-slim",
        "file_ext": ".ts",
        "run_cmd": ["npx", "--yes", "tsx", "/workspace/main.ts"],
        "test_cmd": ["npx", "--yes", "tsx", "/workspace/main.ts"],
    },
}


# ─── Result Dataclass ─────────────────────────────────────

@dataclass
class SandboxResult:
    run_id: str = ""
    status: str = "pending"          # pending | running | success | failure | error | timeout
    success: bool = False
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    duration_ms: int = 0
    timed_out: bool = False
    language: str = ""
    mode: str = "run"                # run | test | validate
    error_summary: str = ""
    test_summary: dict = field(default_factory=dict)
    resource_summary: dict = field(default_factory=dict)
    cleanup_ok: bool = False
    created_at: str = ""
    container_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ─── ID Generator ─────────────────────────────────────────

def _gen_run_id() -> str:
    seed = f"{time.time()}{random.random()}"
    return f"run_{hashlib.md5(seed.encode()).hexdigest()[:12]}"


# ─── Docker Availability Check ────────────────────────────

def _docker_available() -> bool:
    """Check if Docker CLI is present and the daemon is running."""
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, timeout=5, text=True,
        )
        return r.returncode == 0
    except Exception:
        return False


# ─── Core Runner ──────────────────────────────────────────

def execute_in_container(
    code: str,
    language: str = "python",
    test_code: str = "",
    filename: str = "",
    mode: str = "run",
    timeout_seconds: int = 30,
    memory_limit: str = "128m",
    cpu_limit: str = "0.5",
    network_disabled: bool = True,
) -> SandboxResult:
    """
    Execute user code inside an isolated Docker container.

    Returns a structured SandboxResult. Never raises on user-code errors —
    those are captured in stdout/stderr. Only raises on catastrophic infra
    failures, and even those are caught and returned as error results.
    """
    run_id = _gen_run_id()
    result = SandboxResult(
        run_id=run_id,
        language=language,
        mode=mode,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    lang_cfg = LANGUAGE_CONFIGS.get(language)
    if not lang_cfg:
        result.status = "error"
        result.error_summary = f"Unsupported language: {language}"
        return result

    # ── Safety gate: refuse to run on host if Docker is missing ──
    if not _docker_available():
        result.status = "error"
        result.error_summary = (
            "Docker is not available. Sandbox execution requires Docker. "
            "User code will NOT be executed on the host for safety."
        )
        logger.warning("sandbox.docker_unavailable", run_id=run_id)
        return result

    # ── Prepare temp workspace ──
    workspace = None
    container_name = f"sandbox_{run_id}"

    try:
        workspace = Path(tempfile.mkdtemp(prefix="sandbox_"))
        main_file = filename or f"main{lang_cfg['file_ext']}"
        (workspace / main_file).write_text(code, encoding="utf-8")

        if test_code:
            test_file = f"test_main{lang_cfg['file_ext']}"
            (workspace / test_file).write_text(test_code, encoding="utf-8")

        # ── Choose command ──
        if mode == "test" and test_code:
            cmd = lang_cfg["test_cmd"]
        else:
            cmd = lang_cfg["run_cmd"]

        # If custom filename, adjust command
        if filename and filename != f"main{lang_cfg['file_ext']}":
            cmd = list(cmd)
            cmd[-1] = f"/workspace/{filename}"

        # ── Build Docker command ──
        docker_cmd = [
            "docker", "run",
            "--rm",
            "--name", container_name,
            "--memory", memory_limit,
            "--cpus", cpu_limit,
            "--pids-limit", "64",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
            "--security-opt", "no-new-privileges",
            "-v", f"{workspace.resolve()}:/workspace:ro",
            "-w", "/workspace",
        ]

        if network_disabled:
            docker_cmd.extend(["--network", "none"])

        docker_cmd.append(lang_cfg["image"])
        docker_cmd.extend(cmd)

        # ── Execute ──
        result.status = "running"
        start_time = time.monotonic()

        try:
            proc = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 5,  # buffer for container startup
            )
            elapsed = time.monotonic() - start_time

            result.stdout = proc.stdout[:50_000]   # cap output
            result.stderr = proc.stderr[:50_000]
            result.exit_code = proc.returncode
            result.duration_ms = int(elapsed * 1000)
            result.success = proc.returncode == 0
            result.status = "success" if result.success else "failure"

            # Parse test results if test mode
            if mode == "test":
                result.test_summary = _parse_test_output(result.stdout, result.stderr, language)

        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start_time
            result.timed_out = True
            result.status = "timeout"
            result.duration_ms = int(elapsed * 1000)
            result.error_summary = f"Execution timed out after {timeout_seconds}s"
            # Force-kill container
            subprocess.run(["docker", "kill", container_name], capture_output=True, timeout=5)
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=5)

        result.container_id = container_name
        result.resource_summary = {
            "memory_limit": memory_limit,
            "cpu_limit": cpu_limit,
            "timeout_seconds": timeout_seconds,
            "network_disabled": network_disabled,
        }

    except Exception as e:
        result.status = "error"
        result.error_summary = f"Sandbox infrastructure error: {str(e)}"
        logger.error("sandbox.execution_error", run_id=run_id, error=str(e))

    finally:
        # ── Cleanup workspace ──
        if workspace and workspace.exists():
            try:
                shutil.rmtree(workspace)
                result.cleanup_ok = True
            except Exception as e:
                logger.warning("sandbox.cleanup_failed", run_id=run_id, error=str(e))
                result.cleanup_ok = False

    logger.info(
        "sandbox.run_complete",
        run_id=run_id,
        status=result.status,
        duration_ms=result.duration_ms,
        exit_code=result.exit_code,
    )
    return result


# ─── Test Output Parser ───────────────────────────────────

def _parse_test_output(stdout: str, stderr: str, language: str) -> dict:
    """Parse test runner output into a structured summary."""
    summary = {"passed": 0, "failed": 0, "errors": 0, "total": 0, "details": []}
    combined = stdout + "\n" + stderr

    if language == "python":
        # Parse pytest-style output
        for line in combined.splitlines():
            lower = line.strip().lower()
            if lower.startswith("passed") or "passed" in lower:
                try:
                    parts = lower.split()
                    for i, p in enumerate(parts):
                        if p == "passed" and i > 0:
                            summary["passed"] = int(parts[i - 1])
                except (ValueError, IndexError):
                    pass
            if lower.startswith("failed") or "failed" in lower:
                try:
                    parts = lower.split()
                    for i, p in enumerate(parts):
                        if p == "failed" and i > 0:
                            summary["failed"] = int(parts[i - 1])
                except (ValueError, IndexError):
                    pass
            if "PASSED" in line:
                summary["details"].append({"test": line.strip(), "status": "passed"})
            elif "FAILED" in line:
                summary["details"].append({"test": line.strip(), "status": "failed"})
            elif "ERROR" in line:
                summary["details"].append({"test": line.strip(), "status": "error"})
                summary["errors"] += 1

    summary["total"] = summary["passed"] + summary["failed"] + summary["errors"]

    # If summary counts weren't parsed from text but details were collected, derive from details
    if summary["total"] == 0 and summary["details"]:
        summary["passed"] = sum(1 for d in summary["details"] if d["status"] == "passed")
        summary["failed"] = sum(1 for d in summary["details"] if d["status"] == "failed")
        summary["errors"] = sum(1 for d in summary["details"] if d["status"] == "error")
        summary["total"] = len(summary["details"])

    return summary
