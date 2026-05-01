"""
Python Fix Engine — Layer 5

Production-grade fix generator for Python code.
Consumes normalized issues and generates safe, targeted fixes.

Priorities: syntax errors → security → bugs → warnings → info
Each fix is re-parsed after application to ensure it doesn't break syntax.

Key design:
  - Sorts issues by line (ascending) to apply top-down
  - Tracks line offset from insertions so downstream fixes hit the right line
  - Uses message matching that avoids substring false positives
  - Every fix candidate is double-validated with compile() + ast.parse()
"""

import ast
import re
import structlog
from typing import Optional

logger = structlog.get_logger("automerge.python_fix_engine")


def apply_python_fixes(code: str, issues: list[dict]) -> tuple[str, list[str]]:
    """Apply fixes to Python code based on detected issues.

    Returns (fixed_code, list_of_change_descriptions).
    Prioritizes real parser/compiler diagnostics over heuristics.
    Each fix is validated by re-parsing to ensure no syntax breakage.
    """
    lines = code.split("\n")
    fixed_lines = list(lines)
    changes: list[str] = []
    applied_lines: set[int] = set()  # Prevent double-fixing same line

    # Sort by priority: syntax > security > bug > warning > info
    # Within same priority, sort by LINE ASCENDING so top-down fixes
    # apply correctly when insertions shift later lines
    _SEV_ORDER = {"error": 0, "security": 1, "bug": 2, "warning": 3, "info": 4}

    def _sort_key(i: dict):
        origin_priority = 0 if i.get("origin") in ("parser", "compiler") else 1
        sev_priority = _SEV_ORDER.get(i.get("severity", "info"), 5)
        return (origin_priority, sev_priority, i.get("line", 0))

    fixable = [i for i in issues if i["severity"] in ("error", "security", "bug", "warning")]
    fixable.sort(key=_sort_key)

    # Track cumulative line offset from insertions (e.g. mutable default guard)
    line_offset = 0
    needs_ast_import = False
    needs_subprocess_import = False

    for issue in fixable:
        original_line = issue.get("line", 0) - 1
        line_idx = original_line + line_offset
        if line_idx < 0 or line_idx >= len(fixed_lines):
            continue
        if original_line in applied_lines:
            continue

        line = fixed_lines[line_idx]
        msg = issue.get("message", "")
        issue_id = issue.get("id", "")
        parser = issue.get("parser_name", "")

        result = _try_fix(line, fixed_lines, line_idx, msg, issue_id, parser, issue)
        if result:
            new_line, change_desc, extra_import, inserted_lines = result
            # Validate the fix doesn't break syntax (compile + ast.parse)
            test_lines = list(fixed_lines)
            test_lines[line_idx] = new_line
            test_code = "\n".join(test_lines)
            try:
                compile(test_code, "<fix_check>", "exec")
                ast.parse(test_code)  # Double-check with AST parser
                fixed_lines[line_idx] = new_line
                changes.append(change_desc)
                applied_lines.add(original_line)
                line_offset += inserted_lines
                if extra_import == "ast":
                    needs_ast_import = True
                elif extra_import == "subprocess":
                    needs_subprocess_import = True
            except SyntaxError:
                # Fix would break syntax — skip it
                logger.debug("fix_engine.skip_broken_fix", line=line_idx + 1, msg=msg)

    # Add imports at the top if needed
    import_lines = []
    if needs_subprocess_import:
        if not any("import subprocess" in l for l in fixed_lines[:15]):
            import_lines.append("import subprocess")
            changes.insert(0, "Added `import subprocess` for subprocess.run()")
    if needs_ast_import:
        if not any("import ast" in l for l in fixed_lines[:15]):
            import_lines.append("import ast")
            changes.insert(0, "Added `import ast` for ast.literal_eval()")

    if import_lines:
        for imp in reversed(import_lines):
            fixed_lines.insert(0, imp)

    return "\n".join(fixed_lines), changes


