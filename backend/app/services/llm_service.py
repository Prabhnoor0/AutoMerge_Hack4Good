"""
AutoMerge LLM Service — Gemini Integration Layer

Safe, isolated LLM wrapper that provides AI-enhanced explanations,
fix hints, root cause summaries, and chat responses on top of the
existing deterministic parser/static-analysis pipeline.

Rules:
- Never throws uncaught exceptions
- Always returns a fallback-safe result
- Never replaces parser/AST as source of truth
- Respects ENABLE_LLM feature flag
- Enforces timeouts
- Sanitizes sensitive data before sending
"""

import asyncio
import re
import time
import structlog

from app.config import settings

logger = structlog.get_logger("automerge.llm")

# ─── Lazy Gemini Client ──────────────────────────────────

_client_configured = False

def _ensure_configured():
    """Check if API key is present."""
    global _client_configured
    if _client_configured:
        return True
    if not settings.has_llm:
        return False
    _client_configured = True
    logger.info("llm.initialized", model=settings.LLM_MODEL)
    return True


# ─── Sanitization ─────────────────────────────────────────

_SECRET_PATTERNS = [
    r'(?i)(api[_-]?key|secret|password|token|auth)\s*[=:]\s*["\']?[\w\-\.]{8,}',
    r'ghp_[A-Za-z0-9_]{36,}',
    r'sk-[A-Za-z0-9]{32,}',
    r'AIza[A-Za-z0-9_\-]{35}',
]


def _sanitize(text: str) -> str:
    """Remove potential secrets/keys from text before sending to LLM."""
    if not text:
        return text
    for pat in _SECRET_PATTERNS:
        text = re.sub(pat, "[REDACTED]", text)
    return text


# ─── Core Call ────────────────────────────────────────────

async def _call_gemini(prompt: str, max_tokens: int = 1024) -> str | None:
    """Call Gemini with timeout and error handling using HTTP REST API."""
    if not _ensure_configured():
        return None

    sanitized = _sanitize(prompt)

    try:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.LLM_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": sanitized}]}]
        }
        
        start = time.time()
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", None)
            
        elapsed = time.time() - start
        logger.info("llm.call_ok", elapsed_ms=int(elapsed * 1000), chars=len(text or ""))
        return text
    except asyncio.TimeoutError:
        logger.warning("llm.timeout", timeout_s=settings.LLM_TIMEOUT_SECONDS)
        return None
    except Exception as e:
        logger.warning("llm.call_failed", error=str(e)[:200])
        return None


# ─── Public Helpers ───────────────────────────────────────

async def generate_explanation(code: str, issues: list[dict], language: str) -> str | None:
    """Generate a simple English explanation of code issues."""
    if not issues:
        return None

    issues_text = "\n".join(
        f"- Line {i.get('line','?')}: {i.get('message','')} (severity: {i.get('severity','')})"
        for i in issues[:8]
    )

    prompt = f"""You are AutoMerge Mentor, a friendly developer assistant.

A {language} code snippet was analyzed by a static parser and these issues were found:

{issues_text}

Explain these issues to a developer in simple, clear English.
- Use plain language, not jargon
- Explain WHY each issue matters
- Keep it concise (3-5 sentences max)
- Use a helpful, mentoring tone"""

    return await _call_gemini(prompt, max_tokens=512)


async def generate_fix_hint(code: str, issues: list[dict], language: str) -> str | None:
    """Generate smarter fix suggestions based on parser findings."""
    if not issues:
        return None

    top_issue = issues[0]
    code_snippet = code[:1500]

    prompt = f"""You are AutoMerge Mentor. A static analyzer found this issue in {language} code:

Issue: {top_issue.get('message', '')}
Line: {top_issue.get('line', '?')}
Severity: {top_issue.get('severity', '')}

Code context:
```{language}
{code_snippet}
```

Give a specific, actionable fix hint in 2-3 sentences.
Show the exact change needed if possible.
Keep it practical and concise."""

    return await _call_gemini(prompt, max_tokens=400)


async def generate_root_cause_summary(code: str, issues: list[dict], language: str) -> str | None:
    """Generate a root cause → effect → fix chain."""
    if not issues:
        return None

    issues_text = "\n".join(
        f"- {i.get('message','')} (line {i.get('line','?')}, {i.get('severity','')})"
        for i in issues[:5]
    )

    prompt = f"""You are AutoMerge Mentor. Based on static analysis of {language} code:

Issues found:
{issues_text}

Write a ROOT CAUSE CHAIN in this exact format:
🔍 **Root Cause:** [what the fundamental problem is]
⚡ **Effect:** [what happens because of it]
🔧 **Fix:** [what to do to resolve it]

Keep each line to 1-2 sentences. Be specific, not generic."""

    return await _call_gemini(prompt, max_tokens=300)


