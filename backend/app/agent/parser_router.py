"""
Parser Router — Adapter-Based Language Dispatch

Routes code to the correct language-specific parser backend.
Each language handler is isolated and testable.
Fallback is always explicit — never silent.
"""

import ast
import os
import re
import shutil
import subprocess
import tempfile
import json
import structlog
from typing import Optional

from app.agent.diagnostics import (
    NormalizedIssue, ParseResult,
    make_issue_id, build_code_frame,
)

logger = structlog.get_logger("automerge.parser_router")


# ─── Language Detection ───────────────────────────────────

_EXT_MAP = {
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java", ".go": "go", ".rs": "rust",
    ".cpp": "cpp", ".cc": "cpp", ".c": "c", ".rb": "ruby",
}

_LANG_ALIASES = {
    "py": "python", "pyw": "python",
    "js": "javascript", "jsx": "javascript", "mjs": "javascript",
    "ts": "typescript", "tsx": "typescript",
}


def normalize_language(lang: str) -> str:
    """Normalize language aliases to canonical names."""
    return _LANG_ALIASES.get(lang.lower(), lang.lower())


def detect_language(code: str, filename: str = "") -> tuple[str, float]:
    """
    Detect language from filename extension first (authoritative),
    then infer from code keywords as a lower-confidence fallback.
    Returns (language, confidence).
    """
    if filename:
        _, ext = os.path.splitext(filename.lower())
        if ext in _EXT_MAP:
            return _EXT_MAP[ext], 1.0

    # Keyword scoring — conservative
    scores: dict[str, int] = {
        "python": 0, "javascript": 0, "typescript": 0,
        "java": 0, "go": 0, "rust": 0,
    }
    kw_map = {
        "python":     ["def ", "import ", "class ", "self.", "elif ", "print(", "__init__", "None", "True", "False"],
        "javascript": ["const ", "let ", "function ", "console.", "require(", "module.exports", "=>", "undefined"],
        "typescript": ["interface ", ": string", ": number", ": boolean", "readonly ", "as ", "enum ", "namespace "],
        "java":       ["public class", "System.out", "void ", "throws ", "private ", "static ", "public static"],
        "go":         ["func ", "package ", "import (", "fmt.", ":= ", "go func", "chan "],
        "rust":       ["fn ", "let mut", "impl ", "pub fn", "match ", "&self", "println!"],
    }
    for lang, keywords in kw_map.items():
        scores[lang] = sum(1 for kw in keywords if kw in code)

    best_lang = max(scores, key=lambda k: scores[k])
    best_score = scores[best_lang]

    # Require at least 2 keyword hits for non-trivial confidence
    if best_score >= 3:
        confidence = 0.80
    elif best_score == 2:
        confidence = 0.60
    else:
        confidence = 0.40
        best_lang = "python"  # conservative default

    return best_lang, confidence


# ─── Main Router ─────────────────────────────────────────

def route_and_parse(
    code: str,
    language: str,
    filename: str = "",
) -> ParseResult:
    """
    Dispatch code to the correct language-specific parser.
    Returns a ParseResult with normalized diagnostics.
    """
    lang = normalize_language(language)
    is_jsx = filename.endswith(".jsx") if filename else False
    is_tsx = filename.endswith(".tsx") if filename else False

    logger.info("parser_router.dispatch", language=lang, filename=filename or "(none)")

    if lang == "python":
        return _parse_python(code, filename or "code.py")
    elif lang == "javascript":
        return _parse_javascript(code, filename or "code.js", is_jsx=is_jsx)
    elif lang == "typescript":
        return _parse_typescript(code, filename or "code.ts", is_tsx=is_tsx)
    else:
        # Unsupported language — return explicit empty fallback
        return ParseResult(
            language=lang,
            parser_name="none",
            backend_name="unsupported",
            issues=[],
            parse_success=False,
            is_fallback=True,
            fallback_reason=f"No parser available for language '{lang}'",
            parser_confidence=0.0,
        )


# ─── Python Parser (compile + ast) ───────────────────────

