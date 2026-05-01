"""
Python Deep Analyzer — Layer 2b

Extended AST-proven semantic checks that go beyond the base parser_router checks.
Every check here is structurally proven by the AST — no guessing, no regex.

Called from parser_router._parse_python() after the base semantic checks pass.
"""

import ast
import builtins
import structlog
from typing import Optional

from app.agent.diagnostics import NormalizedIssue, make_issue_id, build_code_frame

logger = structlog.get_logger("automerge.python_deep_analyzer")

# Builtins that are commonly shadowed by accident
_SHADOW_BUILTINS = frozenset({
    "list", "dict", "set", "str", "int", "float", "bool", "tuple", "type",
    "id", "input", "print", "open", "map", "filter", "len", "range",
    "min", "max", "sum", "abs", "round", "sorted", "reversed",
    "enumerate", "zip", "any", "all", "hash", "super", "property",
    "classmethod", "staticmethod", "object", "format", "vars", "dir",
    "iter", "next", "repr", "bytes", "complex", "frozenset", "memoryview",
})

_PARSER = "cpython_ast_deep"
_BACKEND = "Python AST Deep Analyzer"


def run_deep_checks(
    tree: ast.AST,
    source_lines: list[str],
    filename: str = "",
) -> list[NormalizedIssue]:
    """Run all deep AST checks. Returns NormalizedIssue list."""
    issues: list[NormalizedIssue] = []
    try:
        issues.extend(_check_shadowed_builtins(tree, source_lines))
        issues.extend(_check_unreachable_code(tree, source_lines))
        issues.extend(_check_os_system(tree, source_lines))
        issues.extend(_check_shell_injection(tree, source_lines))
        issues.extend(_check_open_without_context(tree, source_lines))
        issues.extend(_check_fstring_no_placeholder(tree, source_lines))
        issues.extend(_check_bool_comparison(tree, source_lines))
        issues.extend(_check_init_return(tree, source_lines))
        issues.extend(_check_yield_in_init(tree, source_lines))
        issues.extend(_check_duplicate_dict_keys(tree, source_lines))
        issues.extend(_check_unused_imports(tree, source_lines))
        issues.extend(_check_pickle_loads(tree, source_lines))
        issues.extend(_check_bare_raise_in_except(tree, source_lines))
        issues.extend(_check_empty_except_pass(tree, source_lines))
    except Exception as e:
        logger.warning("python_deep_analyzer.error", error=str(e))
    return issues


def _src(source_lines: list[str], lineno: int) -> str:
    return source_lines[lineno - 1] if 0 < lineno <= len(source_lines) else ""


# ─── Check: Shadowed builtins ────────────────────────────

def _check_shadowed_builtins(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in _SHADOW_BUILTINS:
                    lineno = node.lineno
                    issues.append(NormalizedIssue(
                        id=make_issue_id("python", "semantic", lineno, f"shadow_{target.id}"),
                        language="python", severity="warning", category="semantic",
                        message=f"Assignment shadows builtin `{target.id}` — original builtin is now inaccessible",
                        explanation=f"`{target.id}` is a Python builtin. Assigning to it hides the original, which can cause confusing bugs later when code tries to use the builtin.",
                        line=lineno, column=target.col_offset,
                        source_line=_src(source_lines, lineno),
                        code_frame=build_code_frame(source_lines, lineno),
                        fix_hint=f"Rename the variable to avoid shadowing: e.g., `{target.id}_val` or `my_{target.id}`",
                        confidence=0.95, origin="parser",
                        parser_name=_PARSER, backend_name=_BACKEND,
                    ))
    return issues


# ─── Check: Unreachable code after return/raise/break/continue ─

def _check_unreachable_code(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    _TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)

    def _check_body(body: list[ast.stmt]):
        for i, stmt in enumerate(body):
            if isinstance(stmt, _TERMINATORS) and i + 1 < len(body):
                next_stmt = body[i + 1]
                lineno = next_stmt.lineno
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "semantic", lineno, "unreachable"),
                    language="python", severity="warning", category="semantic",
                    message=f"Unreachable code after `{type(stmt).__name__.lower()}` statement",
                    explanation="This code can never execute because there is a return/raise/break/continue statement before it.",
                    line=lineno, column=next_stmt.col_offset,
                    source_line=_src(source_lines, lineno),
                    code_frame=build_code_frame(source_lines, lineno),
                    fix_hint="Remove the unreachable code or move it before the terminating statement",
                    confidence=0.95, origin="parser",
                    parser_name=_PARSER, backend_name=_BACKEND,
                ))
                break  # Only flag first unreachable stmt per block

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _check_body(node.body)
        if isinstance(node, ast.If):
            _check_body(node.body)
            _check_body(node.orelse)
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            _check_body(node.body)
        if isinstance(node, ast.With):
            _check_body(node.body)
        if isinstance(node, ast.Try):
            _check_body(node.body)
            for handler in node.handlers:
                _check_body(handler.body)
            _check_body(node.orelse)
            _check_body(node.finalbody)
    return issues


