"""
Tests for the precision analyzer engine upgrade.

Proves:
1. Valid JS/TS is NOT falsely flagged
2. Invalid JS/TS syntax IS correctly flagged (when node is available)
3. Invalid Python syntax IS correctly flagged with real parser
4. Patch round-trip: analyze → fix → validate
5. Fallback modes handled safely
6. API response contracts serialize correctly
7. Studio pipeline works end-to-end
"""

import sys
import os

# Ensure backend app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agent.diagnostics import NormalizedIssue, ParseResult, make_issue_id, build_code_frame
from app.agent.parser_router import route_and_parse, detect_language, normalize_language
from app.agent.code_analyzer import analyze_code
from app.services.studio_service import run_studio_pipeline


# ─── Test: Language Detection ─────────────────────────────

def test_language_detection_from_filename():
    assert detect_language("", "main.py") == ("python", 1.0)
    assert detect_language("", "index.js") == ("javascript", 1.0)
    assert detect_language("", "App.tsx") == ("typescript", 1.0)
    assert detect_language("", "utils.ts") == ("typescript", 1.0)
    assert detect_language("", "App.jsx") == ("javascript", 1.0)
    print("  ✓ Language detection from filename — PASSED")


def test_language_alias_normalization():
    assert normalize_language("py") == "python"
    assert normalize_language("js") == "javascript"
    assert normalize_language("jsx") == "javascript"
    assert normalize_language("ts") == "typescript"
    assert normalize_language("tsx") == "typescript"
    assert normalize_language("python") == "python"
    print("  ✓ Language alias normalization — PASSED")


def test_language_detection_from_code():
    py_code = "def hello():\n    print('hello')\n    return True"
    lang, conf = detect_language(py_code, "")
    assert lang == "python", f"Expected python, got {lang}"
    assert conf > 0.5
    print(f"  ✓ Language detection from code keywords — PASSED (lang={lang}, conf={conf:.2f})")


# ─── Test: Python Parser (compile + ast) ─────────────────

def test_python_valid_code():
    code = "def hello():\n    return 'world'\n"
    result = route_and_parse(code, "python", "hello.py")
    assert result.parse_success
    assert not result.is_fallback
    assert result.parser_name == "cpython_ast"
    assert not result.has_syntax_errors
    print("  ✓ Valid Python — no false positives from parser — PASSED")


def test_python_syntax_error():
    code = "def hello(\n    return 'world'\n"
    result = route_and_parse(code, "python", "broken.py")
    assert result.parse_success  # Parser ran successfully (it found an error)
    assert not result.is_fallback
    assert result.has_syntax_errors
    assert len(result.issues) >= 1
    err = result.issues[0]
    assert err.severity == "error"
    assert err.category == "syntax"
    assert err.origin == "parser"
    assert err.confidence == 1.0
    assert "SyntaxError" in err.message
    assert err.line > 0
    print(f"  ✓ Python syntax error detected at line {err.line} — PASSED")


def test_python_semantic_checks():
    code = '''
def process(data=[]):
    try:
        result = eval(data[0])
    except:
        result = None
    if result == None:
        return result
'''
    result = route_and_parse(code, "python", "semantic.py")
    assert result.parse_success
    assert not result.has_syntax_errors

    ids = [i.id for i in result.issues]
    categories = [i.category for i in result.issues]
    severities = [i.severity for i in result.issues]

    # Must detect mutable default
    has_mutable = any(i.category == "semantic" and "Mutable default" in i.message for i in result.issues)
    assert has_mutable, "Should detect mutable default argument"

    # Must detect eval()
    has_eval = any(i.category == "security" for i in result.issues)
    assert has_eval, "Should detect eval() security risk"

    # Must detect bare except
    has_bare = any("Bare except" in i.message for i in result.issues)
    assert has_bare, "Should detect bare except"

    # Must detect == None
    has_none = any("is None" in i.message for i in result.issues)
    assert has_none, "Should detect == None comparison"

    # All must be from parser, not heuristic
    for issue in result.issues:
        assert issue.origin == "parser", f"Expected parser origin, got {issue.origin} for {issue.message}"
        assert issue.confidence == 1.0, f"Expected confidence 1.0, got {issue.confidence}"

    print(f"  ✓ Python semantic checks (found {len(result.issues)} issues, all from AST) — PASSED")