def _parse_python(code: str, filename: str = "code.py") -> ParseResult:
    """
    Parse Python using compile() for syntax + ast.parse() for semantic checks.
    Both are always available in any Python runtime — no external deps.
    compile() is authoritative: it uses the same parser CPython uses to run code.
    """
    source_lines = code.splitlines()
    issues: list[NormalizedIssue] = []

    # Phase 1: Syntax via compile() — authoritative
    try:
        compile(code, filename, "exec")
    except SyntaxError as e:
        line = e.lineno or 0
        col = e.offset or 0
        src = (source_lines[line - 1] if line and line <= len(source_lines) else "") or (e.text or "").rstrip()
        frame = build_code_frame(source_lines, line, col)
        issues.append(NormalizedIssue(
            id=make_issue_id("python", "syntax", line, e.msg),
            language="python",
            severity="error",
            category="syntax",
            message=f"SyntaxError: {e.msg}",
            explanation=(
                f"Python cannot parse this file. Syntax error at line {line}"
                + (f", column {col}" if col else "") + "."
            ),
            line=line,
            column=col,
            end_line=getattr(e, "end_lineno", line) or line,
            end_column=getattr(e, "end_offset", col) or col,
            source_line=src,
            code_frame=frame,
            fix_hint=f"Fix the syntax on line {line}: {(e.text or '').strip()}",
            confidence=1.0,
            origin="parser",
            parser_name="cpython_compile",
            backend_name="Python compile()",
            raw_diagnostic={"msg": e.msg, "lineno": e.lineno, "offset": e.offset, "text": e.text},
        ))
        # Syntax error means AST walk is impossible — stop here
        return ParseResult(
            language="python",
            parser_name="cpython_compile",
            backend_name="Python compile()",
            issues=issues,
            parse_success=True,
            is_fallback=False,
            parser_confidence=1.0,
        )
    except Exception as e:
        logger.error("python_compile.unexpected_error", error=str(e))
        return ParseResult(
            language="python", parser_name="cpython_compile",
            backend_name="Python compile()", issues=[],
            parse_success=False, is_fallback=True,
            fallback_reason=f"compile() raised unexpected error: {e}",
            parser_confidence=0.2,
        )

    # Phase 2: AST semantic checks (syntax is clean)
    try:
        tree = ast.parse(code, filename=filename)
        issues.extend(_python_ast_semantic_checks(tree, source_lines))
        # Phase 3: Concurrency / thread-safety checks
        try:
            from app.agent.concurrency_analyzer import analyze_concurrency, check_thread_join_at_module_level
            issues.extend(analyze_concurrency(tree, source_lines, filename))
            issues.extend(check_thread_join_at_module_level(tree, source_lines))
        except Exception as ce:
            logger.warning("python_concurrency.error", error=str(ce))
    except Exception as e:
        logger.warning("python_ast.error", error=str(e))

    return ParseResult(
        language="python",
        parser_name="cpython_ast",
        backend_name="Python ast.parse() + compile() + Concurrency Analyzer",
        issues=issues,
        parse_success=True,
        is_fallback=False,
        parser_confidence=1.0,
    )