# ─── Check: os.system() ─────────────────────────────────

def _check_os_system(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and node.func.value.id == "os"
                    and node.func.attr == "system"):
                lineno = node.lineno
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "security", lineno, "os_system"),
                    language="python", severity="security", category="security",
                    message="`os.system()` executes shell commands — command injection risk",
                    explanation="os.system() runs commands through the shell. If any user input reaches the command string, an attacker can inject arbitrary shell commands.",
                    line=lineno, column=node.col_offset,
                    source_line=_src(source_lines, lineno),
                    code_frame=build_code_frame(source_lines, lineno),
                    fix_hint="Use `subprocess.run([cmd, arg1, arg2], check=True)` with a list (no shell)",
                    confidence=0.95, origin="parser",
                    parser_name=_PARSER, backend_name=_BACKEND,
                ))
    return issues


# ─── Check: subprocess with shell=True ───────────────────

def _check_shell_injection(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    _RISKY = {"call", "Popen", "run", "check_output", "check_call"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_subprocess = (
            (isinstance(func, ast.Attribute) and func.attr in _RISKY
             and isinstance(func.value, ast.Name) and func.value.id == "subprocess")
        )
        if not is_subprocess:
            continue
        for kw in node.keywords:
            if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                lineno = node.lineno
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "security", lineno, "shell_true"),
                    language="python", severity="security", category="security",
                    message=f"`subprocess.{func.attr}(shell=True)` — command injection risk",
                    explanation="Using shell=True passes the command through the system shell, enabling injection if any part comes from user input.",
                    line=lineno, column=node.col_offset,
                    source_line=_src(source_lines, lineno),
                    code_frame=build_code_frame(source_lines, lineno),
                    fix_hint="Use `shell=False` (default) and pass command as a list: `['cmd', 'arg1']`",
                    confidence=0.95, origin="parser",
                    parser_name=_PARSER, backend_name=_BACKEND,
                ))
    return issues


# ─── Check: open() without context manager ──────────────

def _check_open_without_context(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    # Collect lines where open() is used inside `with`
    with_open_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.With):
            for item in node.items:
                if isinstance(item.context_expr, ast.Call):
                    fn = item.context_expr.func
                    if (isinstance(fn, ast.Name) and fn.id == "open") or \
                       (isinstance(fn, ast.Attribute) and fn.attr == "open"):
                        with_open_lines.add(item.context_expr.lineno)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                fn = node.value.func
                is_open = (isinstance(fn, ast.Name) and fn.id == "open")
                if is_open and node.value.lineno not in with_open_lines:
                    lineno = node.lineno
                    issues.append(NormalizedIssue(
                        id=make_issue_id("python", "runtime-risk", lineno, "open_no_with"),
                        language="python", severity="warning", category="runtime-risk",
                        message="`open()` called without a context manager — file may not be closed on error",
                        explanation="If an exception occurs before `.close()` is called, the file handle leaks. Using `with open(...) as f:` guarantees cleanup.",
                        line=lineno, column=node.col_offset,
                        source_line=_src(source_lines, lineno),
                        code_frame=build_code_frame(source_lines, lineno),
                        fix_hint="Use `with open(...) as f:` instead of `f = open(...)`",
                        confidence=0.90, origin="parser",
                        parser_name=_PARSER, backend_name=_BACKEND,
                    ))
    return issues


# ─── Check: f-string without placeholders ────────────────

def _check_fstring_no_placeholder(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            # f-string with no FormattedValue nodes = no placeholders
            has_placeholder = any(isinstance(v, ast.FormattedValue) for v in node.values)
            if not has_placeholder:
                lineno = node.lineno
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "quality", lineno, "fstring_no_expr"),
                    language="python", severity="info", category="quality",
                    message="f-string has no placeholders — use a regular string instead",
                    explanation="An f-string without `{...}` expressions is just a normal string with unnecessary overhead.",
                    line=lineno, column=node.col_offset,
                    source_line=_src(source_lines, lineno),
                    code_frame=build_code_frame(source_lines, lineno),
                    fix_hint="Remove the `f` prefix to make it a regular string",
                    confidence=1.0, origin="parser",
                    parser_name=_PARSER, backend_name=_BACKEND,
                ))
    return issues


