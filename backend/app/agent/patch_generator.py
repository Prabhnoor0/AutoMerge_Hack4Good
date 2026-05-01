"""
Patch Generator Module

Generates code fix patches based on root cause analysis.
Supports two modes:
  1. Template-based (for demo scenarios — deterministic)
  2. Code-aware (for user-submitted code — dynamic analysis)
"""

import re
import textwrap
from typing import Any

from app.agent.code_analyzer import analyze_code
from app.agent.parser_router import normalize_language, detect_language as router_detect_language


# ─── Demo Fix Templates (deterministic for presentations) ─────

FIX_TEMPLATES = {
    "test_failure": {
        "file_path": "src/utils/calculate.py",
        "language": "python",
        "original": '''def calculate_total(items):
    total = 0
    for item in items:
        total += item.price
    return total''',
        "fixed": '''def calculate_total(items):
    total = 0
    for item in items:
        total += item.price * item.quantity
    return round(total, 2)''',
        "explanation": "The calculate_total function was not accounting for item quantity and had floating-point precision issues. Fixed by multiplying price by quantity and rounding the result.",
    },
    "build_error": {
        "file_path": "src/components/Dashboard.tsx",
        "language": "typescript",
        "original": '''import { useState } from 'react';
import { DataChart } from './DataChart';
import { formatCurrency } from '../utils/format';

export function Dashboard({ data }) {
  const [filter, setFilter] = useState(null);
  const filtered = data.filter(d => d.status = filter);
  return <DataChart data={filtered} />;
}''',
        "fixed": '''import { useState } from 'react';
import { DataChart } from './DataChart';
import { formatCurrency } from '../utils/format';

interface DashboardProps {
  data: Array<{ status: string; value: number }>;
}

export function Dashboard({ data }: DashboardProps) {
  const [filter, setFilter] = useState<string | null>(null);
  const filtered = filter ? data.filter(d => d.status === filter) : data;
  return <DataChart data={filtered} />;
}''',
        "explanation": "Fixed type annotations, added interface for props, changed assignment operator (=) to comparison (===) in filter, and handled null filter case.",
    },
    "type_error": {
        "file_path": "src/services/api.ts",
        "language": "typescript",
        "original": '''async function fetchUser(id: string) {
  const response = await fetch(`/api/users/${id}`);
  const data = response.json();
  return data.user.name;
}''',
        "fixed": '''async function fetchUser(id: string): Promise<string | null> {
  const response = await fetch(`/api/users/${id}`);
  if (!response.ok) return null;
  const data = await response.json();
  return data?.user?.name ?? null;
}''',
        "explanation": "Added missing await on response.json(), added error handling for non-OK responses, used optional chaining to prevent TypeError on nested access, and added proper return type.",
    },
}


# ─── Code-Aware Fix Generation ────────────────────────────

