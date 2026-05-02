"""
Extension Service — Backend intelligence layer for the Chrome extension.

Receives code from browser pages, routes through the existing analyzer pipeline,
persists results, and pushes context into Devमित्र shared context.

Rules:
- Never executes user code
- Reuses existing studio_service analyzer (no new engine)
- Treats all browser code as untrusted
- Returns structured results safe for extension popup rendering
"""

import hashlib
import json
import random
import string
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from app.agent.parser_router import route_and_parse
from app.services.studio_service import run_studio_pipeline
from app.services import llm_service
from app.services.shared_context_service import shared_context

logger = structlog.get_logger("automerge.extension")

# ─── Persistence ─────────────────────────────────────────

DATA_DIR = Path("./data/extension")
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "history.json"

# ─── ID gen ──────────────────────────────────────────────

def _gen_id(prefix: str = "ext") -> str:
    seed = f"{time.time()}{random.random()}"
    return f"{prefix}_{hashlib.md5(seed.encode()).hexdigest()[:10]}"

# ─── Persistence helpers ─────────────────────────────────

def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []

def _save_history(history: list[dict]):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str))

def _save_report(report_id: str, data: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / f"{report_id}.json").write_text(json.dumps(data, indent=2, default=str))

def _load_report(report_id: str) -> dict | None:
    p = DATA_DIR / f"{report_id}.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None

def _append_history(entry: dict):
    history = _load_history()
    history.insert(0, entry)
    _save_history(history[:200])

# ─── Language detection ───────────────────────────────────

_EXT_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".cpp": "cpp", ".c": "c", ".cs": "csharp", ".sh": "bash",
    ".html": "html", ".css": "css", ".sql": "sql",
}

def _guess_language(code: str, filename: str = "", page_url: str = "") -> str:
    # From filename extension
    if filename:
        for ext, lang in _EXT_MAP.items():
            if filename.endswith(ext):
                return lang

    # From URL cues
    url_lower = page_url.lower()
    if ".py" in url_lower:
        return "python"
    if ".js" in url_lower or ".jsx" in url_lower:
        return "javascript"
    if ".ts" in url_lower or ".tsx" in url_lower:
        return "typescript"

    # From code heuristics
    code_lower = code[:500].lower()
    if "def " in code_lower and "print(" in code_lower:
        return "python"
    if "import react" in code_lower or "const " in code_lower:
        return "javascript"
    if "interface " in code_lower or ": string" in code_lower:
        return "typescript"
    if "public class " in code_lower or "system.out" in code_lower:
        return "java"
    if "func " in code_lower and "fmt." in code_lower:
        return "go"
    if "#include" in code_lower:
        return "cpp"

    return "python"  # safe default for analyzer

# ─── Source title builder ─────────────────────────────────

def _build_source_title(source_type: str, filename: str, page_url: str) -> str:
    if filename:
        return filename
    if page_url:
        parts = page_url.rstrip("/").split("/")
        return parts[-1] or page_url[:60]
    return source_type.replace("_", " ").title()

# ─── Devमित्र context push ────────────────────────────────

def _push_to_devmitra(analysis_id: str, code: str, language: str,
                      filename: str, issues: list, root_cause: str,
                      explanation: str, confidence: float):
    """Push extension analysis into Devमित्र shared context for follow-up Q&A."""
    try:
        # Update studio context so Devमित्र has the code
        shared_context.update_studio_context(
            code=code,
            filename=filename or "browser-snippet",
            language=language,
            logs="",
        )
        # Update analysis summary
        issue_summary = "; ".join(
            f"{i.get('severity','?').upper()}: {i.get('message','?')}"
            for i in (issues or [])[:5]
        )
        shared_context.update_analysis_context(
            summary=f"[Extension {analysis_id}] {root_cause or explanation or 'Analysis complete'}",
            issues=issues or [],
        )
        logger.info("extension.devmitra_context_pushed", analysis_id=analysis_id)
    except Exception as e:
        logger.warning("extension.devmitra_push_failed", error=str(e)[:200])


# ─── Core analyze function ────────────────────────────────