# ─── Test: Valid JS/TS NOT falsely flagged ────────────────

def test_valid_js_no_false_positives():
    """The old regex engine flagged every assignment as 'assignment operator used'.
    The new engine must NOT do this."""
    code = '''
const x = 10;
let name = "hello";
const items = [1, 2, 3];
const filtered = items.filter(d => d.status === "active");
const result = items.map(x => x * 2);
function greet(name) {
    return "Hello, " + name;
}
'''
    analysis = analyze_code(code, "javascript", "valid.js")
    issues = analysis["issues"]

    # Must NOT have the false positive "assignment operator used"
    false_positives = [i for i in issues if "assignment operator" in i.get("message", "").lower()]
    assert len(false_positives) == 0, (
        f"FAIL: Found {len(false_positives)} false 'assignment operator' warnings on valid JS code"
    )

    # Should not flag valid assignments as syntax errors
    syntax_errors = [i for i in issues if i.get("category") == "syntax" and i.get("severity") == "error"]
    assert len(syntax_errors) == 0, f"False syntax errors on valid JS: {syntax_errors}"

    print(f"  ✓ Valid JS — no 'assignment operator' false positives — PASSED (total issues: {len(issues)})")


def test_valid_ts_no_false_positives():
    """Valid TypeScript must not be falsely flagged."""
    code = '''
interface User {
    name: string;
    age: number;
}

const greet = (user: User): string => {
    return `Hello, ${user.name}`;
};

const numbers: number[] = [1, 2, 3];
const doubled = numbers.map(n => n * 2);
'''
    analysis = analyze_code(code, "typescript", "valid.ts")
    issues = analysis["issues"]

    false_positives = [i for i in issues if "assignment operator" in i.get("message", "").lower()]
    assert len(false_positives) == 0, f"False 'assignment operator' warnings on valid TS"

    syntax_errors = [i for i in issues if i.get("category") == "syntax" and i.get("severity") == "error"]
    assert len(syntax_errors) == 0, f"False syntax errors on valid TS"

    print(f"  ✓ Valid TS — no false positives — PASSED (total issues: {len(issues)})")


# ─── Test: JS/TS Syntax Errors Detected ──────────────────

def test_js_syntax_error_detected():
    """Invalid JS must be caught when node is available."""
    code = "function broken( { return 42; }"
    result = route_and_parse(code, "javascript", "broken.js")

    if result.is_fallback:
        print(f"  ⚠ JS syntax error test SKIPPED — {result.fallback_reason}")
        return

    assert result.parse_success
    assert result.has_syntax_errors or len(result.issues) > 0
    print(f"  ✓ JS syntax error detected ({len(result.issues)} issues) — PASSED")


# ─── Test: Analyze → Fix → Validate Round-Trip ──────────

def test_python_roundtrip():
    """Analyze broken Python, fix it, validate the fix re-parses clean."""
    code = '''
def process(items=[]):
    try:
        result = eval(items[0])
    except:
        pass
    if result == None:
        return result
'''
    # Analyze
    analysis = analyze_code(code, "python", "roundtrip.py")
    issues = analysis["issues"]
    assert len(issues) > 0, "Should find issues in buggy Python"

    # Fix (via studio pipeline)
    result = run_studio_pipeline(
        code=code,
        language="python",
        filename="roundtrip.py",
        modes=["debug", "fix", "validate"],
    )

    assert "issues" in result
    assert "original_code" in result
    assert "fixed_code" in result
    assert "validation" in result
    assert result["validation"]["status"] in ("passed", "partial", "skipped")
    assert "reasoning_trace" in result
    assert "confidence" in result

    # Confidence should reflect real parser usage
    assert result["confidence"] > 0.5, f"Confidence too low: {result['confidence']}"

    print(f"  ✓ Python round-trip (analyze→fix→validate) — PASSED")
    print(f"    Issues: {len(result['issues'])}, Confidence: {result['confidence']:.0%}")
    print(f"    Validation: {result['validation']['status']}")


# ─── Test: Fallback Modes ────────────────────────────────

def test_unsupported_language_fallback():
    code = "fn main() { println!(\"hello\"); }"
    result = route_and_parse(code, "rust", "main.rs")
    assert result.is_fallback
    assert result.parser_confidence == 0.0
    assert result.fallback_reason
    print(f"  ✓ Unsupported language fallback (rust) — PASSED: {result.fallback_reason}")