def _apply_python_fixes(code: str, issues: list[dict]) -> tuple[str, list[str]]:
    """Apply fixes to Python code based on detected issues.
    Prioritizes real parser/compiler diagnostics (origin=parser/compiler)
    over heuristic-origin issues.
    """
    lines = code.split("\n")
    fixed_lines = list(lines)
    changes: list[str] = []

    # Sort: real parser issues first, then by line in reverse (prevent index shift)
    def _sort_key(i: dict):
        origin_priority = 0 if i.get("origin") in ("parser", "compiler") else 1
        return (origin_priority, -(i.get("line", 0)))

    fixable = [
        i for i in issues
        if i["severity"] in ("error", "security", "bug", "warning")
    ]
    fixable.sort(key=_sort_key)

    for issue in fixable:
        line_idx = issue.get("line", 0) - 1
        if line_idx < 0 or line_idx >= len(fixed_lines):
            continue

        line = fixed_lines[line_idx]
        issue_id = issue["id"]

        if issue_id in ("py_bare_except", "py_bare_except_ast"):
            # Fix: except: → except Exception as e:
            if re.match(r'^(\s*)except\s*:', line):
                indent = re.match(r'^(\s*)', line).group(1)
                fixed_lines[line_idx] = f"{indent}except Exception as e:"
                changes.append(f"Line {line_idx+1}: Changed bare except to 'except Exception as e:'")

        elif issue_id == "py_mutable_default":
            # Fix: def f(x=[]) → def f(x=None) + body init
            match = re.search(r'(=\s*)\[\]', line)
            if match:
                fixed_lines[line_idx] = line.replace("=[]", "=None").replace("= []", "=None")
                # Try to add init line in body
                param_name = re.search(r'(\w+)\s*=\s*None', fixed_lines[line_idx])
                if param_name and line_idx + 1 < len(fixed_lines):
                    body_indent = re.match(r'^(\s*)', fixed_lines[line_idx + 1])
                    if body_indent:
                        init_line = f"{body_indent.group(1)}if {param_name.group(1)} is None: {param_name.group(1)} = []"
                        fixed_lines.insert(line_idx + 1, init_line)
                changes.append(f"Line {line_idx+1}: Replaced mutable default argument with None")

            match = re.search(r'(=\s*)\{\}', line)
            if match:
                fixed_lines[line_idx] = line.replace("={}", "=None").replace("= {}", "=None")
                param_name = re.search(r'(\w+)\s*=\s*None', fixed_lines[line_idx])
                if param_name and line_idx + 1 < len(fixed_lines):
                    body_indent = re.match(r'^(\s*)', fixed_lines[line_idx + 1])
                    if body_indent:
                        init_line = f"{body_indent.group(1)}if {param_name.group(1)} is None: {param_name.group(1)} = {{}}"
                        fixed_lines.insert(line_idx + 1, init_line)
                changes.append(f"Line {line_idx+1}: Replaced mutable default argument with None")

        elif issue_id == "py_eval_usage":
            # Fix: eval(x) → ast.literal_eval(x)
            fixed_lines[line_idx] = line.replace("eval(", "ast.literal_eval(")
            # Check if import exists
            if not any("import ast" in l for l in fixed_lines[:5]):
                fixed_lines.insert(0, "import ast")
            changes.append(f"Line {line_idx+1}: Replaced eval() with ast.literal_eval() for safety")

        elif issue_id == "py_dict_direct_access":
            # Fix: d["a"]["b"] → d.get("a", {}).get("b", default)
            match = re.search(r'(\w+)\["([^"]+)"\]\["([^"]+)"\]', line)
            if match:
                var, key1, key2 = match.groups()
                safe = f'{var}.get("{key1}", {{}}).get("{key2}")'
                fixed_lines[line_idx] = line.replace(match.group(0), safe)
                changes.append(f"Line {line_idx+1}: Added safe dict access with .get()")

        elif issue_id == "py_none_comparison":
            fixed_lines[line_idx] = line.replace("== None", "is None").replace("!= None", "is not None")
            changes.append(f"Line {line_idx+1}: Use 'is None' instead of '== None'")

    return "\n".join(fixed_lines), changes


def _apply_js_fixes(code: str, issues: list[dict]) -> tuple[str, list[str]]:
    """Apply fixes to JavaScript/TypeScript code.
    Only applies fixes for known safe patterns. The js_equality_loose
    pattern (false positive on assignments) is intentionally not handled here.
    """
    lines = code.split("\n")
    fixed_lines = list(lines)
    changes: list[str] = []

    def _sort_key(i: dict):
        origin_priority = 0 if i.get("origin") in ("parser", "compiler") else 1
        return (origin_priority, -(i.get("line", 0)))

    fixable = [i for i in issues if i["severity"] in ("error", "warning", "bug")]
    fixable.sort(key=_sort_key)

    for issue in fixable:
        line_idx = issue.get("line", 0) - 1
        if line_idx < 0 or line_idx >= len(fixed_lines):
            continue

        line = fixed_lines[line_idx]
        issue_id = issue["id"]

        if issue_id == "js_var_usage":
            if "var " in line:
                fixed_lines[line_idx] = line.replace("var ", "const ", 1)
                changes.append(f"Line {line_idx+1}: Replaced 'var' with 'const'")

        elif issue_id == "js_any_type":
            fixed_lines[line_idx] = re.sub(r':\s*any\b', ': unknown', line)
            changes.append(f"Line {line_idx+1}: Replaced 'any' with 'unknown' for type safety")

    return "\n".join(fixed_lines), changes