async def generate_test_suggestion(code: str, issues: list[dict], language: str) -> str | None:
    """Suggest a regression test that would catch the detected bugs."""
    if not issues:
        return None

    top = issues[0]
    code_snippet = code[:1200]

    prompt = f"""You are AutoMerge Mentor. A {language} code analysis found:
Issue: {top.get('message', '')} at line {top.get('line', '?')}

Code:
```{language}
{code_snippet}
```

Write ONE concise regression test that would catch this specific bug.
Use the standard testing framework for {language} (pytest for Python, Jest for JS/TS).
Keep it minimal — just the test function, no boilerplate.
Output only the test code, nothing else."""

    return await _call_gemini(prompt, max_tokens=400)


async def generate_chat_reply(query: str, context: dict) -> str | None:
    """Generate a natural chat response for Devमित्र."""
    code = context.get("code", "")[:1500]
    filename = context.get("filename", "")
    language = context.get("language", "auto")
    repo_summary = context.get("repo_summary", "")
    analysis = context.get("analysis_summary", "")

    ctx_parts = []
    if filename:
        ctx_parts.append(f"File: {filename}")
    if language != "auto":
        ctx_parts.append(f"Language: {language}")
    if repo_summary:
        ctx_parts.append(f"Repo context: {repo_summary[:300]}")
    if analysis:
        ctx_parts.append(f"Analysis: {analysis[:300]}")
    if code:
        ctx_parts.append(f"Code:\n```\n{code}\n```")

    context_block = "\n".join(ctx_parts) if ctx_parts else "No code context available."

    prompt = f"""You are Devमित्र, AutoMerge's built-in AI developer assistant.
You are helpful, concise, and developer-friendly.

Context:
{context_block}

Developer's question: {query}

Give a helpful, concise answer (3-8 sentences). Use markdown formatting.
If you don't have enough context, say so clearly and suggest what to provide."""

    return await _call_gemini(prompt, max_tokens=600)


async def generate_repo_summary(repo_name: str, tech_stack: dict, file_tree: list, readme: str = "") -> str | None:
    """Generate an enhanced repository summary."""
    langs = ", ".join(tech_stack.get("languages", []))
    fws = ", ".join(tech_stack.get("frameworks", []))
    files = "\n".join(f[:80] for f in file_tree[:30]) if file_tree else "No tree available"
    readme_snippet = readme[:800] if readme else ""

    prompt = f"""You are AutoMerge Mentor. Summarize this repository for a developer:

Repository: {repo_name}
Languages: {langs}
Frameworks: {fws}

Key files:
{files}

{f'README excerpt: {readme_snippet}' if readme_snippet else ''}

Write a 3-5 sentence summary covering:
1. What the project does
2. Key technologies used
3. Architecture pattern (if detectable)
Keep it concise and informative."""

    return await _call_gemini(prompt, max_tokens=400)


async def generate_learning_summary(topic: str, weakness_summary: str, evidence: list[str]) -> str | None:
    """Generate classroom-friendly learning explanation."""
    evidence_text = "\n".join(f"- {e}" for e in evidence[:5])

    prompt = f"""You are AutoMerge Mentor in teaching mode.

A developer keeps making this type of mistake:
Topic: {topic}
Pattern: {weakness_summary}

Evidence from past bugs:
{evidence_text}

Write a short learning lesson (4-6 sentences) that:
1. Explains the concept simply
2. Shows why this pattern causes bugs
3. Gives a practical tip to avoid it
4. Encourages the developer

Use a friendly, mentoring tone."""

    return await _call_gemini(prompt, max_tokens=400)


async def generate_pr_body(root_cause: str, changes: list[str], language: str, confidence: float) -> dict | None:
    """Generate improved PR title and body."""
    changes_text = "\n".join(f"- {c}" for c in changes[:8])

    prompt = f"""You are AutoMerge Mentor generating a PR summary.

Root cause: {root_cause}
Language: {language}
Confidence: {confidence:.0%}
Changes made:
{changes_text}

Generate a JSON object with exactly these keys:
- "title": a concise PR title (max 72 chars), starting with "fix:" or "refactor:"
- "summary": a 2-3 sentence human-readable summary of the change
- "impact": one sentence on what this fixes for users

Output ONLY valid JSON, no markdown fences."""

    result = await _call_gemini(prompt, max_tokens=300)
    if not result:
        return None

    # Try to parse JSON from response
    try:
        import json
        # Clean markdown fences if present
        clean = result.strip()
        if clean.startswith("```"):
            clean = "\n".join(clean.split("\n")[1:-1])
        return json.loads(clean)
    except Exception:
        return {"title": None, "summary": result.strip()[:200], "impact": None}


# ─── Status Check ─────────────────────────────────────────

def get_llm_status() -> dict:
    """Return current LLM configuration status."""
    return {
        "enabled": settings.ENABLE_LLM,
        "configured": settings.has_llm,
        "provider": "gemini" if settings.GEMINI_API_KEY else "none",
        "model": settings.LLM_MODEL if settings.has_llm else None,
        "timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
    }