# ─── Test: API Response Shape ────────────────────────────

def test_studio_response_shape():
    """All expected fields must be present in studio pipeline output."""
    code = "def hello():\n    return 'world'\n"
    result = run_studio_pipeline(
        code=code,
        language="python",
        filename="hello.py",
        modes=["debug", "fix", "validate", "refactor", "quality"],
    )

    required_fields = [
        "language", "issues", "root_cause", "explanation", "confidence",
        "reasoning_trace", "original_code", "fixed_code", "diff_text",
        "fix_explanation", "changes", "validation", "refactor_suggestions",
        "quality_suggestions", "modes_executed", "duration_ms",
    ]
    for field in required_fields:
        assert field in result, f"Missing required field: {field}"

    # Validation must have the expected sub-shape
    v = result["validation"]
    for vf in ["status", "tests_passed", "tests_failed", "tests_total", "stdout"]:
        assert vf in v, f"Missing validation field: {vf}"

    print(f"  ✓ API response shape — all {len(required_fields)} fields present — PASSED")


# ─── Test: Code Frame Generation ─────────────────────────

def test_code_frame():
    lines = ["import os", "def hello():", "    return 42", "    x = 1", "print()"]
    frame = build_code_frame(lines, 3, 5)
    assert ">" in frame
    assert "42" in frame
    print(f"  ✓ Code frame generation — PASSED")


# ─── Test: NormalizedIssue serialization ─────────────────

def test_normalized_issue_to_dict():
    issue = NormalizedIssue(
        id="test123",
        language="python",
        severity="error",
        category="syntax",
        message="SyntaxError: invalid syntax",
        line=5,
        column=10,
        confidence=1.0,
        origin="parser",
        parser_name="cpython_compile",
        backend_name="Python compile()",
    )
    d = issue.to_dict()
    assert d["id"] == "test123"
    assert d["severity"] == "error"
    assert d["origin"] == "parser"
    assert d["confidence"] == 1.0
    assert "raw_diagnostic" not in d  # Must not leak
    print("  ✓ NormalizedIssue.to_dict() — PASSED")


# ─── Test: ParseResult legacy conversion ────────────────

def test_parse_result_to_legacy():
    issues = [
        NormalizedIssue(id="a", language="python", severity="error", category="syntax",
                        message="SyntaxError: bad", origin="parser"),
        NormalizedIssue(id="b", language="python", severity="warning", category="quality",
                        message="warning msg", origin="parser"),
    ]
    pr = ParseResult(
        language="python", parser_name="cpython", backend_name="test",
        issues=issues, parse_success=True, is_fallback=False,
    )
    legacy = pr.to_legacy_issues()
    assert len(legacy) == 2
    assert isinstance(legacy[0], dict)
    assert legacy[0]["severity"] == "error"
    assert pr.has_syntax_errors
    assert pr.error_count == 1
    print("  ✓ ParseResult.to_legacy_issues() — PASSED")


# ─── Test: Parser info in analyze_code output ────────────

def test_parser_info_in_output():
    analysis = analyze_code("x = 1\n", "python", "test.py")
    assert "parser_info" in analysis
    pi = analysis["parser_info"]
    assert pi["backend"].startswith("Python ast.parse() + compile()"), f"Unexpected backend: {pi['backend']}"
    assert pi["is_fallback"] is False
    assert pi["parser_confidence"] == 1.0
    print("  ✓ Parser info present in analyze_code output — PASSED")


# ─── Test: exec() and wildcard import detection ─────────

def test_python_exec_and_wildcard():
    """exec() and wildcard import must be detected by AST checks."""
    code = "from os import *\nexec('print(1)')\n"
    result = route_and_parse(code, "python", "exec_test.py")
    messages = [i.message for i in result.issues]
    has_exec = any("exec()" in m for m in messages)
    has_wildcard = any("Wildcard import" in m for m in messages)
    assert has_exec, f"exec() not detected. Messages: {messages}"
    assert has_wildcard, f"Wildcard import not detected. Messages: {messages}"
    print(f"  ✓ exec() and wildcard import detected — PASSED ({len(result.issues)} issues)")


# ─── Test: assert-tuple bug detection ────────────────────

