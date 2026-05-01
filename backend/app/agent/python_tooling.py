"""
Python Optional Tooling — Layer 3

Wraps calls to pylint and bandit (if installed) as optional corroborating checks.
Each tool runs in a subprocess with timeout. Results are normalized to NormalizedIssue.

If a tool is not installed, it gracefully skips. No failure.
These are supplementary — never the primary source of truth.
"""

import json
import os
import shutil
import subprocess
import tempfile
import structlog
from typing import Optional

from app.agent.diagnostics import NormalizedIssue, make_issue_id, build_code_frame

logger = structlog.get_logger("automerge.python_tooling")

_PARSER = "external_tool"


def run_optional_tooling(
    code: str,
    filename: str,
    existing_lines: set[int],
) -> list[NormalizedIssue]:
    """Run optional Python tooling checks. Returns NormalizedIssue list.
    Deduplicates against existing_lines to avoid double-reporting.
    Runs: bandit → pylint → flake8 → mypy (all optional).
    """
    issues: list[NormalizedIssue] = []
    _runners = [
        ("bandit", _run_bandit),
        ("pylint", _run_pylint),
        ("flake8", _run_flake8),
        ("mypy", _run_mypy),
    ]
    for name, runner in _runners:
        try:
            issues.extend(runner(code, filename, existing_lines))
        except Exception as e:
            logger.debug(f"python_tooling.{name}_skip", reason=str(e))
    return issues


