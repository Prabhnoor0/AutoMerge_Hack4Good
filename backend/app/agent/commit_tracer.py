"""
Commit Tracer Module

Traces likely bug-introducing commits by correlating failure evidence
with git commit history. Uses file-path matching, stack trace analysis,
and diff-based heuristics.

Falls back gracefully if no commit data is available.
"""

import re
from typing import Any
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger("automerge.commit_tracer")


async def trace_causal_commit(state: dict[str, Any]) -> dict[str, Any]:
    """Attempt to trace the bug-introducing commit.

    Enriches state['triage'] with:
        - commit_trace: dict with suspect_commit, suspect_file, trace_method,
          trace_confidence, trace_reasoning, timeline
    """
    triage = state.get("triage", {})
    raw_logs = state.get("raw_logs", "")
    file_refs = state.get("file_references", [])
    error_message = state.get("error_message", "")
    stack_trace = state.get("stack_trace", [])
    affected_file = state.get("affected_file", "")

    # GitHub metadata from job
    commit_sha = state.get("github_commit_sha", "")
    branch_name = state.get("github_branch_name", "")
    repo_owner = state.get("repo_owner", "")
    repo_name = state.get("repo_name", "")

    # ── Extract commit references from logs ──
    commit_refs = _extract_commit_refs(raw_logs)
    file_change_refs = _extract_file_changes(raw_logs)

    # ── Build trace ──
    trace = {
        "suspect_commit": None,
        "suspect_file": None,
        "trace_method": "none",
        "trace_confidence": 0.0,
        "trace_reasoning": "",
        "timeline": [],
        "available": False,
    }

    # Strategy 1: Direct commit reference in logs
    if commit_refs:
        best_commit = commit_refs[0]
        trace.update({
            "suspect_commit": best_commit["sha"],
            "suspect_file": affected_file or (file_refs[0] if file_refs else None),
            "trace_method": "log_reference",
            "trace_confidence": 0.7,
            "trace_reasoning": f"Commit {best_commit['sha'][:8]} referenced in failure logs"
                + (f" ({best_commit.get('message', '')})" if best_commit.get("message") else ""),
            "available": True,
        })

    # Strategy 2: GitHub commit SHA available on the job
    elif commit_sha:
        trace.update({
            "suspect_commit": commit_sha,
            "suspect_file": affected_file or (file_refs[0] if file_refs else None),
            "trace_method": "github_context",
            "trace_confidence": 0.6,
            "trace_reasoning": f"Job linked to commit {commit_sha[:8]} on branch {branch_name or 'unknown'}",
            "available": True,
        })

    # Strategy 3: File-path correlation (which file changed + which file failed)
    elif file_refs and file_change_refs:
        overlap = set(file_refs) & set(file_change_refs)
        if overlap:
            suspect_file = list(overlap)[0]
            trace.update({
                "suspect_file": suspect_file,
                "trace_method": "file_correlation",
                "trace_confidence": 0.5,
                "trace_reasoning": f"File '{suspect_file}' appears in both failure trace and recent changes",
                "available": True,
            })

    # Strategy 4: Stack trace file extraction
    elif stack_trace:
        trace_files = _extract_files_from_trace(stack_trace)
        if trace_files:
            trace.update({
                "suspect_file": trace_files[0],
                "trace_method": "stack_trace",
                "trace_confidence": 0.4,
                "trace_reasoning": f"File '{trace_files[0]}' appears in stack trace at failure point",
                "available": True,
            })

    # No commit data available — graceful fallback
    else:
        trace.update({
            "trace_method": "unavailable",
            "trace_confidence": 0.0,
            "trace_reasoning": "No commit history or change context available for tracing",
            "available": False,
        })

    # ── Build Timeline ──
    timeline_events = []

    if trace["suspect_commit"]:
        timeline_events.append({
            "event": "commit",
            "label": f"Commit {trace['suspect_commit'][:8]}",
            "detail": trace.get("trace_reasoning", ""),
            "timestamp": None,
        })

    if trace["suspect_file"]:
        timeline_events.append({
            "event": "file_change",
            "label": f"Change in {_basename(trace['suspect_file'])}",
            "detail": f"File: {trace['suspect_file']}",
            "timestamp": None,
        })

    if error_message:
        timeline_events.append({
            "event": "failure",
            "label": "Failure Detected",
            "detail": error_message[:120],
            "timestamp": state.get("created_at"),
        })

    trace["timeline"] = timeline_events

    triage["commit_trace"] = trace
    state["triage"] = triage

    logger.info(
        "commit_tracer.completed",
        method=trace["trace_method"],
        confidence=trace["trace_confidence"],
        available=trace["available"],
    )

    return state


# ─── Internal Helpers ────────────────────────────────────

def _extract_commit_refs(raw_logs: str) -> list[dict]:
    """Extract commit SHA references from log text."""
    refs = []
    # Full SHA (40 hex chars)
    for match in re.finditer(r'\b([0-9a-f]{40})\b', raw_logs):
        refs.append({"sha": match.group(1), "message": ""})

    # Short SHA with context: "commit abc1234" or "abc1234 Fix typo"
    for match in re.finditer(r'commit\s+([0-9a-f]{7,12})\b', raw_logs, re.IGNORECASE):
        sha = match.group(1)
        if not any(r["sha"].startswith(sha) for r in refs):
            refs.append({"sha": sha, "message": ""})

    return refs[:5]  # Limit


def _extract_file_changes(raw_logs: str) -> list[str]:
    """Extract file paths that appear to have been changed (from diff headers, etc)."""
    changed = []
    # Unified diff headers
    for match in re.finditer(r'(?:---|\+\+\+)\s+[ab]/(.+)', raw_logs):
        changed.append(match.group(1))
    # "Modified: path/to/file"
    for match in re.finditer(r'(?:Modified|Changed|Updated):\s+(\S+\.\w+)', raw_logs, re.IGNORECASE):
        changed.append(match.group(1))
    return list(set(changed))


def _extract_files_from_trace(stack_trace: list[str]) -> list[str]:
    """Extract source file paths from stack trace lines."""
    files = []
    for line in stack_trace:
        # Python: File "path/to/file.py", line 42
        match = re.search(r'File\s+"([^"]+)"', line)
        if match:
            filepath = match.group(1)
            if not _is_stdlib(filepath):
                files.append(filepath)
            continue
        # JS/TS: at functionName (path/to/file.ts:42:10)
        match = re.search(r'at\s+\S+\s+\(([^)]+):\d+:\d+\)', line)
        if match:
            filepath = match.group(1)
            if not _is_stdlib(filepath):
                files.append(filepath)

    return list(dict.fromkeys(files))  # Deduplicate preserving order


def _is_stdlib(filepath: str) -> bool:
    """Check if a file path is from stdlib or packages (not user code)."""
    noise = [
        "node_modules/", "site-packages/", "lib/python",
        "/usr/lib/", "<frozen", "<string>", "<module>",
    ]
    return any(n in filepath for n in noise)


def _basename(filepath: str) -> str:
    """Get the basename of a file path."""
    return filepath.rsplit("/", 1)[-1] if "/" in filepath else filepath
