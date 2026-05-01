"""
Root Cause Analyzer Module

Determines the probable root cause of a failure.
Supports both log-based and code-analysis-based root cause detection.
"""

import re
from typing import Any


ROOT_CAUSE_TEMPLATES = {
    "test_failure": {
        "cause": "Test assertion failed due to unexpected return value or state",
        "reasoning": "The test expected a specific value but received a different result. This indicates a logic error in the function under test or stale expectations.",
        "code_area": "Test file and the source function being tested",
    },
    "build_error": {
        "cause": "Build process failed due to compilation or bundling error",
        "reasoning": "The build system hit a fatal error. Common causes: syntax errors, missing deps, or incompatible config.",
        "code_area": "Build configuration and source files with syntax issues",
    },
    "type_error": {
        "cause": "Type mismatch between expected and actual value types",
        "reasoning": "A function received wrong type or a property was accessed on an incompatible object.",
        "code_area": "Function signatures and call sites with type mismatches",
    },
    "import_error": {
        "cause": "Missing module or incorrect import path",
        "reasoning": "A required module could not be found. Dependency not installed or file moved without updating imports.",
        "code_area": "Import statements and dependency declarations",
    },
    "runtime_error": {
        "cause": "Runtime logic error causing unexpected program behavior",
        "reasoning": "Accessing undefined variables, missing keys, or array index out of bounds.",
        "code_area": "Runtime execution path and data access patterns",
    },
    "infrastructure_error": {
        "cause": "Infrastructure or environment configuration issue",
        "reasoning": "Network timeouts, missing files, or permission issues.",
        "code_area": "Configuration files and environment setup",
    },
}


async def analyze_root_cause(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze and determine the root cause."""
    failure_type = state.get("failure_type", "unknown")
    error_message = state.get("error_message", "")
    file_refs = state.get("file_references", [])
    primary_signal = state.get("primary_signal", {})
    raw_logs = state.get("raw_logs", "")

    # ── Code-aware mode: analyze source directly ──
    is_code_submission = "─── Source Code ───" in raw_logs
    if is_code_submission:
        return _analyze_code_submission(state, raw_logs)

    # ── Log-based mode (original behavior) ──
    template = ROOT_CAUSE_TEMPLATES.get(failure_type, {
        "cause": "Unable to determine specific root cause",
        "reasoning": "The failure pattern does not match known categories.",
        "code_area": "Unknown",
    })

    specific_cause = template["cause"]
    if error_message:
        specific_cause = f"{template['cause']}. Specifically: {error_message[:200]}"

    affected_file = "unknown"
    if file_refs:
        source_files = [f for f in file_refs if "test" not in f.lower()]
        affected_file = source_files[0] if source_files else file_refs[0]

    base_confidence = state.get("classification_confidence", 0.5)
    boost = sum([
        0.1 if error_message else 0,
        0.1 if file_refs else 0,
        0.1 if state.get("stack_trace") else 0,
    ])
    confidence = min(base_confidence + boost, 0.95)

    reasoning_trace = (
        f"1. Detected {len(state.get('signals', []))} technical signals\n"
        f"2. Primary signal: {primary_signal.get('type', 'unknown')}\n"
        f"3. Classified as: {failure_type}\n"
        f"4. Root cause: {specific_cause}\n"
        f"5. Affected area: {affected_file}\n"
        f"6. Confidence: {confidence:.0%}"
    )

    state.update({
        "root_cause": specific_cause,
        "root_cause_reasoning": template["reasoning"],
        "affected_file": affected_file,
        "affected_code_area": template["code_area"],
        "confidence": confidence,
        "reasoning_trace": reasoning_trace,
    })
    return state


def _analyze_code_submission(state: dict, raw_logs: str) -> dict:
    """Analyze root cause from directly submitted source code."""
    from app.agent.code_analyzer import analyze_code

    # Extract source code from logs
    source_match = re.search(r"─── Source Code ───\n(.*?)─── End Source ───", raw_logs, re.DOTALL)
    if not source_match:
        state.update({
            "root_cause": "Could not extract source code from submission",
            "confidence": 0.3,
            "reasoning_trace": "Source code markers not found in submission",
        })
        return state

    source_code = source_match.group(1).strip()

    # Detect language
    lang_match = re.search(r"Analyzing\s+[\w.]+\s+\((\w+)\)", raw_logs)
    language = lang_match.group(1) if lang_match else "python"

    # Run deep analysis
    analysis = analyze_code(source_code, language)
    issues = analysis["issues"]
    metrics = analysis["metrics"]

    if not issues:
        state.update({
            "root_cause": "No critical issues detected — code follows standard patterns",
            "root_cause_reasoning": "Static analysis passed without finding actionable issues.",
            "confidence": 0.6,
            "failure_type": "clean",
            "reasoning_trace": (
                f"1. Analyzed {metrics['total_lines']} lines of {language} code\n"
                f"2. Ran {len(PYTHON_BUG_PATTERNS) if language in ('python','py') else len([])} pattern checks\n"
                f"3. No errors, warnings, or bugs detected\n"
                f"4. Code quality: Good\n"
                f"5. Confidence: 60%"
            ),
        })
        return state

    # Build root cause from top issues
    top_issues = issues[:3]
    severity_map = {
        "error": "Critical",
        "security": "Security vulnerability",
        "bug": "Bug",
        "warning": "Code quality issue",
        "info": "Improvement opportunity",
    }

    primary = top_issues[0]
    root_cause = f"{severity_map.get(primary['severity'], 'Issue')}: {primary['message']}"
    if primary.get("line"):
        root_cause += f" (line {primary['line']})"

    # Determine failure type from issues
    if any(i["severity"] == "error" for i in issues):
        failure_type = "build_error"
    elif any(i["severity"] == "security" for i in issues):
        failure_type = "runtime_error"
    elif any(i["severity"] == "bug" for i in issues):
        failure_type = "runtime_error"
    else:
        failure_type = "type_error"

    # Confidence based on severity
    confidence_map = {"error": 0.92, "security": 0.88, "bug": 0.82, "warning": 0.7, "info": 0.6}
    confidence = confidence_map.get(primary["severity"], 0.6)

    # Build detailed reasoning trace
    trace_parts = [
        f"1. Analyzed {metrics['total_lines']} lines of {language} code",
        f"2. Found {metrics['issue_count']} issue(s): {metrics['error_count']} errors, {metrics['warning_count']} warnings, {metrics['info_count']} info",
        f"3. Primary issue: {primary['message']}",
    ]
    for i, issue in enumerate(top_issues[1:], 4):
        trace_parts.append(f"{i}. Also found: {issue['message']} (line {issue.get('line', '?')})")
    trace_parts.append(f"{len(trace_parts)+1}. Suggested fix: {primary.get('fix_hint', 'See generated patch')}")
    trace_parts.append(f"{len(trace_parts)+1}. Confidence: {confidence:.0%}")

    state.update({
        "root_cause": root_cause,
        "root_cause_reasoning": primary.get("fix_hint", ""),
        "affected_file": state.get("failure_title", "").split(": ")[-1] if ": " in state.get("failure_title", "") else "submitted_code",
        "confidence": confidence,
        "failure_type": failure_type,
        "code_issues": issues,
        "code_metrics": metrics,
        "reasoning_trace": "\n".join(trace_parts),
    })
    return state


# Make template dict available for import
PYTHON_BUG_PATTERNS = []  # populated from code_analyzer at runtime
