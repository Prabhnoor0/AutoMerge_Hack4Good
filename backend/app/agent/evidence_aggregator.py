"""
Evidence Aggregator Module

Merges multiple signals, triage data, and analysis outputs into a single
coherent evidence-based report. Computes the final probabilistic confidence
score and produces a structured evidence payload.

This is the last precision module in the pipeline, running after commit_tracer
and before summary_generation.
"""

import re
from typing import Any
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger("automerge.evidence_aggregator")


# ─── Scoring Weights for Final Confidence ────────────────

SCORING_WEIGHTS = {
    "evidence_score":       0.25,  # From precision_triage
    "reproducibility":      0.20,  # From reproduction_engine
    "classification_conf":  0.15,  # From failure_classifier
    "commit_trace":         0.10,  # From commit_tracer
    "flake_penalty":        0.15,  # Inverse of flake_score
    "pattern_recurrence":   0.15,  # From bug memory
}


async def aggregate_evidence(state: dict[str, Any]) -> dict[str, Any]:
    """Aggregate all evidence into a final scored report.

    Enriches state with:
        - evidence_report: comprehensive evidence payload
        - confidence: final calibrated score
    """
    triage = state.get("triage", {})
    signals = state.get("signals", [])
    error_message = state.get("error_message", "")
    failure_type = state.get("failure_type", "unknown")
    root_cause = state.get("root_cause", "")
    stack_trace = state.get("stack_trace", [])
    file_refs = state.get("file_references", [])
    test_names = state.get("test_names", [])

    # Triage data
    evidence_items = triage.get("evidence_items", [])
    evidence_score = triage.get("evidence_score", 0.0)
    flake_score = triage.get("flake_score", 0.0)
    reproducibility = triage.get("reproducibility", "unknown")
    reproduction_status = triage.get("reproduction_status", "unknown")
    stability_score = triage.get("stability_score", 0.5)
    signal_quality = triage.get("signal_quality", "moderate")
    noise_ratio = triage.get("noise_ratio", 0.0)
    is_noise = triage.get("is_noise", False)
    triage_verdict = triage.get("triage_verdict", "moderate_confidence")
    dedup_key = triage.get("dedup_key", "")
    commit_trace = triage.get("commit_trace", {})
    reproduction_reasoning = triage.get("reproduction_reasoning", "")

    # ── 1. Group Evidence by Category ──
    grouped_evidence = _group_evidence(
        evidence_items=evidence_items,
        signals=signals,
        stack_trace=stack_trace,
        file_refs=file_refs,
        test_names=test_names,
        error_message=error_message,
        commit_trace=commit_trace,
    )

    # ── 2. Compute Final Confidence Score ──
    final_confidence = _compute_final_confidence(
        evidence_score=evidence_score,
        reproducibility=reproducibility,
        classification_confidence=state.get("classification_confidence", 0.5),
        commit_trace_confidence=commit_trace.get("trace_confidence", 0.0),
        flake_score=flake_score,
        pattern_recurrence=0.0,  # Will be populated from memory when available
    )

    # ── 3. Determine Bug Severity ──
    severity = _compute_severity(
        failure_type=failure_type,
        final_confidence=final_confidence,
        flake_score=flake_score,
        signal_quality=signal_quality,
    )

    # ── 4. Generate "Why This Is Real" / "Why It Might Be Noise" ──
    why_real = _generate_why_real(
        evidence_items, reproducibility, commit_trace, signals
    )
    why_noise = _generate_why_noise(
        flake_score, noise_ratio, is_noise, signal_quality
    )

    # ── 5. Suggested Next Action ──
    next_action = _suggest_next_action(
        triage_verdict, severity, reproducibility, commit_trace
    )

    # ── 6. Build Evidence Report ──
    evidence_report = {
        # Core
        "title": state.get("failure_title", "Unknown Failure"),
        "failure_type": failure_type,
        "root_cause": root_cause,
        "severity": severity,

        # Evidence
        "evidence_items": evidence_items,
        "grouped_evidence": grouped_evidence,
        "evidence_score": round(evidence_score, 3),

        # Reproducibility
        "reproducibility": reproduction_status,
        "stability_score": round(stability_score, 3),
        "reproduction_reasoning": reproduction_reasoning,

        # Flake
        "flake_score": round(flake_score, 3),
        "is_flaky": flake_score > 0.4,

        # Commit trace
        "commit_trace": commit_trace,

        # Scoring
        "confidence": round(final_confidence, 3),
        "signal_quality": signal_quality,
        "triage_verdict": triage_verdict,
        "dedup_key": dedup_key,

        # Explanations
        "why_real": why_real,
        "why_noise": why_noise,
        "next_action": next_action,

        # Metadata
        "is_noise": is_noise,
        "noise_ratio": round(noise_ratio, 3),
        "aggregated_at": datetime.now(timezone.utc).isoformat(),
    }

    state["evidence_report"] = evidence_report
    state["confidence"] = final_confidence

    logger.info(
        "evidence_aggregator.completed",
        confidence=round(final_confidence, 2),
        severity=severity,
        verdict=triage_verdict,
    )

    return state