def _python_ast_semantic_checks(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    """
    AST-proven semantic / quality checks for Python.
    Only flags things the AST can structurally guarantee — no guessing.
    """
    issues = []

    for node in ast.walk(tree):

        # Bare except — AST-exact: ExceptHandler with type=None
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
            issues.append(NormalizedIssue(
                id=make_issue_id("python", "runtime-risk", node.lineno, "bare_except"),
                language="python",
                severity="warning",
                category="runtime-risk",
                message="Bare except: clause catches all exceptions including SystemExit and KeyboardInterrupt",
                explanation=(
                    "A bare `except:` swallows every exception including KeyboardInterrupt "
                    "and SystemExit. This hides bugs and makes the program hard to stop."
                ),
                line=node.lineno,
                column=node.col_offset,
                source_line=src,
                code_frame=build_code_frame(source_lines, node.lineno),
                fix_hint="Replace `except:` with `except Exception as e:`",
                confidence=1.0,
                origin="parser",
                parser_name="cpython_ast",
                backend_name="Python ast.parse()",
            ))

        # Mutable default arguments — AST-exact: List/Dict/Set as default
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_defaults = node.args.defaults + [d for d in node.args.kw_defaults if d is not None]
            for default in all_defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    kind = type(default).__name__.lower()
                    src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
                    issues.append(NormalizedIssue(
                        id=make_issue_id("python", "semantic", node.lineno, f"mutable_default_{node.name}"),
                        language="python",
                        severity="bug",
                        category="semantic",
                        message=f"Mutable default argument ({kind}) in '{node.name}' — shared across all calls",
                        explanation=(
                            "Default argument values are created once at function definition. "
                            "A mutable default (list/dict/set) accumulates state across calls."
                        ),
                        line=node.lineno,
                        column=node.col_offset,
                        source_line=src,
                        code_frame=build_code_frame(source_lines, node.lineno),
                        fix_hint="Use None as default, then initialize inside the body: `if param is None: param = []`",
                        confidence=1.0,
                        origin="parser",
                        parser_name="cpython_ast",
                        backend_name="Python ast.parse()",
                    ))

        # == None comparison — AST-exact
        if isinstance(node, ast.Compare):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(comp, ast.Constant) and comp.value is None:
                    if isinstance(op, ast.Eq):
                        src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
                        issues.append(NormalizedIssue(
                            id=make_issue_id("python", "style", node.lineno, "none_eq_comparison"),
                            language="python",
                            severity="warning",
                            category="style",
                            message="Use `is None` instead of `== None`",
                            explanation="`None` is a singleton. `is None` is idiomatic and avoids custom `__eq__` confusion.",
                            line=node.lineno,
                            column=node.col_offset,
                            source_line=src,
                            code_frame=build_code_frame(source_lines, node.lineno),
                            fix_hint="Replace `== None` with `is None`",
                            confidence=1.0,
                            origin="parser",
                            parser_name="cpython_ast",
                            backend_name="Python ast.parse()",
                        ))
                    elif isinstance(op, ast.NotEq):
                        src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
                        issues.append(NormalizedIssue(
                            id=make_issue_id("python", "style", node.lineno, "none_ne_comparison"),
                            language="python",
                            severity="warning",
                            category="style",
                            message="Use `is not None` instead of `!= None`",
                            explanation="`None` is a singleton. `is not None` is the correct Python idiom.",
                            line=node.lineno,
                            column=node.col_offset,
                            source_line=src,
                            code_frame=build_code_frame(source_lines, node.lineno),
                            fix_hint="Replace `!= None` with `is not None`",
                            confidence=1.0,
                            origin="parser",
                            parser_name="cpython_ast",
                            backend_name="Python ast.parse()",
                        ))

        # eval() / exec() call — AST-exact
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
                src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
                is_eval = func.id == "eval"
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "security", node.lineno, f"{func.id}_usage"),
                    language="python",
                    severity="security",
                    category="security",
                    message=f"{func.id}() executes arbitrary code — remote code execution risk",
                    explanation=(
                        f"If user-controlled data reaches {func.id}(), an attacker can run arbitrary Python code."
                        + (" Use `ast.literal_eval()` for safe literal parsing." if is_eval else "")
                    ),
                    line=node.lineno,
                    column=node.col_offset,
                    source_line=src,
                    code_frame=build_code_frame(source_lines, node.lineno),
                    fix_hint=(
                        "Use `ast.literal_eval()` for safe literal parsing, or a proper schema parser"
                        if is_eval else
                        "Avoid exec(). Use importlib, getattr(), or explicit dispatch instead."
                    ),
                    confidence=1.0,
                    origin="parser",
                    parser_name="cpython_ast",
                    backend_name="Python ast.parse()",
                ))

        # Wildcard import — AST-exact: ImportFrom with names=[alias(name='*')]
        if isinstance(node, ast.ImportFrom):
            if any(alias.name == "*" for alias in node.names):
                src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "quality", node.lineno, "wildcard_import"),
                    language="python",
                    severity="warning",
                    category="quality",
                    message=f"Wildcard import `from {node.module or '?'} import *` pollutes namespace",
                    explanation=(
                        "Wildcard imports dump all names into your namespace, making it impossible to tell "
                        "where a name came from. This can also shadow builtins silently."
                    ),
                    line=node.lineno,
                    column=node.col_offset,
                    source_line=src,
                    code_frame=build_code_frame(source_lines, node.lineno),
                    fix_hint=f"Import specific names: `from {node.module or '?'} import name1, name2`",
                    confidence=1.0,
                    origin="parser",
                    parser_name="cpython_ast",
                    backend_name="Python ast.parse()",
                ))

        # Raising a string literal (Python 2 pattern) — AST-exact
        if isinstance(node, ast.Raise) and node.exc is not None:
            if isinstance(node.exc, ast.Constant) and isinstance(node.exc.value, str):
                src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "semantic", node.lineno, "raise_string"),
                    language="python",
                    severity="error",
                    category="semantic",
                    message="Raising a string literal — use `raise Exception('...')` instead",
                    explanation=(
                        "In Python 3, `raise 'error'` does not work. You must raise an Exception "
                        "subclass instance: `raise ValueError('error message')`."
                    ),
                    line=node.lineno,
                    column=node.col_offset,
                    source_line=src,
                    code_frame=build_code_frame(source_lines, node.lineno),
                    fix_hint="Use `raise Exception('message')` or a specific exception class",
                    confidence=1.0,
                    origin="parser",
                    parser_name="cpython_ast",
                    backend_name="Python ast.parse()",
                ))

        # assert with a tuple (always True) — AST-exact
        if isinstance(node, ast.Assert) and isinstance(node.test, ast.Tuple):
            if len(node.test.elts) > 0:
                src = source_lines[node.lineno - 1] if node.lineno <= len(source_lines) else ""
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "semantic", node.lineno, "assert_tuple"),
                    language="python",
                    severity="bug",
                    category="semantic",
                    message="assert with a tuple is always True — did you mean `assert condition, 'message'`?",
                    explanation=(
                        "`assert (x, 'msg')` asserts a non-empty tuple which is always truthy. "
                        "The correct form is `assert x, 'msg'` (no parentheses around both)."
                    ),
                    line=node.lineno,
                    column=node.col_offset,
                    source_line=src,
                    code_frame=build_code_frame(source_lines, node.lineno),
                    fix_hint="Remove the tuple parentheses: `assert condition, 'message'`",
                    confidence=1.0,
                    origin="parser",
                    parser_name="cpython_ast",
                    backend_name="Python ast.parse()",
                ))

    return issues


