"""
Sandbox Service — High-level orchestration layer for sandbox execution.

Coordinates between the API layer and the container runner.
Handles persistence, history, and structured responses.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

from app.services.sandbox_runner import execute_in_container, SandboxResult

logger = structlog.get_logger("sandbox.service")

# ─── Persistence ──────────────────────────────────────────

DATA_DIR = Path("./data/sandbox")
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "history.json"


def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []


def _save_history(history: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str))


def _save_run(result: SandboxResult):
    """Persist a single run to the run file and append to history."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    run_file = DATA_DIR / f"{result.run_id}.json"
    run_file.write_text(json.dumps(result.to_dict(), indent=2, default=str))

    # Append summary to history
    history = _load_history()
    history.insert(0, {
        "run_id": result.run_id,
        "language": result.language,
        "mode": result.mode,
        "status": result.status,
        "success": result.success,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "timed_out": result.timed_out,
        "created_at": result.created_at,
        "error_summary": result.error_summary[:200] if result.error_summary else "",
    })
    # Keep last 200 entries
    _save_history(history[:200])


# ─── Public API ───────────────────────────────────────────

def run_code(
    code: str,
    language: str = "python",
    test_code: str = "",
    filename: str = "",
    mode: str = "run",
    timeout: int = 30,
    memory_limit: str = "128m",
    cpu_limit: str = "0.5",
    network_disabled: bool = True,
    source_feature: str = "",
) -> dict:
    """
    Execute user code in a sandboxed container and return the result.

    Args:
        code: The source code to execute
        language: Programming language (python, javascript, typescript)
        test_code: Optional test code to run against the user code
        filename: Optional custom filename
        mode: Execution mode — run | test | validate
        timeout: Timeout in seconds (max 120)
        memory_limit: Docker memory limit (e.g. "128m", "256m")
        cpu_limit: Docker CPU limit (e.g. "0.5", "1.0")
        network_disabled: Whether to disable network access
        source_feature: Which feature triggered this run (battle, studio, etc.)

    Returns:
        Structured result dict with stdout, stderr, exit_code, etc.
    """
    # ── Validate inputs ──
    if not code or not code.strip():
        return SandboxResult(
            status="error",
            error_summary="No code provided",
            created_at=datetime.now(timezone.utc).isoformat(),
        ).to_dict()

    # Enforce safe limits
    timeout = min(max(timeout, 5), 120)
    allowed_memory = ["64m", "128m", "256m", "512m"]
    if memory_limit not in allowed_memory:
        memory_limit = "128m"

    allowed_cpu = ["0.25", "0.5", "1.0"]
    if cpu_limit not in allowed_cpu:
        cpu_limit = "0.5"

    if language not in ("python", "javascript", "typescript"):
        return SandboxResult(
            status="error",
            error_summary=f"Unsupported language: {language}",
            created_at=datetime.now(timezone.utc).isoformat(),
        ).to_dict()

    logger.info(
        "sandbox.run_requested",
        language=language,
        mode=mode,
        timeout=timeout,
        source=source_feature,
    )

    # ── Execute ──
    result = execute_in_container(
        code=code,
        language=language,
        test_code=test_code,
        filename=filename,
        mode=mode,
        timeout_seconds=timeout,
        memory_limit=memory_limit,
        cpu_limit=cpu_limit,
        network_disabled=network_disabled,
    )

    # ── Persist ──
    try:
        _save_run(result)
    except Exception as e:
        logger.warning("sandbox.persist_failed", run_id=result.run_id, error=str(e))

    return result.to_dict()


def get_run(run_id: str) -> dict | None:
    """Retrieve a specific run by ID."""
    run_file = DATA_DIR / f"{run_id}.json"
    if run_file.exists():
        try:
            return json.loads(run_file.read_text())
        except Exception:
            return None
    return None


def get_runs(limit: int = 50) -> list[dict]:
    """Get recent sandbox run history."""
    history = _load_history()
    return history[:limit]


def delete_run(run_id: str) -> bool:
    """Delete a specific run from history."""
    run_file = DATA_DIR / f"{run_id}.json"
    deleted = False
    if run_file.exists():
        run_file.unlink()
        deleted = True

    history = _load_history()
    history = [h for h in history if h.get("run_id") != run_id]
    _save_history(history)

    return deleted