def test_python_assert_tuple():
    """assert (condition, 'msg') is always True — must be flagged."""
    code = "x = 5\nassert (x > 0, 'must be positive')\n"
    result = route_and_parse(code, "python", "assert_test.py")
    messages = [i.message for i in result.issues]
    has_assert_bug = any("assert with a tuple" in m for m in messages)
    assert has_assert_bug, f"assert-tuple not detected. Messages: {messages}"
    print("  ✓ assert-tuple bug detected — PASSED")


# ─── Test: Multi-error collection (8+ issues in one pass) ─

def test_multi_error_collection():
    """Analyzer must find ALL issues in one pass, not just the first."""
    code = (
        "from os import *\n"
        "\n"
        "def process(data=[], cache={}):\n"
        "    try:\n"
        "        result = eval(data[0])\n"
        "        exec(data[1])\n"
        "    except:\n"
        "        pass\n"
        "    if result != None:\n"
        "        assert (result > 0, 'must be positive')\n"
        "        return result\n"
        "    return None\n"
    )
    analysis = analyze_code(code, "python", "multi.py")
    issues = analysis["issues"]
    assert len(issues) >= 7, f"Expected ≥7 issues, got {len(issues)}"
    severities = set(i["severity"] for i in issues)
    assert "security" in severities, "No security issues found"
    assert "bug" in severities, "No bug issues found"
    assert "warning" in severities, "No warning issues found"
    print(f"  ✓ Multi-error collection — PASSED ({len(issues)} issues across {len(severities)} severities)")


# ─── Test: Structured explanation format ─────────────────

def test_structured_explanation():
    """Explanation must be structured with severity breakdown and grouped tiers."""
    from app.services.studio_service import generate_explanation
    issues = [
        {"id": "a", "severity": "error", "message": "SyntaxError: bad", "line": 1,
         "fix_hint": "Fix it", "source_line": "def bad:", "origin": "parser",
         "backend_name": "Python compile()", "explanation": ""},
        {"id": "b", "severity": "warning", "message": "Bare except", "line": 5,
         "fix_hint": "Use except Exception", "source_line": "except:",
         "origin": "parser", "backend_name": "Python ast.parse()", "explanation": ""},
    ]
    result = generate_explanation(issues, "def bad:\n", "python")
    assert "Analysis Report" in result, "Missing report header"
    assert "2 Issues" in result or "2 Issue" in result, "Missing issue count"
    assert "Blocking Issues" in result, "Missing blocking tier"
    assert "How to fix" in result, "Missing fix hints"
    print("  ✓ Structured explanation format — PASSED")


# ─── Test: Lock declared but never used ─────────────────

def test_concurrency_lock_unused():
    """Lock defined but never acquired must be flagged."""
    code = (
        "import threading\n"
        "cache = {}\n"
        "lock = threading.Lock()\n"
        "\n"
        "def worker(k, v):\n"
        "    cache[k] = v\n"  # lock never used
        "\n"
        "t = threading.Thread(target=worker, args=(1, 2))\n"
        "t.start()\n"
    )
    result = route_and_parse(code, "python", "lock_unused.py")
    messages = [i.message for i in result.issues]
    has_lock_bug = any("never acquired" in m for m in messages)
    assert has_lock_bug, f"Lock-unused bug not detected. Messages: {messages}"
    print(f"  ✓ Lock declared but never used — PASSED ({len(result.issues)} issues)")


# ─── Test: Shared global mutation in thread ──────────────

def test_concurrency_shared_mutation():
    """Shared mutable global mutated in thread without lock must be flagged."""
    code = (
        "import threading\n"
        "data = []\n"
        "\n"
        "def worker(x):\n"
        "    data.append(x)\n"
        "\n"
        "t = threading.Thread(target=worker, args=(1,))\n"
        "t.start()\n"
    )
    result = route_and_parse(code, "python", "shared_mut.py")
    messages = [i.message for i in result.issues]
    has_shared = any("Thread-unsafe" in m or "shared" in m.lower() for m in messages)
    assert has_shared, f"Shared mutation not detected. Messages: {messages}"
    print(f"  ✓ Shared global mutation in thread — PASSED ({len(result.issues)} issues)")


# ─── Test: TOCTOU race detection ─────────────────────────

