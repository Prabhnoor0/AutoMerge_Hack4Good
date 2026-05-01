"""
Signal Extractor Module

Extracts the most relevant technical signals from parsed logs.
"""

import re
from typing import Any


# Common error patterns and their signal types
ERROR_PATTERNS = {
    r"ImportError|ModuleNotFoundError": "missing_import",
    r"TypeError.*argument|TypeError.*expected": "type_mismatch",
    r"AttributeError": "attribute_error",
    r"NameError": "undefined_variable",
    r"SyntaxError": "syntax_error",
    r"IndentationError": "indentation_error",
    r"KeyError": "missing_key",
    r"IndexError": "index_out_of_range",
    r"ValueError": "invalid_value",
    r"AssertionError|assert.*failed": "assertion_failure",
    r"ConnectionError|TimeoutError": "connection_issue",
    r"FileNotFoundError": "missing_file",
    r"PermissionError": "permission_denied",
    r"npm ERR!|Module not found": "npm_error",
    r"Cannot find module": "missing_module",
    r"TypeScript error|TS\d{4}": "typescript_error",
    r"FAIL\s+.*\.test": "test_failure",
    r"Build failed|compilation failed": "build_failure",
    r"exit code [1-9]": "nonzero_exit",
}


async def extract_signals(state: dict[str, Any]) -> dict[str, Any]:
    """Extract key technical signals from parsed log data."""
    error_lines = state.get("error_lines", [])
    stack_trace = state.get("stack_trace", [])
    raw_logs = state.get("raw_logs", "")

    # Match error patterns
    detected_signals = []
    for pattern, signal_type in ERROR_PATTERNS.items():
        for line in error_lines + stack_trace:
            if re.search(pattern, line, re.IGNORECASE):
                detected_signals.append({
                    "type": signal_type,
                    "evidence": line[:200],
                    "pattern": pattern,
                })
                break  # One match per pattern is enough

    # Determine primary signal
    primary_signal = detected_signals[0] if detected_signals else {
        "type": "unknown_error",
        "evidence": error_lines[0] if error_lines else "No error lines found",
        "pattern": "none",
    }

    # Extract specific error message
    error_message = ""
    for line in error_lines + stack_trace:
        if any(kw in line for kw in ["Error:", "Exception:", "FAIL", "error["]):
            error_message = line.strip()
            break
    if not error_message and error_lines:
        error_message = error_lines[0]

    # Extract line numbers from references
    line_numbers = re.findall(r':(\d+)', raw_logs)
    line_numbers = [int(n) for n in line_numbers[:5]]

    state.update({
        "signals": detected_signals,
        "primary_signal": primary_signal,
        "error_message": error_message,
        "affected_line_numbers": line_numbers,
        "signal_count": len(detected_signals),
    })

    return state
