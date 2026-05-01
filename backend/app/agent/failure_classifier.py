"""
Failure Classifier Module

Categorizes failures into actionable types for the pipeline.
"""

from typing import Any


# Failure type taxonomy
FAILURE_CATEGORIES = {
    "test_failure": {
        "signals": ["test_failure", "assertion_failure"],
        "description": "Unit or integration test assertion failed",
        "severity": "medium",
    },
    "build_error": {
        "signals": ["build_failure", "syntax_error", "npm_error", "typescript_error"],
        "description": "Build or compilation failed",
        "severity": "high",
    },
    "type_error": {
        "signals": ["type_mismatch", "typescript_error", "attribute_error"],
        "description": "Type system or attribute access error",
        "severity": "medium",
    },
    "import_error": {
        "signals": ["missing_import", "missing_module"],
        "description": "Missing dependency or import path",
        "severity": "low",
    },
    "runtime_error": {
        "signals": ["undefined_variable", "missing_key", "index_out_of_range", "invalid_value"],
        "description": "Runtime logic error",
        "severity": "medium",
    },
    "infrastructure_error": {
        "signals": ["connection_issue", "missing_file", "permission_denied", "nonzero_exit"],
        "description": "Infrastructure or environment issue",
        "severity": "high",
    },
}


async def classify_failure(state: dict[str, Any]) -> dict[str, Any]:
    """Classify the failure into a category."""
    signals = state.get("signals", [])
    signal_types = {s["type"] for s in signals}

    best_match = "unknown"
    best_score = 0
    best_category = None

    for category_name, category_info in FAILURE_CATEGORIES.items():
        overlap = signal_types & set(category_info["signals"])
        score = len(overlap)
        if score > best_score:
            best_score = score
            best_match = category_name
            best_category = category_info

    # If no match from signals, try from explicit failure_type
    if best_match == "unknown" and state.get("failure_type", "unknown") != "unknown":
        explicit = state["failure_type"]
        if explicit in FAILURE_CATEGORIES:
            best_match = explicit
            best_category = FAILURE_CATEGORIES[explicit]

    state.update({
        "failure_type": best_match,
        "failure_category": best_category or {
            "description": "Unclassified failure",
            "severity": "medium",
        },
        "classification_confidence": min(0.5 + best_score * 0.15, 0.95),
    })

    return state