# ─── JavaScript Parser (node --check) ────────────────────

_node_path: Optional[str] = None
_node_checked = False


def _get_node() -> Optional[str]:
    global _node_path, _node_checked
    if not _node_checked:
        _node_path = shutil.which("node")
        _node_checked = True
    return _node_path


def _parse_javascript(code: str, filename: str = "code.js", is_jsx: bool = False) -> ParseResult:
    """
    Parse JavaScript using `node --check` — V8-backed, authoritative.
    If Node is unavailable, returns an explicit fallback result.
    Note: JSX syntax requires a transformer; node --check only handles plain JS.
    """
    node = _get_node()
    if not node:
        return ParseResult(
            language="javascript",
            parser_name="none",
            backend_name="unavailable",
            issues=[],
            parse_success=False,
            is_fallback=True,
            fallback_reason="Node.js not found on PATH — install Node.js to enable JS parsing",
            parser_confidence=0.0,
        )

    source_lines = code.splitlines()
    suffix = ".js"  # node --check doesn't support JSX natively

    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            [node, "--check", tmp_path],
            capture_output=True, text=True, timeout=10,
        )

        if proc.returncode == 0:
            return ParseResult(
                language="javascript",
                parser_name="node_check",
                backend_name="Node.js --check (V8)",
                issues=[],
                parse_success=True,
                is_fallback=False,
                parser_confidence=1.0,
            )

        issues = _parse_node_stderr(proc.stderr, source_lines, tmp_path)
        return ParseResult(
            language="javascript",
            parser_name="node_check",
            backend_name="Node.js --check (V8)",
            issues=issues,
            parse_success=True,
            is_fallback=False,
            parser_confidence=1.0,
        )

    except subprocess.TimeoutExpired:
        return ParseResult(
            language="javascript", parser_name="node_check",
            backend_name="Node.js --check (V8)", issues=[],
            parse_success=False, is_fallback=True,
            fallback_reason="node --check timed out after 10s", parser_confidence=0.2,
        )
    except Exception as e:
        return ParseResult(
            language="javascript", parser_name="node_check",
            backend_name="Node.js --check (V8)", issues=[],
            parse_success=False, is_fallback=True,
            fallback_reason=f"node --check error: {e}", parser_confidence=0.2,
        )
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _parse_node_stderr(stderr: str, source_lines: list[str], tmp_path: str) -> list[NormalizedIssue]:
    """Parse `node --check` stderr into NormalizedIssue objects."""
    issues = []
    escaped = re.escape(tmp_path)

    # Node format: /tmp/xxx.js:LINE\nCODE_LINE\n   ^\nSyntaxError: message
    pattern = re.compile(
        r'(?:' + escaped + r'|[^\n]+):(\d+)\n(.*?)\n\s*\^+\s*\n(SyntaxError|ReferenceError|TypeError|Error): (.+)',
        re.DOTALL,
    )
    for m in pattern.finditer(stderr):
        lineno = int(m.group(1))
        err_type = m.group(3)
        err_msg = m.group(4).strip()
        src = source_lines[lineno - 1] if lineno <= len(source_lines) else m.group(2)
        issues.append(NormalizedIssue(
            id=make_issue_id("javascript", "syntax", lineno, err_msg),
            language="javascript",
            severity="error",
            category="syntax",
            message=f"{err_type}: {err_msg}",
            explanation=f"V8/Node.js rejected this code: {err_type} at line {lineno}.",
            line=lineno,
            column=0,
            source_line=src,
            code_frame=build_code_frame(source_lines, lineno),
            fix_hint=f"Fix the {err_type} on line {lineno}",
            confidence=1.0,
            origin="parser",
            parser_name="node_check",
            backend_name="Node.js --check (V8)",
            raw_diagnostic={"type": err_type, "message": err_msg},
        ))

    # Fallback: simpler line scan if pattern didn't match
    if not issues:
        for line_text in stderr.splitlines():
            for err_type in ("SyntaxError:", "ReferenceError:", "TypeError:"):
                if err_type in line_text:
                    msg = line_text[line_text.index(err_type):].strip()
                    issues.append(NormalizedIssue(
                        id=make_issue_id("javascript", "syntax", 0, msg),
                        language="javascript",
                        severity="error",
                        category="syntax",
                        message=msg,
                        explanation="Node.js reported a parse error (exact location unavailable).",
                        line=0,
                        confidence=0.8,
                        origin="parser",
                        parser_name="node_check",
                        backend_name="Node.js --check (V8)",
                        raw_diagnostic={"raw": stderr[:500]},
                    ))
                    break

    return issues