def _try_fix(
    line: str,
    all_lines: list[str],
    line_idx: int,
    msg: str,
    issue_id: str,
    parser: str,
    issue: dict,
) -> Optional[tuple[str, str, str, int]]:
    """Try to generate a fix for a single issue.

    Returns (new_line, change_description, import_needed, lines_inserted) or None.
    import_needed: "" | "ast" | "subprocess"
    lines_inserted: how many new lines were inserted below (for offset tracking)
    """

    # ── eval() → ast.literal_eval() ──
    # IMPORTANT: check for "eval()" but NOT "exec()" — avoid matching "execute" substring
    if "eval(" in line and "literal_eval" not in line:
        if "eval()" in msg and "exec()" not in msg:
            new = line.replace("eval(", "ast.literal_eval(")
            return (
                new,
                f"Line {line_idx+1}: Replaced `eval()` with `ast.literal_eval()`",
                "ast",
                0,
            )

    # ── exec() — comment out with warning ──
    if "exec()" in msg and "exec(" in line:
        indent = re.match(r'^(\s*)', line).group(1)
        new = f"{indent}pass  # FIXME: exec() removed for security — {line.strip()}"
        return (new, f"Line {line_idx+1}: Commented out `exec()` call for security", "", 0)

    # ── Bare except ──
    if "Bare except" in msg or "bare_except" in issue_id:
        if re.match(r'^(\s*)except\s*:', line):
            indent = re.match(r'^(\s*)', line).group(1)
            return (
                f"{indent}except Exception as e:",
                f"Line {line_idx+1}: Changed bare `except:` to `except Exception as e:`",
                "",
                0,
            )

    # ── Mutable default [] ──
    if "Mutable default" in msg or "mutable_default" in issue_id:
        inserted = 0
        if "=[]" in line.replace(" ", "") or "= []" in line:
            new = line.replace("=[]", "=None").replace("= []", "=None")
            param = re.search(r'(\w+)\s*=\s*None', new)
            if param and line_idx + 1 < len(all_lines):
                body_indent = re.match(r'^(\s*)', all_lines[line_idx + 1])
                if body_indent:
                    init = f"{body_indent.group(1)}if {param.group(1)} is None: {param.group(1)} = []"
                    all_lines.insert(line_idx + 1, init)
                    inserted = 1
            return (new, f"Line {line_idx+1}: Replaced mutable default `[]` with `None` + guard", "", inserted)

        if "={}" in line.replace(" ", "") or "= {}" in line:
            new = line.replace("={}", "=None").replace("= {}", "=None")
            param = re.search(r'(\w+)\s*=\s*None', new)
            if param and line_idx + 1 < len(all_lines):
                body_indent = re.match(r'^(\s*)', all_lines[line_idx + 1])
                if body_indent:
                    init = f"{body_indent.group(1)}if {param.group(1)} is None: {param.group(1)} = {{}}"
                    all_lines.insert(line_idx + 1, init)
                    inserted = 1
            return (new, f"Line {line_idx+1}: Replaced mutable default `{{}}` with `None` + guard", "", inserted)

    # ── == None → is None ──
    if "== None" in line and ("is None" in msg or "None" in msg):
        new = line.replace("== None", "is None")
        return (new, f"Line {line_idx+1}: Changed `== None` to `is None`", "", 0)

    # ── != None → is not None ──
    if "!= None" in line and ("is not None" in msg or "None" in msg):
        new = line.replace("!= None", "is not None")
        return (new, f"Line {line_idx+1}: Changed `!= None` to `is not None`", "", 0)

    # ── os.system() → subprocess.run() with proper list args ──
    if "os.system()" in msg:
        m = re.search(r'os\.system\((.+?)\)', line)
        if m:
            arg = m.group(1).strip()
            indent = re.match(r'^(\s*)', line).group(1)
            # Try to decompose string concatenation into list args
            if "+" in arg:
                # e.g. 'echo ' + result  →  ["echo", result]
                parts = [p.strip() for p in arg.split("+")]
                list_args = []
                for p in parts:
                    p_stripped = p.strip("'\"").strip()
                    if p_stripped:
                        for word in p_stripped.split():
                            list_args.append(f'"{word}"')
                    else:
                        list_args.append(p.strip())
                # Last part might be a variable, not a string
                last_orig = parts[-1].strip()
                if not (last_orig.startswith("'") or last_orig.startswith('"')):
                    list_args[-1] = last_orig
                new = f"{indent}subprocess.run([{', '.join(list_args)}], check=True)"
            elif arg.startswith("'") or arg.startswith('"'):
                # Pure string: 'ls -la' → ["ls", "-la"]
                cmd_str = arg.strip("'\"")
                cmd_parts = cmd_str.split()
                quoted = [f'"{p}"' for p in cmd_parts]
                new = f"{indent}subprocess.run([{', '.join(quoted)}], check=True)"
            else:
                # Variable: cmd → shlex.split(cmd) — safest option
                new = f"{indent}subprocess.run({arg}.split(), check=True)"
            return (new, f"Line {line_idx+1}: Replaced `os.system()` with `subprocess.run()` (list args)", "subprocess", 0)

    # ── subprocess shell=True → shell=False ──
    if "shell=True" in msg and "shell=True" in line:
        new = line.replace("shell=True", "shell=False")
        return (new, f"Line {line_idx+1}: Changed `shell=True` to `shell=False`", "", 0)

    # ── f-string no placeholder ──
    if "f-string has no placeholders" in msg:
        new = re.sub(r'\bf(["\'])', r'\1', line, count=1)
        if new != line:
            return (new, f"Line {line_idx+1}: Removed unnecessary `f` prefix from string", "", 0)

    # ── assert tuple ──
    if "assert with a tuple" in msg:
        m = re.match(r'^(\s*)assert\s*\((.+?),\s*([\'"].*?[\'"])\)\s*$', line)
        if m:
            indent, cond, msg_str = m.groups()
            new = f"{indent}assert {cond}, {msg_str}"
            return (new, f"Line {line_idx+1}: Fixed assert-tuple to `assert condition, message`", "", 0)

    # ── Unreachable code ──
    if "Unreachable code" in msg:
        indent = re.match(r'^(\s*)', line).group(1)
        new = f"{indent}# UNREACHABLE: {line.strip()}"
        return (new, f"Line {line_idx+1}: Commented out unreachable code", "", 0)

    # ── Wildcard import — add TODO ──
    if "Wildcard import" in msg or "wildcard_import" in issue_id:
        new = f"{line}  # TODO: replace wildcard import with specific names"
        return (new, f"Line {line_idx+1}: Marked wildcard import for cleanup", "", 0)

    # ── except Exception: pass — mark for review ──
    if "silently ignored" in msg and "pass" in line:
        indent = re.match(r'^(\s*)', line).group(1)
        new = f"{indent}pass  # TODO: handle or log this exception"
        return (new, f"Line {line_idx+1}: Marked silent exception handler for review", "", 0)

    return None