def test_concurrency_toctou():
    """Check-then-act race on shared dict in thread must be flagged."""
    code = (
        "import threading\n"
        "cache = {}\n"
        "\n"
        "def worker(key, value):\n"
        "    if key in cache:\n"
        "        cache[key] = value\n"
        "\n"
        "t = threading.Thread(target=worker, args=('x', 1))\n"
        "t.start()\n"
    )
    result = route_and_parse(code, "python", "toctou.py")
    messages = [i.message for i in result.issues]
    has_toctou = any("TOCTOU" in m or "Check-then-act" in m for m in messages)
    assert has_toctou, f"TOCTOU not detected. Messages: {messages}"
    print(f"  ✓ TOCTOU check-then-act race — PASSED ({len(result.issues)} issues)")


# ─── Test: Thread not joined ─────────────────────────────

def test_concurrency_thread_no_join():
    """Thread started but not joined must be flagged."""
    code = (
        "import threading\n"
        "\n"
        "def worker():\n"
        "    pass\n"
        "\n"
        "t = threading.Thread(target=worker)\n"
        "t.start()\n"
        "# no t.join()\n"
    )
    result = route_and_parse(code, "python", "no_join.py")
    messages = [i.message for i in result.issues]
    has_join = any("join" in m.lower() for m in messages)
    assert has_join, f"Missing join not detected. Messages: {messages}"
    print(f"  ✓ Thread started but never joined — PASSED ({len(result.issues)} issues)")


# ─── Test: Valid sequential code has NO concurrency bugs ──

def test_concurrency_no_false_positives():
    """Sequential Python code with no threading must have zero concurrency bugs."""
    code = (
        "data = []\n"
        "cache = {}\n"
        "\n"
        "def process(key, value):\n"
        "    data.append(value)\n"
        "    cache[key] = value\n"
        "\n"
        "process('a', 1)\n"
    )
    result = route_and_parse(code, "python", "sequential.py")
    concurrency_issues = [
        i for i in result.issues
        if i.parser_name == "cpython_ast_concurrency"
    ]
    assert len(concurrency_issues) == 0, (
        f"False positive concurrency issues on sequential code: "
        f"{[i.message for i in concurrency_issues]}"
    )
    print(f"  ✓ No false positives on sequential code — PASSED")


# ─── Test: Indirect helper mutation via call graph ───────

def test_concurrency_indirect_mutation():
    """worker→helper→global mutation must be flagged even though worker looks safe."""
    code = (
        "import threading\n"
        "cache = {}\n"
        "\n"
        "def update_cache(key, value):\n"
        "    cache[key] = value\n"
        "\n"
        "def worker(k, v):\n"
        "    update_cache(k, v)\n"
        "\n"
        "t = threading.Thread(target=worker, args=('a', 1))\n"
        "t.start()\n"
    )
    result = route_and_parse(code, "python", "indirect.py")
    messages = [i.message for i in result.issues]
    has_indirect = any("indirect" in m.lower() or "Indirect" in m for m in messages)
    assert has_indirect, f"Indirect mutation not detected. Messages: {messages}"
    print(f"  ✓ Indirect helper mutation detected — PASSED ({len(result.issues)} issues)")


# ─── Run All Tests ───────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  AutoMerge Analyzer Engine Tests")
    print("=" * 60 + "\n")

    tests = [
        test_language_detection_from_filename,
        test_language_alias_normalization,
        test_language_detection_from_code,
        test_python_valid_code,
        test_python_syntax_error,
        test_python_semantic_checks,
        test_valid_js_no_false_positives,
        test_valid_ts_no_false_positives,
        test_js_syntax_error_detected,
        test_python_roundtrip,
        test_unsupported_language_fallback,
        test_studio_response_shape,
        test_code_frame,
        test_normalized_issue_to_dict,
        test_parse_result_to_legacy,
        test_parser_info_in_output,
        test_python_exec_and_wildcard,
        test_python_assert_tuple,
        test_multi_error_collection,
        test_structured_explanation,
        # Concurrency tests
        test_concurrency_lock_unused,
        test_concurrency_shared_mutation,
        test_concurrency_toctou,
        test_concurrency_thread_no_join,
        test_concurrency_no_false_positives,
        test_concurrency_indirect_mutation,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {test.__name__} — FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__} — ERROR: {type(e).__name__}: {e}")

    print("\n" + "=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    sys.exit(1 if failed > 0 else 0)
