"""
Precision Triage Module

Signal quality gate that evaluates failure evidence before root cause analysis.
Computes reproducibility, flake score, evidence strength, and confidence calibration.

This module sits BETWEEN failure_classification and root_cause_analysis in the pipeline.
It does NOT remove or alter upstream signals — it adds triage metadata used downstream.
"""

import re
import hashlib
from typing import Any
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger("automerge.precision_triage")


# ─── Evidence Quality Weights ─────────────────────────────

EVIDENCE_WEIGHTS = {
    "stack_trace":        0.25,  # Stack trace present and parseable
    "error_message":      0.15,  # Clear error message extracted
    "file_references":    0.10,  # Source file paths referenced
    "test_names":         0.10,  # Specific test names identified
    "multiple_signals":   0.10,  # More than one corroborating signal
    "line_numbers":       0.05,  # Specific line numbers cited
    "classification_hit": 0.10,  # Matched a known failure category
    "pattern_recurrence": 0.15,  # Seen this pattern before in memory
}

# Maximum combined evidence score
MAX_EVIDENCE_SCORE = sum(EVIDENCE_WEIGHTS.values())

# ─── Flake Indicators ────────────────────────────────────

FLAKE_PATTERNS = [
    r"timeout|timed?\s*out",
    r"flaky|intermittent|sporadic",
    r"ECONNRESET|ECONNREFUSED|ETIMEDOUT",
    r"socket hang up",
    r"race\s*condition",
    r"deadlock",
    r"resource\s*(temporarily)?\s*unavailable",
    r"too many open files",
    r"connection\s+reset",
    r"network\s+error",
]

# ─── Weak Signal Patterns (noise sources) ─────────────────

WEAK_SIGNAL_PATTERNS = [
    r"deprecated",
    r"ExperimentalWarning",
    r"DeprecationWarning",
    r"FutureWarning",
    r"PendingDeprecationWarning",
    r"console\.log",
    r"DEBUG\s*:",
    r"info\s*:",
]


