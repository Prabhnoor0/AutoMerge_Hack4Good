"""
Code Analyzer Module

Performs language-aware static analysis on source code.
Uses real language parsers/compilers as the primary diagnostic source:
  - Python:     compile() + ast.parse()  (always available)
  - JavaScript: node --check             (V8, requires Node.js)
  - TypeScript: tsc --noEmit             (requires TypeScript)

Heuristic/regex checks are ONLY used as a secondary quality layer after
the parser runs — never as the primary source of truth.
"""

import re
import structlog
from typing import Any

from app.agent.parser_router import (
    route_and_parse,
    normalize_language,
    detect_language as router_detect_language,
)
from app.agent.diagnostics import NormalizedIssue, ParseResult

logger = structlog.get_logger("automerge.code_analyzer")


# ─── Secondary quality checks (Python only, post-parse) ──
# These supplement the AST parser, never replace it.
# They only run if the primary parse succeeded.

_PYTHON_QUALITY_PATTERNS = [
    {
        "id": "py_broad_import",
        "pattern": r"^from\s+\w+\s+import\s+\*",
        "severity": "warning",
        "category": "quality",
        "message": "Wildcard import pollutes namespace and hides dependencies",
        "fix_hint": "Import specific names instead of using *",
        "explanation": "Wildcard imports make it hard to trace where names come from and can shadow builtins.",
    },
    {
        "id": "py_global_usage",
        "pattern": r"^\s*global\s+",
        "severity": "warning",
        "category": "quality",
        "message": "Global variable usage makes code harder to test and reason about",
        "fix_hint": "Pass values as function arguments or use a class to hold state",
        "explanation": "Global state introduces hidden coupling and makes unit testing difficult.",
    },
    {
        "id": "py_assert_in_prod",
        "pattern": r"^\s*assert\s+",
        "severity": "info",
        "category": "quality",
        "message": "assert statements are removed when Python runs with -O (optimize flag)",
        "fix_hint": "Use explicit if/raise for production validation",
        "explanation": "Running `python -O` strips all assert statements, removing runtime checks silently.",
    },
]

# JS/TS quality checks — only non-syntax, non-false-positive patterns
# The infamous js_equality_loose pattern [^!=]=[^=] is intentionally REMOVED.
# It generates false positives on every valid assignment operator.
_JS_QUALITY_PATTERNS = [
    {
        "id": "js_var_usage",
        "pattern": r"\bvar\s+\w",
        "severity": "warning",
        "category": "quality",
        "message": "'var' has function scope — use 'let' or 'const' for block scope",
        "fix_hint": "Replace 'var' with 'const' (if not reassigned) or 'let'",
        "explanation": "'var' leaks out of if/for/while blocks due to function-level hoisting.",
    },
    {
        "id": "js_any_type",
        "pattern": r":\s*any\b",
        "severity": "warning",
        "category": "type",
        "message": "Using 'any' type disables TypeScript type safety for this value",
        "fix_hint": "Use a specific type or 'unknown' with type narrowing",
        "explanation": "'any' is an escape hatch that removes all type checking, defeating TypeScript's purpose.",
    },
    {
        "id": "js_console_log",
        "pattern": r"\bconsole\.(log|warn|error|debug)\(",
        "severity": "info",
        "category": "quality",
        "message": "Console statement left in production code",
        "fix_hint": "Use a structured logging library instead",
        "explanation": "console.* calls left in production can leak sensitive data and clutter output.",
    },
]