def _generate_diff(original: str, fixed: str, file_path: str) -> str:
    """Generate a unified diff string."""
    orig_lines = original.strip().split("\n")
    fixed_lines = fixed.strip().split("\n")

    diff_lines = [
        f"--- a/{file_path}",
        f"+++ b/{file_path}",
        f"@@ -1,{len(orig_lines)} +1,{len(fixed_lines)} @@",
    ]

    i, j = 0, 0
    while i < len(orig_lines) or j < len(fixed_lines):
        if i < len(orig_lines) and j < len(fixed_lines):
            if orig_lines[i] == fixed_lines[j]:
                diff_lines.append(f" {orig_lines[i]}")
                i += 1
                j += 1
            else:
                diff_lines.append(f"-{orig_lines[i]}")
                i += 1
                if j < len(fixed_lines):
                    diff_lines.append(f"+{fixed_lines[j]}")
                    j += 1
        elif i < len(orig_lines):
            diff_lines.append(f"-{orig_lines[i]}")
            i += 1
        else:
            diff_lines.append(f"+{fixed_lines[j]}")
            j += 1

    return "\n".join(diff_lines)


async def generate_patch(state: dict[str, Any]) -> dict[str, Any]:
    """Generate a code patch based on the root cause analysis.

    Uses template mode for demo jobs and code-aware mode for editor submissions.
    """
    failure_type = state.get("failure_type", "runtime_error")
    raw_logs = state.get("raw_logs", "")

    # ── Mode 1: Demo template (for demo jobs) ──
    if failure_type in FIX_TEMPLATES and "─── Source Code ───" not in raw_logs:
        template = FIX_TEMPLATES[failure_type]
        diff_text = _generate_diff(template["original"], template["fixed"], template["file_path"])
        state["patch"] = {
            "file_path": template["file_path"],
            "original_code": template["original"],
            "fixed_code": template["fixed"],
            "diff_text": diff_text,
            "explanation": template["explanation"],
            "language": template.get("language", "python"),
        }
        return state

    # ── Mode 2: Code-aware analysis (for editor submissions) ──
    source_code = _extract_source_code(raw_logs)
    if not source_code:
        # Fallback to template if we can't find source
        template = FIX_TEMPLATES.get(failure_type, FIX_TEMPLATES.get("runtime_error", {}))
        if template:
            diff_text = _generate_diff(template["original"], template["fixed"], template["file_path"])
            state["patch"] = {
                "file_path": template.get("file_path", "unknown"),
                "original_code": template.get("original", ""),
                "fixed_code": template.get("fixed", ""),
                "diff_text": diff_text,
                "explanation": template.get("explanation", ""),
                "language": template.get("language", "python"),
            }
        return state

    # Detect language from state or logs
    language = _detect_language(raw_logs, state)

    # Analyze the code
    analysis = analyze_code(source_code, language)
    issues = analysis["issues"]

    # Store analysis results in state for downstream use
    state["code_analysis"] = analysis

    if not issues:
        # No issues found — still produce a clean report
        state["patch"] = {
            "file_path": state.get("failure_title", "untitled").split(": ")[-1] if ": " in state.get("failure_title", "") else "submitted_code",
            "original_code": source_code,
            "fixed_code": source_code,
            "diff_text": "",
            "explanation": "Static analysis found no actionable issues in the submitted code. The code follows good practices.",
            "language": language,
        }
        return state

    # Apply fixes
    if language in ("python", "py"):
        fixed_code, changes = _apply_python_fixes(source_code, issues)
    elif language in ("javascript", "js", "typescript", "ts", "tsx", "jsx"):
        fixed_code, changes = _apply_js_fixes(source_code, issues)
    else:
        fixed_code = source_code
        changes = []

    # Build file path from context
    file_path = _extract_filename(state)

    # Generate diff
    diff_text = _generate_diff(source_code, fixed_code, file_path) if source_code != fixed_code else ""

    # Build explanation from issues and changes
    explanation_parts = []
    for issue in issues[:5]:  # Top 5 issues
        sev = issue["severity"].upper()
        explanation_parts.append(f"[{sev}] Line {issue.get('line', '?')}: {issue['message']}")

    if changes:
        explanation_parts.append("")
        explanation_parts.append("Applied fixes:")
        for change in changes[:5]:
            explanation_parts.append(f"  • {change}")

    explanation = "\n".join(explanation_parts)

    state["patch"] = {
        "file_path": file_path,
        "original_code": source_code,
        "fixed_code": fixed_code,
        "diff_text": diff_text,
        "explanation": explanation,
        "language": language,
    }

    # Update root cause with analysis findings if not already set
    if not state.get("root_cause") or state.get("root_cause") == "Unable to determine specific root cause":
        top_issue = issues[0]
        state["root_cause"] = f"{top_issue['message']} (line {top_issue.get('line', '?')})"
        # Use higher confidence for real parser diagnostics
        origin = top_issue.get("origin", "heuristic")
        issue_conf = top_issue.get("confidence", 0.5)
        is_real_parser = origin in ("parser", "compiler")
        base_conf = 0.85 if top_issue["severity"] in ("error", "bug", "security") else 0.65
        if not is_real_parser:
            base_conf = min(base_conf, 0.45)  # Heuristic-only = lower confidence
        state["confidence"] = max(state.get("confidence", 0), base_conf * issue_conf)

    return state