# ─── Scoring ─────────────────────────────────────────────

def _compute_final_confidence(
    evidence_score: float,
    reproducibility: str,
    classification_confidence: float,
    commit_trace_confidence: float,
    flake_score: float,
    pattern_recurrence: float,
) -> float:
    """Compute a calibrated final confidence score using weighted components."""
    # Reproducibility → numeric
    repro_map = {
        "reproducible": 1.0,
        "partially_reproducible": 0.6,
        "likely_flaky": 0.25,
        "non_reproducible": 0.1,
        "unknown": 0.4,
    }
    repro_score = repro_map.get(reproducibility, 0.4)

    # Weighted sum
    score = (
        evidence_score * SCORING_WEIGHTS["evidence_score"]
        + repro_score * SCORING_WEIGHTS["reproducibility"]
        + classification_confidence * SCORING_WEIGHTS["classification_conf"]
        + commit_trace_confidence * SCORING_WEIGHTS["commit_trace"]
        + (1.0 - flake_score) * SCORING_WEIGHTS["flake_penalty"]
        + pattern_recurrence * SCORING_WEIGHTS["pattern_recurrence"]
    )

    # Normalize to meaningful range: low evidence shouldn't trivially reach 0.9+
    return max(0.05, min(0.95, score))


def _compute_severity(
    failure_type: str,
    final_confidence: float,
    flake_score: float,
    signal_quality: str,
) -> str:
    """Determine report severity."""
    severity_base = {
        "build_error": 0.8,
        "infrastructure_error": 0.7,
        "type_error": 0.6,
        "runtime_error": 0.6,
        "test_failure": 0.5,
        "import_error": 0.4,
    }

    base = severity_base.get(failure_type, 0.5)
    adjusted = base * 0.5 + final_confidence * 0.3 + (1 - flake_score) * 0.2

    if adjusted >= 0.7:
        return "critical"
    elif adjusted >= 0.55:
        return "high"
    elif adjusted >= 0.4:
        return "medium"
    else:
        return "low"


# ─── Evidence Grouping ───────────────────────────────────

def _group_evidence(
    evidence_items: list[dict],
    signals: list[dict],
    stack_trace: list[str],
    file_refs: list[str],
    test_names: list[str],
    error_message: str,
    commit_trace: dict,
) -> dict[str, list[dict]]:
    """Group evidence by category for structured display."""
    groups: dict[str, list[dict]] = {
        "signals": [],
        "stack_trace": [],
        "files": [],
        "tests": [],
        "commit": [],
    }

    # Signals
    for sig in signals[:5]:
        groups["signals"].append({
            "label": sig.get("type", "unknown"),
            "detail": sig.get("evidence", "")[:150],
        })

    # Stack trace (condensed)
    if stack_trace:
        # Show the most relevant frames
        relevant = _extract_relevant_frames(stack_trace)
        for frame in relevant[:4]:
            groups["stack_trace"].append({
                "label": "Frame",
                "detail": frame[:200],
            })

    # Files
    source_files = [f for f in file_refs if "node_modules" not in f and "venv" not in f]
    for f in source_files[:5]:
        groups["files"].append({"label": "File", "detail": f})

    # Tests
    for t in test_names[:5]:
        groups["tests"].append({"label": "Test", "detail": t})

    # Commit
    if commit_trace.get("available"):
        groups["commit"].append({
            "label": commit_trace.get("trace_method", "trace"),
            "detail": commit_trace.get("trace_reasoning", ""),
        })

    # Remove empty groups
    return {k: v for k, v in groups.items() if v}