async def analyze_browser_code(
    code: str,
    language: str = "",
    filename: str = "",
    source_type: str = "selection",
    page_url: str = "",
    repo_url: str = "",
    selected_text: str = "",
    session_id: str = "",
    extension_version: str = "1.0",
) -> dict:
    """
    Main entry point for the Chrome extension.

    Routes code through the existing Studio analyzer pipeline and returns
    a compact, popup-ready result plus a full stored report.
    """
    if not code or not code.strip():
        return {
            "status": "error",
            "error": "No code provided. Select code on the page first.",
            "analysis_id": None,
        }

    code_to_analyze = (selected_text or code).strip()
    if not code_to_analyze:
        return {
            "status": "error",
            "error": "Empty code after extraction.",
            "analysis_id": None,
        }

    # Clamp to avoid extreme inputs
    code_to_analyze = code_to_analyze[:50_000]

    # Resolve language
    resolved_lang = language or _guess_language(code_to_analyze, filename, page_url)

    # Resolve filename
    resolved_filename = filename or _build_source_title(source_type, filename, page_url)

    analysis_id = _gen_id("ext")
    code_hash = hashlib.md5(code_to_analyze.encode()).hexdigest()[:12]

    logger.info(
        "extension.analyze_requested",
        analysis_id=analysis_id,
        source_type=source_type,
        language=resolved_lang,
        code_len=len(code_to_analyze),
    )

    # ── PHASE 1: Parser-first syntax validation ───────────
    # run_and_parse() uses compile() for Python, node --check for JS/TS.
    # Syntax errors detected here are ground truth — LLM cannot override them.
    parser_issues: list[dict] = []
    parser_syntax_failed = False
    try:
        parse_result = route_and_parse(code_to_analyze, resolved_lang, resolved_filename)
        for iss in (parse_result.issues or []):
            d = iss.to_dict() if hasattr(iss, "to_dict") else (
                iss.__dict__ if hasattr(iss, "__dict__") else dict(iss)
            )
            parser_issues.append(d)
        parser_syntax_failed = any(
            i.get("category") == "syntax" or i.get("severity") == "error"
            for i in parser_issues
        )
    except Exception as pe:
        logger.warning("extension.parser_precheck_failed", error=str(pe)[:200])

    # ── PHASE 2: Studio LLM pipeline (explanation / fix / learning) ──
    try:
        studio_result = run_studio_pipeline(
            code=code_to_analyze,
            language=resolved_lang,
            filename=resolved_filename,
            modes=["debug", "fix", "validate"],
        )
    except Exception as e:
        logger.error("extension.pipeline_failed", error=str(e)[:300])
        return {
            "status": "error",
            "error": f"Analysis pipeline failed: {str(e)[:200]}",
            "analysis_id": analysis_id,
        }

    # ── PHASE 3: AI Logic Analysis (If Parser passed) ────────
    ai_root_cause = ""
    ai_explanation = ""
    ai_fix = ""
    ai_issues = []
    
    if not parser_syntax_failed:
        try:
            ai_res = await llm_service.analyze_code_for_logic_bugs(code_to_analyze, resolved_lang)
            if ai_res is None:
                # AI call failed (e.g., 429 Too Many Requests)
                ai_issues = [{
                    "severity": "warning", 
                    "message": "AI Analysis Unavailable (Rate Limit/Network). Only basic syntax was checked.",
                    "line": 1
                }]
                ai_root_cause = "LLM API Limit Reached / Unavailable"
                ai_explanation = (
                    "⚠️ **AI Reviewer Unreachable**\n\n"
                    "The static parser found no syntax errors, but the AI logic analyzer could not "
                    "be reached (likely due to API rate limits). Logical bugs or runtime errors may still exist."
                )
            elif ai_res.get("has_issues"):
                ai_issues = ai_res.get("issues", [])
                ai_root_cause = ai_res.get("root_cause", "")
                ai_explanation = ai_res.get("explanation", "")
                ai_fix = ai_res.get("fix_suggestion", "")
        except Exception as e:
            logger.warning("extension.ai_analysis_failed", error=str(e)[:200])

    # ── PHASE 4: Merge — parser > ai > studio ────────────────
    # Parser issues take precedence
    llm_issues = studio_result.get("issues", [])
    merged_issues = parser_issues[:]
    parser_lines = {i.get("line") for i in parser_issues if i.get("line")}
    
    # Add AI issues
    for ai_iss in ai_issues:
        ai_iss["severity"] = ai_iss.get("severity", "bug")
        merged_issues.append(ai_iss)

    # Add Studio issues
    for li in llm_issues:
        if li.get("line") not in parser_lines:
            merged_issues.append(li)

    issues = merged_issues
    if parser_syntax_failed and not issues:
        issues = parser_issues

    base_confidence = studio_result.get("confidence", 0.0)
    if parser_syntax_failed:
        confidence = 1.0
    elif ai_issues:
        confidence = 0.85
    else:
        confidence = base_confidence

    root_cause      = ai_root_cause or studio_result.get("root_cause", "")
    explanation     = ai_explanation or studio_result.get("explanation", "")
    fix_explanation = ai_fix or studio_result.get("fix_explanation", "")
    fixed_code      = studio_result.get("fixed_code", "")
    diff_text       = studio_result.get("diff_text", "")
    validation      = studio_result.get("validation", {})

    # If parser found syntax error but LLM says "no issues", override explanation
    if parser_syntax_failed:
        first_syn = next((i for i in parser_issues if i.get("category") == "syntax"), None)
        if first_syn:
            parser_msg = first_syn.get("message", "Syntax error detected")
            parser_line = first_syn.get("line")
            parser_fix = first_syn.get("fix_hint", "")
            if not root_cause or "no issue" in root_cause.lower():
                root_cause = f"Syntax error at line {parser_line}: {parser_msg}"
            if not explanation or "no issue" in explanation.lower():
                explanation = (
                    f"The parser detected a syntax error: {parser_msg}. "
                    f"This was found on line {parser_line} by the language parser "
                    f"and must be fixed before the code can run."
                )
            if not fix_explanation and parser_fix:
                fix_explanation = parser_fix

    # Build learning notes from quality + refactor suggestions
    learning_items = []
    for s in (studio_result.get("quality_suggestions") or [])[:3]:
        if isinstance(s, dict):
            learning_items.append(s.get("message", str(s)))
        else:
            learning_items.append(str(s))
    for s in (studio_result.get("refactor_suggestions") or [])[:2]:
        if isinstance(s, dict):
            learning_items.append(s.get("message", str(s)))
        else:
            learning_items.append(str(s))
    learning_notes = " | ".join(learning_items[:4]) if learning_items else ""

    # Compact issue summary for popup
    issue_summary_items = []
    for iss in issues[:6]:
        sev = iss.get("severity", "info").upper()
        msg = iss.get("message", "")[:80]
        line = iss.get("line")
        entry = f"[{sev}]" + (f" L{line}:" if line else "") + f" {msg}"
        issue_summary_items.append(entry)
    issue_summary = "\n".join(issue_summary_items)

    website_base = "http://localhost:3000"
    open_full_report_url = f"{website_base}/extension?report={analysis_id}"

    # ── Full report dict (stored) ─────────────────────────
    full_report = {
        "analysis_id": analysis_id,
        "code_hash": code_hash,
        "source_type": source_type,
        "page_url": page_url,
        "repo_url": repo_url,
        "filename": resolved_filename,
        "language": resolved_lang,
        "code_snippet": code_to_analyze[:2000],
        "extension_version": extension_version,
        "session_id": session_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        # Full pipeline output
        "issues": issues,
        "root_cause": root_cause,
        "explanation": explanation,
        "fix_suggestion": fix_explanation,
        "fixed_code": fixed_code,
        "diff_text": diff_text,
        "confidence": confidence,
        "validation": validation,
        "learning_notes": learning_notes,
        "issue_summary": issue_summary,
        "quality_suggestions": studio_result.get("quality_suggestions", []),
        "refactor_suggestions": studio_result.get("refactor_suggestions", []),
    }

    # ── Persist ───────────────────────────────────────────
    try:
        _save_report(analysis_id, full_report)
        _append_history({
            "analysis_id": analysis_id,
            "source_type": source_type,
            "page_url": page_url[:200],
            "filename": resolved_filename,
            "language": resolved_lang,
            "confidence": confidence,
            "issue_count": len(issues),
            "root_cause": (root_cause or "")[:200],
            "code_hash": code_hash,
            "created_at": full_report["created_at"],
            "open_url": open_full_report_url,
        })
    except Exception as e:
        logger.warning("extension.persist_failed", error=str(e)[:200])

    # ── Push to Devमित्र ───────────────────────────────────
    _push_to_devmitra(
        analysis_id=analysis_id,
        code=code_to_analyze,
        language=resolved_lang,
        filename=resolved_filename,
        issues=issues,
        root_cause=root_cause,
        explanation=explanation,
        confidence=confidence,
    )

    # ── Compact response for popup ─────────────────────────
    return {
        "status": "ok",
        "analysis_id": analysis_id,
        "language": resolved_lang,
        "source_type": source_type,
        "source_summary": f"{source_type.replace('_', ' ').title()} — {resolved_filename}",
        "issue_count": len(issues),
        "issue_summary": issue_summary,
        "root_cause": root_cause,
        "explanation": explanation,
        "fix_suggestion": fix_explanation,
        "learning_notes": learning_notes,
        "confidence": round(confidence, 2),
        "open_full_report_url": open_full_report_url,
        "has_fix": bool(fixed_code and fixed_code.strip() != code_to_analyze.strip()),
        "validation_status": (validation or {}).get("status", ""),
        "created_at": full_report["created_at"],
    }


# ─── History + Report retrieval ───────────────────────────

def get_history(limit: int = 50) -> list[dict]:
    return _load_history()[:limit]

def get_report(analysis_id: str) -> dict | None:
    return _load_report(analysis_id)

def delete_report(analysis_id: str) -> bool:
    p = DATA_DIR / f"{analysis_id}.json"
    deleted = False
    if p.exists():
        p.unlink()
        deleted = True
    history = _load_history()
    history = [h for h in history if h.get("analysis_id") != analysis_id]
    _save_history(history)
    return deleted