def _extract_source_code(raw_logs: str) -> str | None:
    """Extract submitted source code from the analysis context logs."""
    # The code route wraps source between markers
    match = re.search(r"─── Source Code ───\n(.*?)─── End Source ───", raw_logs, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _detect_language(raw_logs: str, state: dict) -> str:
    """Detect programming language from context."""
    # Check the analysis log header (set by code route)
    lang_match = re.search(r"Analyzing\s+[\w.]+\s+\((\w+)\)", raw_logs)
    if lang_match:
        return normalize_language(lang_match.group(1))
    # Repo analysis format: "File: path.py (python)"
    file_match = re.search(r"File:\s+(\S+)\s+\((\w+)\)", raw_logs)
    if file_match:
        # Try to detect from filename first
        filename = file_match.group(1)
        _, confidence = router_detect_language("", filename)
        if confidence >= 0.9:
            from app.agent.parser_router import detect_language as _dl
            lang, _ = _dl("", filename)
            return lang
        return normalize_language(file_match.group(2))
    return normalize_language(state.get("language", "python"))


def _extract_filename(state: dict) -> str:
    """Extract a reasonable file name from state."""
    title = state.get("failure_title", "")

    # "Repo analysis: owner/repo — src/utils/calculate.py"
    repo_match = re.search(r"Repo analysis:.*—\s+(.+)", title)
    if repo_match:
        return repo_match.group(1).strip()

    # "Code analysis: main.python" → "main.py"
    match = re.search(r"Code analysis:\s+(.+)", title)
    if match:
        name = match.group(1).strip()
        # Normalize extensions
        name = re.sub(r'\.python$', '.py', name)
        name = re.sub(r'\.typescript$', '.ts', name)
        name = re.sub(r'\.javascript$', '.js', name)
        return name
    return "submitted_code"