# ─── TypeScript Parser (tsc --noEmit) ────────────────────

_tsc_path: Optional[str] = None
_tsc_checked = False


def _get_tsc() -> Optional[str]:
    global _tsc_path, _tsc_checked
    if not _tsc_checked:
        _tsc_path = shutil.which("tsc")
        _tsc_checked = True
    return _tsc_path


def _parse_typescript(code: str, filename: str = "code.ts", is_tsx: bool = False) -> ParseResult:
    """
    Parse TypeScript using tsc --noEmit.
    If tsc is unavailable, returns explicit fallback (not a fake result).
    """
    tsc = _get_tsc()
    if not tsc:
        return ParseResult(
            language="typescript",
            parser_name="none",
            backend_name="unavailable",
            issues=[],
            parse_success=False,
            is_fallback=True,
            fallback_reason=(
                "TypeScript compiler (tsc) not found on PATH. "
                "Install it: npm install -g typescript"
            ),
            parser_confidence=0.0,
        )

    source_lines = code.splitlines()
    suffix = ".tsx" if is_tsx else ".ts"

    with tempfile.TemporaryDirectory() as tmpdir:
        code_file = os.path.join(tmpdir, f"code{suffix}")
        tsconfig_file = os.path.join(tmpdir, "tsconfig.json")

        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code)

        tsconfig = {
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "node",
                "strict": True,
                "noEmit": True,
                "skipLibCheck": True,
                "allowJs": True,
                "allowSyntheticDefaultImports": True,
                "esModuleInterop": True,
            },
            "include": [f"code{suffix}"],
        }
        if is_tsx:
            tsconfig["compilerOptions"]["jsx"] = "react"

        with open(tsconfig_file, "w") as f:
            json.dump(tsconfig, f)

        try:
            proc = subprocess.run(
                [tsc, "--noEmit", "--pretty", "false", "--project", tsconfig_file],
                capture_output=True, text=True, timeout=30, cwd=tmpdir,
            )
            raw_output = proc.stdout + proc.stderr
            issues = _parse_tsc_output(raw_output, source_lines, code_file)
            return ParseResult(
                language="typescript",
                parser_name="tsc",
                backend_name="TypeScript Compiler (tsc)",
                issues=issues,
                parse_success=True,
                is_fallback=False,
                parser_confidence=1.0,
            )
        except subprocess.TimeoutExpired:
            return ParseResult(
                language="typescript", parser_name="tsc",
                backend_name="TypeScript Compiler (tsc)", issues=[],
                parse_success=False, is_fallback=True,
                fallback_reason="tsc timed out after 30s", parser_confidence=0.2,
            )
        except Exception as e:
            return ParseResult(
                language="typescript", parser_name="tsc",
                backend_name="TypeScript Compiler (tsc)", issues=[],
                parse_success=False, is_fallback=True,
                fallback_reason=f"tsc error: {e}", parser_confidence=0.2,
            )