# ─── Check: Comparison with True/False using == ──────────

def _check_bool_comparison(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(comp, ast.Constant) and isinstance(comp.value, bool):
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        val = comp.value
                        lineno = node.lineno
                        if isinstance(op, ast.Eq):
                            fix = f"Use `if x:` instead of `if x == {val}`" if val else f"Use `if not x:` instead of `if x == {val}`"
                        else:
                            fix = f"Use `if not x:` instead of `if x != {val}`" if val else f"Use `if x:` instead of `if x != {val}`"
                        issues.append(NormalizedIssue(
                            id=make_issue_id("python", "style", lineno, f"bool_cmp_{val}"),
                            language="python", severity="info", category="style",
                            message=f"Comparison with `{val}` using `{'==' if isinstance(op, ast.Eq) else '!='}` — use direct truthiness check",
                            explanation=f"Comparing to `{val}` with `==` is redundant. Use `if x:` or `if not x:` for cleaner, more Pythonic code.",
                            line=lineno, column=node.col_offset,
                            source_line=_src(source_lines, lineno),
                            code_frame=build_code_frame(source_lines, lineno),
                            fix_hint=fix,
                            confidence=0.95, origin="parser",
                            parser_name=_PARSER, backend_name=_BACKEND,
                        ))
    return issues


# ─── Check: __init__ returning a value ───────────────────

def _check_init_return(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child.value is not None:
                    # Allow `return None` explicitly
                    if isinstance(child.value, ast.Constant) and child.value.value is None:
                        continue
                    lineno = child.lineno
                    issues.append(NormalizedIssue(
                        id=make_issue_id("python", "semantic", lineno, "init_return"),
                        language="python", severity="bug", category="semantic",
                        message="`__init__` should not return a value — raises TypeError at runtime",
                        explanation="Python's `__init__` must return None. Returning any other value raises `TypeError: __init__() should return None`.",
                        line=lineno, column=child.col_offset,
                        source_line=_src(source_lines, lineno),
                        code_frame=build_code_frame(source_lines, lineno),
                        fix_hint="Remove the return value, or move the logic to a factory method",
                        confidence=1.0, origin="parser",
                        parser_name=_PARSER, backend_name=_BACKEND,
                    ))
    return issues


# ─── Check: yield in __init__ ────────────────────────────

def _check_yield_in_init(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for child in ast.walk(node):
                if isinstance(child, (ast.Yield, ast.YieldFrom)):
                    lineno = child.lineno
                    issues.append(NormalizedIssue(
                        id=make_issue_id("python", "semantic", lineno, "yield_in_init"),
                        language="python", severity="bug", category="semantic",
                        message="`yield` inside `__init__` makes it a generator — almost certainly a bug",
                        explanation="Using `yield` in `__init__` turns the constructor into a generator function. The object will not be properly initialized.",
                        line=lineno, column=child.col_offset,
                        source_line=_src(source_lines, lineno),
                        code_frame=build_code_frame(source_lines, lineno),
                        fix_hint="Remove the yield or move it to a separate method",
                        confidence=1.0, origin="parser",
                        parser_name=_PARSER, backend_name=_BACKEND,
                    ))
    return issues


# ─── Check: Duplicate dictionary keys ───────────────────

def _check_duplicate_dict_keys(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            seen: dict[object, int] = {}
            for i, key in enumerate(node.keys):
                if key is None:
                    continue  # **unpacking
                if isinstance(key, ast.Constant):
                    val = key.value
                    if val in seen:
                        lineno = key.lineno
                        issues.append(NormalizedIssue(
                            id=make_issue_id("python", "semantic", lineno, f"dup_key_{val}"),
                            language="python", severity="bug", category="semantic",
                            message=f"Duplicate dictionary key `{val!r}` — later value silently overwrites the earlier one",
                            explanation="When a dictionary has duplicate keys, only the last value is kept. The earlier value is silently lost, which is almost always a bug.",
                            line=lineno, column=key.col_offset,
                            source_line=_src(source_lines, lineno),
                            code_frame=build_code_frame(source_lines, lineno),
                            fix_hint="Remove the duplicate key or rename one of them",
                            confidence=1.0, origin="parser",
                            parser_name=_PARSER, backend_name=_BACKEND,
                        ))
                    else:
                        seen[val] = i
    return issues


# ─── Check: Unused imports ───────────────────────────────

def _check_unused_imports(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    # Collect all imported names and their lines
    imported: dict[str, int] = {}  # name -> lineno
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            if any(a.name == "*" for a in node.names):
                continue  # Can't track wildcard
            for alias in node.names:
                name = alias.asname or alias.name
                imported[name] = node.lineno

    if not imported:
        return issues

    # Collect all Name references in the tree (excluding imports themselves)
    used_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)

    for name, lineno in imported.items():
        if name not in used_names and not name.startswith("_"):
            issues.append(NormalizedIssue(
                id=make_issue_id("python", "quality", lineno, f"unused_import_{name}"),
                language="python", severity="info", category="quality",
                message=f"Imported `{name}` is never used",
                explanation="Unused imports clutter the namespace and slow down module loading.",
                line=lineno, column=0,
                source_line=_src(source_lines, lineno),
                code_frame=build_code_frame(source_lines, lineno),
                fix_hint=f"Remove the unused import of `{name}`",
                confidence=0.85, origin="parser",
                parser_name=_PARSER, backend_name=_BACKEND,
            ))
    return issues


# ─── Check: pickle.loads() ──────────────────────────────

def _check_pickle_loads(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle"
                    and node.func.attr in ("loads", "load")):
                lineno = node.lineno
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "security", lineno, "pickle_loads"),
                    language="python", severity="security", category="security",
                    message=f"`pickle.{node.func.attr}()` can execute arbitrary code during deserialization",
                    explanation="Pickle deserialization executes arbitrary Python code embedded in the data. Never unpickle data from untrusted sources.",
                    line=lineno, column=node.col_offset,
                    source_line=_src(source_lines, lineno),
                    code_frame=build_code_frame(source_lines, lineno),
                    fix_hint="Use `json.loads()` for data interchange, or validate the source before unpickling",
                    confidence=0.90, origin="parser",
                    parser_name=_PARSER, backend_name=_BACKEND,
                ))
    return issues


# ─── Check: except Exception: raise OtherException() (losing traceback) ─

def _check_bare_raise_in_except(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None:
            for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                if isinstance(child, ast.Raise) and child.exc is not None and child.cause is None:
                    # Raising a NEW exception without `from` — loses original traceback
                    if isinstance(child.exc, ast.Call):
                        lineno = child.lineno
                        issues.append(NormalizedIssue(
                            id=make_issue_id("python", "runtime-risk", lineno, "raise_without_from"),
                            language="python", severity="warning", category="runtime-risk",
                            message="Re-raising a new exception without `from` loses the original traceback",
                            explanation="When you catch an exception and raise a new one, use `raise NewException(...) from e` to preserve the original traceback chain.",
                            line=lineno, column=child.col_offset,
                            source_line=_src(source_lines, lineno),
                            code_frame=build_code_frame(source_lines, lineno),
                            fix_hint="Add `from e` to preserve context: `raise NewException(...) from e`",
                            confidence=0.80, origin="parser",
                            parser_name=_PARSER, backend_name=_BACKEND,
                        ))
    return issues


# ─── Check: except Exception: pass (silently swallowing) ─

def _check_empty_except_pass(tree: ast.AST, source_lines: list[str]) -> list[NormalizedIssue]:
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Body is exactly [Pass]
            if (len(node.body) == 1 and isinstance(node.body[0], ast.Pass)
                    and node.type is not None):
                lineno = node.lineno
                issues.append(NormalizedIssue(
                    id=make_issue_id("python", "runtime-risk", lineno, "except_pass"),
                    language="python", severity="warning", category="runtime-risk",
                    message="Exception caught and silently ignored with `pass`",
                    explanation="Catching an exception and doing nothing hides bugs. At minimum, log the exception for debugging.",
                    line=lineno, column=node.col_offset,
                    source_line=_src(source_lines, lineno),
                    code_frame=build_code_frame(source_lines, lineno),
                    fix_hint="Log the exception: `except Exception as e: logger.error(e)` or re-raise",
                    confidence=0.90, origin="parser",
                    parser_name=_PARSER, backend_name=_BACKEND,
                ))
    return issues
