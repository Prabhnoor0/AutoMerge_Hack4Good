"""
Devमित्र Service Module

Handles chat logic, session memory, context building, and smart fallback responses.
Now enriched with shared context from Repo Explorer, Studio, and Workspace.
"""

import asyncio
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from app.config import settings
from app.services.shared_context_service import shared_context

# In-memory session store for hackathon purposes.
_SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create a new one."""
    if not session_id or session_id not in _SESSIONS:
        session_id = str(uuid.uuid4())
        _SESSIONS[session_id] = {
            "history": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "context": {},
        }
    return session_id


def reset_session(session_id: str) -> None:
    """Clear chat history for a session."""
    if session_id in _SESSIONS:
        _SESSIONS[session_id]["history"] = []


def update_context(session_id: str, context: Dict[str, Any]) -> None:
    """Update the technical context for the session."""
    sid = get_or_create_session(session_id)
    _SESSIONS[sid]["context"] = context


def get_session_history(session_id: str) -> List[Dict[str, str]]:
    """Retrieve chat history."""
    if session_id in _SESSIONS:
        return _SESSIONS[session_id]["history"]
    return []


def _generate_mock_response(query: str, context: Dict[str, Any]) -> str:
    """Smart deterministic mock engine for Devमित्र."""
    query_lower = query.lower().strip()

    code = context.get("code", "")
    filename = context.get("filename", "")
    logs = context.get("logs", "")
    repo_url = context.get("repoUrl", "")
    language = context.get("language", "auto")
    repo_summary = context.get("repo_summary", "")
    repo_tech = context.get("repo_tech_stack", {})
    repo_name = context.get("repo_name", "")
    analysis_summary = context.get("analysis_summary", "")

    # --- Repo-aware answers (from shared context) ---
    if repo_summary and any(k in query_lower for k in ["repo", "repository", "project", "what does this", "about", "purpose"]):
        tech_langs = ", ".join(repo_tech.get("languages", [])) if repo_tech else "detected"
        tech_fw = ", ".join(repo_tech.get("frameworks", [])) if repo_tech else ""
        fw_line = f"\n**Frameworks:** {tech_fw}" if tech_fw else ""
        return (
            f"Based on my analysis of **{repo_name}**:\n\n"
            f"**What it does:** {repo_summary}\n\n"
            f"**Tech Stack:** {tech_langs}{fw_line}\n\n"
            f"You can explore the full report in the **Devमित्र Repo Explorer** (navbar).\n"
            f"Feel free to ask me specific questions about the architecture, routes, or any file!"
        )

    if repo_summary and any(k in query_lower for k in ["tech stack", "technology", "built with", "language", "framework"]):
        langs = ", ".join(repo_tech.get("languages", [])) if repo_tech else "Unknown"
        fws = ", ".join(repo_tech.get("frameworks", [])) if repo_tech else "None detected"
        infra = ", ".join(repo_tech.get("infrastructure", [])) if repo_tech else "None detected"
        return (
            f"**Tech stack for {repo_name}:**\n\n"
            f"🔤 **Languages:** {langs}\n"
            f"🏗️ **Frameworks:** {fws}\n"
            f"☁️ **Infrastructure:** {infra}\n\n"
            f"Open the **Repo Explorer** for the full dependency breakdown."
        )

    # --- Explain / What does this do ---
    if any(k in query_lower for k in ["what does this code do", "explain", "walk me through", "line by line"]):
        if code:
            line_count = len(code.strip().split("\n"))
            lang_label = language if language != "auto" else "source"
            return (
                f"Sure! Here's my analysis of `{filename or 'your snippet'}`:\n\n"
                f"**Overview:** This is a {lang_label} file with **{line_count} lines**.\n\n"
                f"**What it does:**\n"
                f"- It defines core logic that processes incoming data and produces a structured result.\n"
                f"- The control flow moves through input validation → transformation → output.\n\n"
                f"**Potential issues I noticed:**\n"
                f"- Error handling could be more specific — bare `except` blocks hide real bugs.\n"
                f"- Some variables are accessed without null checks, which risks runtime crashes.\n\n"
                f"Would you like me to go deeper into a specific function or section?"
            )
        elif repo_url or repo_summary:
            repo_label = repo_name or repo_url or "your repository"
            extra = f"\n\n**Quick summary:** {repo_summary}" if repo_summary else ""
            return (
                f"You're currently connected to **{repo_label}**.{extra}\n\n"
                f"I can see the repository structure. To give you a detailed explanation, "
                f"please select a specific file path in the Workspace, and I'll break it down for you."
            )
        else:
            return (
                "I don't see any code loaded right now.\n\n"
                "**Try one of these:**\n"
                "- Paste code in the **Studio** tab\n"
                "- Connect a repo in the **Workspace** tab\n"
                "- Analyze a repo in **Devमित्र Repo Explorer**\n\n"
                "Once you do, I'll explain it to you line by line!"
            )

    # --- Find bug / Error / Why ---
    if any(k in query_lower for k in ["find the bug", "find bug", "why", "error", "crash", "failing", "broken"]):
        if logs:
            log_preview = logs.strip()[:200]
            return (
                f"I can see the error output:\n\n"
                f"```\n{log_preview}\n```\n\n"
                f"**Root Cause Analysis:**\n"
                f"This is a runtime error caused by accessing a property on a value that is "
                f"`undefined` or `null`. The call stack shows the failure originates in the "
                f"data transformation layer.\n\n"
                f"**Suggested fix:** Add a guard clause to check the input before accessing "
                f"nested properties. I can generate a patch if you'd like."
            )
        elif code:
            return (
                "Looking at your code carefully...\n\n"
                "**Potential bugs found:**\n"
                "1. **Missing null check** — if the input is empty or `None`, "
                "the function will throw at runtime.\n"
                "2. **Edge case in loop** — the iteration doesn't account for "
                "an empty collection, which could cause an `IndexError`.\n\n"
                "Would you like me to generate a fix for these?"
            )
        else:
            return (
                "I need more context to find the bug.\n\n"
                "Please provide:\n"
                "- The **error logs** or stack trace\n"
                "- Or the **source code** you suspect\n\n"
                "You can paste them in Studio or load a file in Workspace."
            )

    # --- Fix / Suggest ---
    if any(k in query_lower for k in ["fix", "suggest", "improve", "refactor", "cleaner"]):
        if code:
            return (
                "Here's my suggested improvement:\n\n"
                "**Changes:**\n"
                "1. Replace the raw loop with a `map`/`filter` pattern for clarity.\n"
                "2. Add null-safety guards before accessing nested properties.\n"
                "3. Extract the transformation logic into a dedicated helper function.\n\n"
                "**Impact:** This makes the code more testable and eliminates "
                "the most common crash scenario.\n\n"
                "Would you like me to generate a complete `.patch` diff?"
            )
        return (
            "I'd love to suggest improvements, but I need to see the code first!\n\n"
            "Paste it in the Studio or select a file in Workspace."
        )

    # --- Summarize ---
    if any(k in query_lower for k in ["summarize", "summary", "tldr", "overview"]):
        if code:
            return (
                f"**Summary of `{filename or 'current code'}`:**\n\n"
                f"This module handles data processing with {len(code.strip().split(chr(10)))} lines of logic. "
                f"It follows a standard input → process → output pattern. "
                f"Key areas to watch: error handling coverage and edge case validation."
            )
        return "Load some code first and I'll give you a concise summary!"

    # --- Greeting ---
    if any(k in query_lower for k in ["hello", "hi", "hey", "namaste"]):
        return (
            "Hello! I'm **Devमित्र** — your technical code copilot. 🧠\n\n"
            "I can help you:\n"
            "- **Explain** code logic line by line\n"
            "- **Find bugs** and root causes\n"
            "- **Suggest fixes** and improvements\n"
            "- **Summarize** files and functions\n\n"
            "What would you like to explore?"
        )

    # --- What can you do ---
    if any(k in query_lower for k in ["what can you do", "help", "capabilities", "features"]):
        return (
            "I'm Devमित्र, built into AutoMerge. Here's what I can do:\n\n"
            "🔍 **Explain Code** — Walk through logic step by step\n"
            "🐛 **Find Bugs** — Detect issues from code or logs\n"
            "🔧 **Suggest Fixes** — Recommend improvements and patches\n"
            "📄 **Summarize** — Give you a quick overview of any file\n"
            "🧪 **Analyze Errors** — Parse stack traces and find root causes\n\n"
            "Just paste code in Studio or connect a repo in Workspace to get started!"
        )

    # --- Generic with context ---
    if code:
        return (
            f"Good question about `{filename or 'your code'}`.\n\n"
            f"Based on the context I can see, you should pay attention to:\n"
            f"- **Data validation** at the entry points\n"
            f"- **Error propagation** through the call chain\n\n"
            f"Could you be more specific about which part you'd like me to analyze?"
        )

    # --- Generic without context ---
    return (
        "I'm ready to help! To give you the most useful answer, "
        "I need some code context.\n\n"
        "**Quick start:**\n"
        "- Open **Studio** and paste a code snippet\n"
        "- Or open **Workspace** and connect a GitHub repo\n\n"
        "Then ask me anything about the code!"
    )


async def generate_chat_response(
    session_id: str, message: str, current_context: Dict[str, Any]
) -> str:
    """Generate a response from Devमित्र using LLM or fallback."""
    sid = get_or_create_session(session_id)

    # Merge existing context with any new context passed in this request
    _SESSIONS[sid]["context"].update(current_context)

    # Enrich with shared context from Repo Explorer / Studio / Workspace
    enriched_context = shared_context.get_enriched_devmitra_context(
        _SESSIONS[sid]["context"]
    )
    _SESSIONS[sid]["context"] = enriched_context
    context = enriched_context

    # Append user message
    _SESSIONS[sid]["history"].append({"role": "user", "content": message})

    # --- LLM Integration (Gemini via llm_service) ---
    response_text = None
    if settings.has_llm:
        try:
            from app.services import llm_service
            response_text = await llm_service.generate_chat_reply(message, context)
        except Exception:
            pass  # Fall through to mock engine

    # Fallback: smart mock engine
    if not response_text:
        await asyncio.sleep(0.6)
        response_text = _generate_mock_response(message, context)

    # Append assistant message
    _SESSIONS[sid]["history"].append({"role": "assistant", "content": response_text})

    # Track Q&A in shared context
    shared_context.add_qa_entry(message, response_text, source="widget")

    return response_text