async def precision_triage(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate signal quality and compute triage metadata.

    Adds to state:
        - triage: dict with evidence_score, flake_score, reproducibility,
          signal_quality, is_noise, confidence_calibrated, evidence_items,
          dedup_key, triage_verdict
    """
    signals = state.get("signals", [])
    error_lines = state.get("error_lines", [])
    stack_trace = state.get("stack_trace", [])
    raw_logs = state.get("raw_logs", "")
    file_refs = state.get("file_references", [])
    test_names = state.get("test_names", [])
    line_numbers = state.get("affected_line_numbers", [])
    failure_type = state.get("failure_type", "unknown")
    error_message = state.get("error_message", "")
    classification_confidence = state.get("classification_confidence", 0.5)

    # ── 1. Compute Evidence Score ──
    evidence_items = []
    evidence_score = 0.0

    if stack_trace and len(stack_trace) >= 2:
        evidence_items.append({
            "type": "stack_trace",
            "weight": EVIDENCE_WEIGHTS["stack_trace"],
            "detail": f"{len(stack_trace)} stack trace lines",
        })
        evidence_score += EVIDENCE_WEIGHTS["stack_trace"]

    if error_message and len(error_message) > 10:
        evidence_items.append({
            "type": "error_message",
            "weight": EVIDENCE_WEIGHTS["error_message"],
            "detail": error_message[:120],
        })
        evidence_score += EVIDENCE_WEIGHTS["error_message"]

    if file_refs:
        source_files = [f for f in file_refs if not _is_noise_file(f)]
        if source_files:
            evidence_items.append({
                "type": "file_references",
                "weight": EVIDENCE_WEIGHTS["file_references"],
                "detail": f"{len(source_files)} source file(s): {', '.join(source_files[:3])}",
            })
            evidence_score += EVIDENCE_WEIGHTS["file_references"]

    if test_names:
        evidence_items.append({
            "type": "test_names",
            "weight": EVIDENCE_WEIGHTS["test_names"],
            "detail": f"{len(test_names)} test(s): {', '.join(test_names[:3])}",
        })
        evidence_score += EVIDENCE_WEIGHTS["test_names"]

    if len(signals) > 1:
        evidence_items.append({
            "type": "multiple_signals",
            "weight": EVIDENCE_WEIGHTS["multiple_signals"],
            "detail": f"{len(signals)} corroborating signals",
        })
        evidence_score += EVIDENCE_WEIGHTS["multiple_signals"]

    if line_numbers:
        evidence_items.append({
            "type": "line_numbers",
            "weight": EVIDENCE_WEIGHTS["line_numbers"],
            "detail": f"Lines: {', '.join(str(n) for n in line_numbers[:5])}",
        })
        evidence_score += EVIDENCE_WEIGHTS["line_numbers"]

    if failure_type != "unknown" and classification_confidence > 0.5:
        evidence_items.append({
            "type": "classification_hit",
            "weight": EVIDENCE_WEIGHTS["classification_hit"],
            "detail": f"Classified as {failure_type} (conf={classification_confidence:.0%})",
        })
        evidence_score += EVIDENCE_WEIGHTS["classification_hit"]

    # Normalize to 0-1
    evidence_score_normalized = min(evidence_score / MAX_EVIDENCE_SCORE, 1.0) if MAX_EVIDENCE_SCORE > 0 else 0.0

    # ── 2. Compute Flake Score ──
    flake_score = _compute_flake_score(error_lines, stack_trace, raw_logs)

    # ── 3. Assess Reproducibility ──
    reproducibility = _assess_reproducibility(
        signals, stack_trace, error_message, flake_score
    )

    # ── 4. Check for Noise / Weak Signals ──
    noise_ratio = _compute_noise_ratio(error_lines, signals)
    is_noise = noise_ratio > 0.7 and evidence_score_normalized < 0.3

    # ── 5. Signal Quality Assessment ──
    if evidence_score_normalized >= 0.6 and flake_score < 0.3:
        signal_quality = "strong"
    elif evidence_score_normalized >= 0.35 or (evidence_score_normalized >= 0.2 and flake_score < 0.5):
        signal_quality = "moderate"
    else:
        signal_quality = "weak"

    # ── 6. Calibrated Confidence ──
    # Start from classification confidence, then adjust based on evidence
    raw_confidence = classification_confidence
    # Boost for strong evidence
    raw_confidence += evidence_score_normalized * 0.3
    # Penalize for flakiness
    raw_confidence -= flake_score * 0.25
    # Penalize for noise
    raw_confidence -= noise_ratio * 0.15
    # Boost for reproducibility
    if reproducibility == "reproducible":
        raw_confidence += 0.1
    elif reproducibility == "likely_flaky":
        raw_confidence -= 0.15
    # Clamp
    confidence_calibrated = max(0.05, min(0.98, raw_confidence))

    # ── 7. Deduplication Key ──
    dedup_key = _compute_dedup_key(failure_type, error_message, signals)

    # ── 8. Triage Verdict ──
    if is_noise:
        triage_verdict = "noise"
    elif signal_quality == "weak" and confidence_calibrated < 0.35:
        triage_verdict = "low_signal"
    elif flake_score > 0.6:
        triage_verdict = "likely_flaky"
    elif signal_quality == "strong" and confidence_calibrated > 0.6:
        triage_verdict = "high_confidence"
    elif confidence_calibrated > 0.4:
        triage_verdict = "moderate_confidence"
    else:
        triage_verdict = "low_confidence"

    triage = {
        "evidence_score": round(evidence_score_normalized, 3),
        "evidence_items": evidence_items,
        "flake_score": round(flake_score, 3),
        "reproducibility": reproducibility,
        "noise_ratio": round(noise_ratio, 3),
        "is_noise": is_noise,
        "signal_quality": signal_quality,
        "confidence_calibrated": round(confidence_calibrated, 3),
        "dedup_key": dedup_key,
        "triage_verdict": triage_verdict,
        "triage_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info(
        "precision_triage.completed",
        verdict=triage_verdict,
        evidence=round(evidence_score_normalized, 2),
        flake=round(flake_score, 2),
        confidence=round(confidence_calibrated, 2),
    )

    state["triage"] = triage
    # Override confidence with calibrated value
    state["confidence"] = confidence_calibrated

    return state


# ─── Internal Helpers ────────────────────────────────────

def _compute_flake_score(
    error_lines: list[str],
    stack_trace: list[str],
    raw_logs: str,
) -> float:
    """Compute a 0-1 flake score based on known flaky patterns."""
    all_text = " ".join(error_lines + stack_trace) + " " + raw_logs[:2000]
    hits = 0
    for pattern in FLAKE_PATTERNS:
        if re.search(pattern, all_text, re.IGNORECASE):
            hits += 1
    # Normalize: 0 hits = 0.0, 3+ hits = high flake score
    return min(hits / 3.0, 1.0)


def _assess_reproducibility(
    signals: list[dict],
    stack_trace: list[str],
    error_message: str,
    flake_score: float,
) -> str:
    """Estimate reproducibility based on signal consistency.

    Returns: 'reproducible', 'partially_reproducible', 'likely_flaky', 'unknown'
    """
    if flake_score > 0.6:
        return "likely_flaky"

    # Strong deterministic signals
    deterministic_types = {
        "syntax_error", "type_mismatch", "missing_import",
        "missing_module", "indentation_error", "build_failure",
    }
    signal_types = {s.get("type") for s in signals}

    if signal_types & deterministic_types:
        return "reproducible"

    if stack_trace and len(stack_trace) >= 3 and error_message:
        return "reproducible"

    if flake_score > 0.3:
        return "likely_flaky"

    if signals:
        return "partially_reproducible"

    return "unknown"


def _compute_noise_ratio(error_lines: list[str], signals: list[dict]) -> float:
    """Compute the ratio of weak/noise signals to total signals."""
    if not error_lines and not signals:
        return 0.5  # Ambiguous

    total_lines = len(error_lines)
    if total_lines == 0:
        return 0.0

    weak_count = 0
    for line in error_lines:
        for pattern in WEAK_SIGNAL_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                weak_count += 1
                break

    return weak_count / total_lines


def _compute_dedup_key(
    failure_type: str,
    error_message: str,
    signals: list[dict],
) -> str:
    """Compute a deduplication key for grouping similar failures."""
    # Normalize error message by stripping variable parts
    normalized_msg = re.sub(r'[0-9a-f]{8,}', '<hash>', error_message)
    normalized_msg = re.sub(r'line \d+', 'line N', normalized_msg, flags=re.IGNORECASE)
    normalized_msg = re.sub(r':\d+:\d+', ':N:N', normalized_msg)
    normalized_msg = re.sub(r'\d+', 'N', normalized_msg)

    signal_types = sorted({s.get("type", "") for s in signals})

    raw = f"{failure_type}|{normalized_msg[:100]}|{'|'.join(signal_types)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_noise_file(filepath: str) -> bool:
    """Check if a file reference is likely noise (not real source)."""
    noise_patterns = [
        "node_modules/", "venv/", ".git/", "__pycache__/",
        "dist/", "build/", ".next/", "coverage/",
    ]
    return any(p in filepath for p in noise_patterns)