def _extract_relevant_frames(stack_trace: list[str]) -> list[str]:
    """Extract the most relevant frames from a stack trace (skip stdlib)."""
    relevant = []
    for line in stack_trace:
        if any(skip in line for skip in [
            "site-packages/", "node_modules/", "/usr/lib/",
            "<frozen", "lib/python", "Traceback",
        ]):
            continue
        if line.strip():
            relevant.append(line.strip())
    return relevant if relevant else stack_trace[:4]


# ─── Explanation Generators ──────────────────────────────

def _generate_why_real(
    evidence_items: list[dict],
    reproducibility: str,
    commit_trace: dict,
    signals: list[dict],
) -> list[str]:
    """Generate human-readable reasons why this finding is likely real."""
    reasons = []

    evidence_count = len(evidence_items)
    if evidence_count >= 3:
        reasons.append(f"Supported by {evidence_count} independent evidence sources")
    elif evidence_count >= 1:
        reasons.append(f"Backed by {evidence_count} evidence source(s)")

    if reproducibility in ("reproducible", "partially_reproducible"):
        reasons.append(
            "Reproducible" if reproducibility == "reproducible"
            else "Partially reproducible across simulated runs"
        )

    if commit_trace.get("available"):
        reasons.append(f"Traced to {commit_trace.get('trace_method', 'commit')} evidence")

    # Signal-specific reasons
    signal_types = {s.get("type") for s in signals}
    if signal_types & {"syntax_error", "build_failure"}:
        reasons.append("Deterministic failure — will block every build")
    elif signal_types & {"type_mismatch", "missing_import"}:
        reasons.append("Type system or import error — deterministic")

    return reasons if reasons else ["Limited evidence available"]


def _generate_why_noise(
    flake_score: float,
    noise_ratio: float,
    is_noise: bool,
    signal_quality: str,
) -> list[str]:
    """Generate reasons why this finding might be noise."""
    reasons = []

    if flake_score > 0.4:
        reasons.append(f"Flake indicators present (score: {flake_score:.0%})")
    if noise_ratio > 0.5:
        reasons.append(f"High noise ratio in error lines ({noise_ratio:.0%})")
    if signal_quality == "weak":
        reasons.append("Signal quality is weak — may be a false positive")
    if is_noise:
        reasons.append("Overall assessment: likely noise")

    return reasons if reasons else ["No significant noise indicators"]


def _suggest_next_action(
    triage_verdict: str,
    severity: str,
    reproducibility: str,
    commit_trace: dict,
) -> str:
    """Suggest the next developer action based on evidence."""
    if triage_verdict == "noise":
        return "This finding is likely noise. No action needed unless it recurs."

    if triage_verdict == "likely_flaky":
        return "Investigate test stability. Consider adding retry logic or fixing the flaky test."

    if triage_verdict == "high_confidence":
        if commit_trace.get("available"):
            suspect = commit_trace.get("suspect_commit", "")
            file = commit_trace.get("suspect_file", "")
            return (
                f"Review the fix below. "
                + (f"Check commit {suspect[:8]} " if suspect else "")
                + (f"in {file} " if file else "")
                + "for the root cause."
            )
        return "Apply the suggested fix and run the test suite to verify."

    if triage_verdict == "moderate_confidence":
        return "Review the evidence and fix. Manual verification recommended."

    if triage_verdict == "low_confidence":
        return "Low confidence — monitor for recurrence before investing time."

    return "Review the report and determine if action is needed."