def _parse_tsc_output(output: str, source_lines: list[str], tmp_file: str) -> list[NormalizedIssue]:
    """Parse tsc --pretty false output into NormalizedIssue objects."""
    issues = []
    # Format: path/code.ts(LINE,COL): error|warning TS####: message
    pattern = re.compile(r'[^\n(]+\((\d+),(\d+)\):\s+(error|warning)\s+TS(\d+):\s+(.+)')
    for m in pattern.finditer(output):
        lineno, col = int(m.group(1)), int(m.group(2))
        level, ts_code, msg = m.group(3), m.group(4), m.group(5).strip()
        severity = "error" if level == "error" else "warning"
        category = _ts_code_category(ts_code)
        src = source_lines[lineno - 1] if lineno <= len(source_lines) else ""
        issues.append(NormalizedIssue(
            id=make_issue_id("typescript", category, lineno, msg),
            language="typescript",
            severity=severity,
            category=category,
            message=f"TS{ts_code}: {msg}",
            explanation=f"TypeScript compiler error TS{ts_code} at line {lineno}:{col}.",
            line=lineno,
            column=col,
            source_line=src,
            code_frame=build_code_frame(source_lines, lineno, col),
            fix_hint=f"Fix TypeScript error TS{ts_code} on line {lineno}",
            confidence=1.0,
            origin="compiler",
            parser_name="tsc",
            backend_name="TypeScript Compiler (tsc)",
            raw_diagnostic={"ts_code": ts_code, "level": level},
        ))
    return issues


def _ts_code_category(ts_code: str) -> str:
    code = int(ts_code) if ts_code.isdigit() else 0
    if 1000 <= code <= 1999:
        return "syntax"
    elif 2000 <= code <= 2999:
        return "semantic"
    elif 4000 <= code <= 4999:
        return "type"
    return "semantic"
