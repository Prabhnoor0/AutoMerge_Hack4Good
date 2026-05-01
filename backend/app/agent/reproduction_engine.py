"""
Reproduction Engine Module

Simulates failure reproduction by analyzing signal consistency and determinism.
Assigns reproducibility status and stability score to failures.

This module provides data used by precision_triage and the final report.
It does NOT actually re-execute code — it evaluates reproducibility heuristically
based on signal type, error determinism, and flake indicators.
"""

import re
from typing import Any

import structlog

logger = structlog.get_logger("automerge.reproduction_engine")


# ─── Deterministic Error Categories ──────────────────────

DETERMINISTIC_SIGNALS = {
    "syntax_error",
    "indentation_error",
    "missing_import",
    "missing_module",
    "type_mismatch",
    "build_failure",
    "typescript_error",
    "npm_error",
}

SEMI_DETERMINISTIC_SIGNALS = {
    "attribute_error",
    "undefined_variable",
    "missing_key",
    "index_out_of_range",
    "invalid_value",
    "assertion_failure",
    "test_failure",
    "missing_file",
    "permission_denied",
}

NON_DETERMINISTIC_SIGNALS = {
    "connection_issue",
    "nonzero_exit",
    "unknown_error",
}


async def assess_reproduction(state: dict[str, Any]) -> dict[str, Any]:
    """Assess failure reproducibility and stability.

    Enriches the state['triage'] dict with:
        - reproduction_status: 'reproducible' | 'partially_reproducible' | 'likely_flaky' | 'non_reproducible'
        - stability_score: 0.0-1.0 (1.0 = perfectly stable/reproducible)
        - reproduction_runs: simulated run count
        - reproduction_pass_rate: fraction of runs that would reproduce
        - reproduction_reasoning: human-readable explanation
    """
    signals = state.get("signals", [])
    error_message = state.get("error_message", "")
    stack_trace = state.get("stack_trace", [])
    raw_logs = state.get("raw_logs", "")
    triage = state.get("triage", {})
    flake_score = triage.get("flake_score", 0.0)

    signal_types = {s.get("type", "unknown") for s in signals}

    # ── Determinism Analysis ──
    deterministic_count = len(signal_types & DETERMINISTIC_SIGNALS)
    semi_count = len(signal_types & SEMI_DETERMINISTIC_SIGNALS)
    non_det_count = len(signal_types & NON_DETERMINISTIC_SIGNALS)
    total_classified = deterministic_count + semi_count + non_det_count

    # ── Stack Trace Consistency ──
    has_consistent_trace = _has_consistent_stack_trace(stack_trace, error_message)

    # ── Compute Stability Score ──
    stability_score = 0.5  # baseline

    if total_classified > 0:
        stability_score += (deterministic_count / total_classified) * 0.3
        stability_score += (semi_count / total_classified) * 0.1
        stability_score -= (non_det_count / total_classified) * 0.2

    if has_consistent_trace:
        stability_score += 0.15

    # Flake penalty
    stability_score -= flake_score * 0.3

    # Error message specificity boost
    if error_message and len(error_message) > 20:
        stability_score += 0.05

    stability_score = max(0.0, min(1.0, stability_score))

    # ── Simulated Reproduction Runs ──
    # We simulate N conceptual runs based on determinism
    reproduction_runs = 5
    if stability_score > 0.8:
        reproduction_pass_rate = 1.0  # 5/5 would reproduce
    elif stability_score > 0.6:
        reproduction_pass_rate = 0.8  # 4/5
    elif stability_score > 0.4:
        reproduction_pass_rate = 0.6  # 3/5
    elif stability_score > 0.2:
        reproduction_pass_rate = 0.4  # 2/5
    else:
        reproduction_pass_rate = 0.2  # 1/5

    # ── Reproduction Status ──
    if reproduction_pass_rate >= 0.9:
        reproduction_status = "reproducible"
    elif reproduction_pass_rate >= 0.6:
        reproduction_status = "partially_reproducible"
    elif reproduction_pass_rate >= 0.3:
        reproduction_status = "likely_flaky"
    else:
        reproduction_status = "non_reproducible"

    # ── Reasoning ──
    reasoning_parts = []
    if deterministic_count > 0:
        det_types = signal_types & DETERMINISTIC_SIGNALS
        reasoning_parts.append(
            f"Deterministic signal(s): {', '.join(det_types)}"
        )
    if non_det_count > 0:
        nd_types = signal_types & NON_DETERMINISTIC_SIGNALS
        reasoning_parts.append(
            f"Non-deterministic signal(s): {', '.join(nd_types)}"
        )
    if has_consistent_trace:
        reasoning_parts.append("Stack trace is consistent and specific")
    if flake_score > 0.3:
        reasoning_parts.append(f"Flake indicators detected (score: {flake_score:.0%})")
    reasoning_parts.append(
        f"Estimated reproduction: {int(reproduction_pass_rate * reproduction_runs)}/{reproduction_runs} runs"
    )

    reproduction_reasoning = "; ".join(reasoning_parts)

    # ── Update triage ──
    triage.update({
        "reproduction_status": reproduction_status,
        "stability_score": round(stability_score, 3),
        "reproduction_runs": reproduction_runs,
        "reproduction_pass_rate": round(reproduction_pass_rate, 2),
        "reproduction_reasoning": reproduction_reasoning,
    })

    # Also update top-level reproducibility in triage
    triage["reproducibility"] = reproduction_status

    state["triage"] = triage

    logger.info(
        "reproduction.assessed",
        status=reproduction_status,
        stability=round(stability_score, 2),
        pass_rate=reproduction_pass_rate,
    )

    return state


def _has_consistent_stack_trace(
    stack_trace: list[str], error_message: str
) -> bool:
    """Check if the stack trace is consistent and specific (not generic)."""
    if len(stack_trace) < 2:
        return False

    # Look for specific file + line references in trace
    file_line_refs = 0
    for line in stack_trace:
        if re.search(r'File\s+"[^"]+",\s+line\s+\d+', line):
            file_line_refs += 1
        elif re.search(r'at\s+\S+\s+\([^)]+:\d+:\d+\)', line):
            file_line_refs += 1

    # At least 1 specific file reference = consistent
    return file_line_refs >= 1