def _run_secondary_quality(
    code: str,
    language: str,
    existing_issue_lines: set[int],
) -> list[dict]:
    """
    Run regex-based quality patterns as a secondary layer.
    Only reports issues on lines not already covered by the primary parser.
    Only applies patterns valid for the given language.
    Marks all results as origin='heuristic' with reduced confidence.
    """
    if language == "python":
        patterns = _PYTHON_QUALITY_PATTERNS
    elif language in ("javascript", "typescript"):
        patterns = _JS_QUALITY_PATTERNS
    else:
        return []

    issues = []
    lines = code.splitlines()

    for i, line in enumerate(lines, 1):
        for pat in patterns:
            if re.search(pat["pattern"], line):
                # Don't double-report lines the parser already covered
                if i in existing_issue_lines:
                    continue
                issues.append({
                    "id": pat["id"],
                    "language": language,
                    "severity": pat["severity"],
                    "category": pat["category"],
                    "message": pat["message"],
                    "explanation": pat.get("explanation", ""),
                    "line": i,
                    "column": 0,
                    "source_line": line.rstrip(),
                    "fix_hint": pat["fix_hint"],
                    "confidence": 0.70,  # Lower confidence for heuristic checks
                    "origin": "heuristic",
                    "parser_name": "regex_quality",
                    "backend_name": "Secondary quality layer",
                    "code_frame": "",
                })

    return issues


# ─── Public API ───────────────────────────────────────────

def analyze_code(code: str, language: str, filename: str = "") -> dict[str, Any]:
    """
    Perform language-aware static analysis on source code.

    Primary analysis uses real parsers:
      - Python:     compile() + ast.parse()
      - JavaScript: node --check (V8)
      - TypeScript: tsc --noEmit

    Secondary quality checks (regex) supplement the parser output
    on lines not already reported.

    Returns a dict with:
      - issues:        list of dicts (backward-compatible shape)
      - parse_result:  ParseResult object for internal use
      - metrics:       summary counts
      - source_lines:  split source for patch generation
      - parser_info:   which backend ran and whether it was a fallback
    """
    lang = normalize_language(language)
    source_lines = code.splitlines()

    # ── Step 1: Real parser (primary) ────────────────────
    parse_result: ParseResult = route_and_parse(code, lang, filename)

    logger.info(
        "code_analyzer.parsed",
        language=lang,
        backend=parse_result.backend_name,
        is_fallback=parse_result.is_fallback,
        issue_count=len(parse_result.issues),
    )

    # Convert NormalizedIssue objects to dicts for backward compat
    issues: list[dict] = parse_result.to_legacy_issues()

    # Track lines already covered by the parser
    parser_lines = {iss["line"] for iss in issues}

    # ── Step 2: Secondary quality layer (heuristic, supplementary) ──
    # Only runs if the primary parser succeeded (no point adding noise on broken code)
    if parse_result.parse_success and not parse_result.has_syntax_errors:
        quality_issues = _run_secondary_quality(code, lang, parser_lines)
        issues.extend(quality_issues)

    # ── Step 3: Sort — errors first, then by severity ────
    _severity_order = {"error": 0, "security": 1, "bug": 2, "warning": 3, "info": 4}
    issues.sort(key=lambda x: (_severity_order.get(x["severity"], 5), x.get("line", 0)))

    # ── Step 4: Metrics ──────────────────────────────────
    metrics = {
        "total_lines": len(source_lines),
        "non_empty_lines": sum(1 for l in source_lines if l.strip()),
        "issue_count": len(issues),
        "error_count": sum(1 for i in issues if i["severity"] == "error"),
        "warning_count": sum(1 for i in issues if i["severity"] in ("warning", "bug", "security")),
        "info_count": sum(1 for i in issues if i["severity"] == "info"),
        "parser_backend": parse_result.backend_name,
        "is_fallback": parse_result.is_fallback,
    }

    return {
        "issues": issues,
        "parse_result": parse_result,   # Internal — not sent to frontend directly
        "metrics": metrics,
        "source_lines": source_lines,
        "parser_info": {
            "backend": parse_result.backend_name,
            "parser_name": parse_result.parser_name,
            "is_fallback": parse_result.is_fallback,
            "fallback_reason": parse_result.fallback_reason,
            "parser_confidence": parse_result.parser_confidence,
        },
    }