def _run_bandit(code: str, filename: str, existing_lines: set[int]) -> list[NormalizedIssue]:
    """Run bandit security scanner if available."""
    bandit = shutil.which("bandit")
    if not bandit:
        return []

    source_lines = code.splitlines()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [bandit, "-f", "json", "-q", "--severity-level", "medium", tmp_path],
            capture_output=True, text=True, timeout=15,
        )
        raw = proc.stdout.strip()
        if not raw:
            return []

        data = json.loads(raw)
        results = data.get("results", [])
        issues = []
        for r in results[:10]:  # Cap at 10
            lineno = r.get("line_number", 0)
            if lineno in existing_lines:
                continue
            sev = r.get("issue_severity", "LOW")
            severity = "security" if sev in ("HIGH", "MEDIUM") else "warning"
            issues.append(NormalizedIssue(
                id=make_issue_id("python", "security", lineno, r.get("test_id", "")),
                language="python",
                severity=severity,
                category="security",
                message=f"[{r.get('test_id', '')}] {r.get('issue_text', '')}",
                explanation=r.get("more_info", ""),
                line=lineno,
                column=r.get("col_offset", 0),
                source_line=_src(source_lines, lineno),
                code_frame=build_code_frame(source_lines, lineno) if lineno else "",
                fix_hint="Review the security issue and apply the recommended fix",
                confidence=0.85,
                origin="linter",
                parser_name=f"bandit_{r.get('test_id', '')}",
                backend_name="Bandit Security Scanner",
            ))
        return issues
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _run_pylint(code: str, filename: str, existing_lines: set[int]) -> list[NormalizedIssue]:
    """Run pylint if available. Only keeps error/warning level messages."""
    pylint = shutil.which("pylint")
    if not pylint:
        return []

    source_lines = code.splitlines()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [
                pylint, "--output-format=json",
                "--disable=C,R",  # Disable convention and refactor — too noisy
                "--max-line-length=120",
                tmp_path,
            ],
            capture_output=True, text=True, timeout=20,
        )
        raw = proc.stdout.strip()
        if not raw:
            return []

        data = json.loads(raw)
        issues = []
        for msg in data[:10]:
            lineno = msg.get("line", 0)
            if lineno in existing_lines:
                continue
            msg_type = msg.get("type", "")
            if msg_type not in ("error", "warning", "fatal"):
                continue
            severity = "error" if msg_type in ("error", "fatal") else "warning"
            sym = msg.get("symbol", "")
            issues.append(NormalizedIssue(
                id=make_issue_id("python", "quality", lineno, sym),
                language="python",
                severity=severity,
                category="quality",
                message=f"[{sym}] {msg.get('message', '')}",
                explanation=msg.get("message-id", ""),
                line=lineno,
                column=msg.get("column", 0),
                source_line=_src(source_lines, lineno),
                code_frame=build_code_frame(source_lines, lineno) if lineno else "",
                fix_hint=f"Fix pylint {msg_type}: {sym}",
                confidence=0.80,
                origin="linter",
                parser_name=f"pylint_{sym}",
                backend_name="Pylint",
            ))
        return issues
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _run_flake8(code: str, filename: str, existing_lines: set[int]) -> list[NormalizedIssue]:
    """Run flake8 if available. Focuses on errors and warnings only."""
    flake8 = shutil.which("flake8")
    if not flake8:
        return []

    source_lines = code.splitlines()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [
                flake8,
                "--format=%(row)d:%(col)d:%(code)s:%(text)s",
                "--select=E,W,F",  # Errors, Warnings, pyFlakes
                "--max-line-length=120",
                tmp_path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        raw = proc.stdout.strip()
        if not raw:
            return []

        issues = []
        for line_str in raw.splitlines()[:10]:
            parts = line_str.split(":", 3)
            if len(parts) < 4:
                continue
            try:
                lineno = int(parts[0])
            except ValueError:
                continue
            if lineno in existing_lines:
                continue
            col = int(parts[1]) if parts[1].isdigit() else 0
            err_code = parts[2].strip()
            message = parts[3].strip()
            severity = "error" if err_code.startswith(("E", "F")) else "warning"
            issues.append(NormalizedIssue(
                id=make_issue_id("python", "quality", lineno, err_code),
                language="python",
                severity=severity,
                category="quality",
                message=f"[{err_code}] {message}",
                explanation=f"flake8 rule {err_code}",
                line=lineno,
                column=col,
                source_line=_src(source_lines, lineno),
                code_frame=build_code_frame(source_lines, lineno) if lineno else "",
                fix_hint=f"Fix flake8 {err_code}: {message}",
                confidence=0.80,
                origin="linter",
                parser_name=f"flake8_{err_code}",
                backend_name="Flake8",
            ))
        return issues
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _run_mypy(code: str, filename: str, existing_lines: set[int]) -> list[NormalizedIssue]:
    """Run mypy if available. Only reports errors (not notes)."""
    mypy = shutil.which("mypy")
    if not mypy:
        return []

    source_lines = code.splitlines()
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [
                mypy, "--no-color-output", "--no-error-summary",
                "--ignore-missing-imports",
                "--no-incremental",
                tmp_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        raw = proc.stdout.strip()
        if not raw:
            return []

        issues = []
        for line_str in raw.splitlines()[:10]:
            # Format: file.py:line: error: message  [code]
            if ": error:" not in line_str:
                continue
            parts = line_str.split(":", 3)
            if len(parts) < 4:
                continue
            try:
                lineno = int(parts[1].strip())
            except ValueError:
                continue
            if lineno in existing_lines:
                continue
            message = parts[3].strip()
            if message.startswith("error:"):
                message = message[6:].strip()
            issues.append(NormalizedIssue(
                id=make_issue_id("python", "type", lineno, message[:30]),
                language="python",
                severity="error",
                category="type",
                message=f"[mypy] {message}",
                explanation="Type error detected by mypy static type checker",
                line=lineno,
                column=0,
                source_line=_src(source_lines, lineno),
                code_frame=build_code_frame(source_lines, lineno) if lineno else "",
                fix_hint="Fix the type annotation or value to match the expected type",
                confidence=0.85,
                origin="linter",
                parser_name="mypy",
                backend_name="Mypy Type Checker",
            ))
        return issues
    except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
        return []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _src(source_lines: list[str], lineno: int) -> str:
    return source_lines[lineno - 1] if 0 < lineno <= len(source_lines) else ""
