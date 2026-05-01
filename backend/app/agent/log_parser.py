"""
Log Parser Module

Cleans and normalizes raw build/test logs into structured segments.
"""

import re
from typing import Any


async def parse_logs(state: dict[str, Any]) -> dict[str, Any]:
    """Parse raw logs into structured segments."""
    raw_logs = state.get("raw_logs", "")

    # Split into lines and clean
    lines = raw_logs.strip().split("\n")
    cleaned_lines = [line.strip() for line in lines if line.strip()]

    # Extract error lines
    error_lines = []
    warning_lines = []
    stack_trace_lines = []
    info_lines = []

    in_traceback = False

    for line in cleaned_lines:
        lower = line.lower()

        # Detect traceback blocks
        if "traceback" in lower or "exception" in lower:
            in_traceback = True
        if in_traceback:
            stack_trace_lines.append(line)
            if not line.startswith(" ") and line != cleaned_lines[0] and "Error" in line:
                in_traceback = False
            continue

        # Categorize lines
        if any(kw in lower for kw in ["error", "failed", "failure", "fatal", "cannot", "undefined"]):
            error_lines.append(line)
        elif any(kw in lower for kw in ["warning", "warn", "deprecated"]):
            warning_lines.append(line)
        else:
            info_lines.append(line)

    # Extract file references
    file_refs = re.findall(r'[\w/\\]+\.\w+(?::\d+)?', raw_logs)
    file_refs = list(set(file_refs))[:10]  # Deduplicate and limit

    # Extract test names
    test_names = re.findall(r'(?:test_\w+|FAIL:?\s+\w+|FAILED\s+[\w.]+)', raw_logs, re.IGNORECASE)
    test_names = list(set(test_names))[:10]

    state.update({
        "parsed_logs": {
            "total_lines": len(cleaned_lines),
            "error_count": len(error_lines),
            "warning_count": len(warning_lines),
        },
        "error_lines": error_lines,
        "warning_lines": warning_lines,
        "stack_trace": stack_trace_lines,
        "info_lines": info_lines[:20],  # Limit info lines
        "file_references": file_refs,
        "test_names": test_names,
        "cleaned_logs": "\n".join(cleaned_lines),
    })

    return state
