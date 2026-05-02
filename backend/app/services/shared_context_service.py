"""
Shared Code Context Service

Bridges the Devमित्र widget, Repo Explorer, Studio, and Workspace so
both chat experiences (bottom-right widget + navbar Repo Explorer) share
the same understanding of the currently loaded code and repository.

This is a lightweight in-process singleton — perfect for hackathon scale.
"""

import json
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = structlog.get_logger("automerge.shared_context")

# ─── Persistent storage ──────────────────────────────────
DATA_DIR = Path("./data/shared_context")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CONTEXT_FILE = DATA_DIR / "active_context.json"


class SharedContextStore:
    """Singleton store for cross-feature code understanding context."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._context: Dict[str, Any] = {
            "studio": {"code": "", "filename": "", "language": "", "logs": "", "updated_at": ""},
            "workspace": {"files": [], "repo_url": "", "current_file": "", "updated_at": ""},
            "repo_explorer": {"report_id": "", "repo_name": "", "summary": "", "tech_stack": {}, "updated_at": ""},
            "analysis": {"last_summary": "", "last_issues": [], "updated_at": ""},
        }
        self._qa_history: List[Dict[str, str]] = []
        self._load()

    # ─── Persistence ──────────────────────────────────────

    def _load(self):
        if CONTEXT_FILE.exists():
            try:
                data = json.loads(CONTEXT_FILE.read_text())
                self._context = data.get("context", self._context)
                self._qa_history = data.get("qa_history", [])
            except Exception:
                pass

    def _save(self):
        try:
            CONTEXT_FILE.write_text(json.dumps({
                "context": self._context,
                "qa_history": self._qa_history[-100:],  # keep last 100
            }, indent=2, default=str))
        except Exception as e:
            logger.warning("shared_context.save_failed", error=str(e))

    # ─── Update Methods ──────────────────────────────────

    def update_studio_context(self, code: str = "", filename: str = "",
                              language: str = "", logs: str = ""):
        self._context["studio"] = {
            "code": code[:10000],
            "filename": filename,
            "language": language,
            "logs": logs[:5000],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        logger.info("shared_context.studio_updated", filename=filename)

    def update_workspace_context(self, repo_url: str = "", files: list = None,
                                 current_file: str = ""):
        self._context["workspace"] = {
            "repo_url": repo_url,
            "files": (files or [])[:50],
            "current_file": current_file,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        logger.info("shared_context.workspace_updated", repo_url=repo_url)

    def update_repo_explorer_context(self, report_id: str, repo_name: str,
                                     summary: str, tech_stack: dict):
        self._context["repo_explorer"] = {
            "report_id": report_id,
            "repo_name": repo_name,
            "summary": summary[:2000],
            "tech_stack": tech_stack,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        logger.info("shared_context.repo_explorer_updated", repo=repo_name)

    def update_analysis_context(self, summary: str, issues: list):
        self._context["analysis"] = {
            "last_summary": summary[:2000],
            "last_issues": issues[:20],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()

    def add_qa_entry(self, question: str, answer: str, source: str = "widget"):
        self._qa_history.append({
            "question": question,
            "answer": answer[:2000],
            "source": source,
            "asked_at": datetime.now(timezone.utc).isoformat(),
        })
        self._save()

    # ─── Read Methods ─────────────────────────────────────

    def get_full_context(self) -> Dict[str, Any]:
        return self._context

    def get_context_summary(self) -> Dict[str, Any]:
        """Returns a lightweight summary for the Devमित्र widget context badge."""
        ctx = self._context
        signals = []
        if ctx["studio"].get("code"):
            signals.append({"type": "studio", "label": f"Studio: {ctx['studio'].get('filename', 'snippet')}"})
        if ctx["workspace"].get("repo_url"):
            signals.append({"type": "workspace", "label": f"Workspace: {ctx['workspace']['repo_url'].split('/')[-1]}"})
        if ctx["repo_explorer"].get("report_id"):
            signals.append({"type": "repo_explorer", "label": f"Repo: {ctx['repo_explorer'].get('repo_name', '')}"})
        if ctx["analysis"].get("last_summary"):
            signals.append({"type": "analysis", "label": "Analysis available"})

        return {
            "has_context": len(signals) > 0,
            "signals": signals,
            "primary_label": signals[0]["label"] if signals else "No code context yet",
        }

    def get_enriched_devmitra_context(self, widget_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge the widget's own context with the shared context to give Devमित्र
        the richest possible understanding for answering questions.
        """
        enriched = {**widget_context}

        ctx = self._context
        # If widget has no code but studio does, inject it
        if not enriched.get("code") and ctx["studio"].get("code"):
            enriched["code"] = ctx["studio"]["code"]
            enriched["filename"] = ctx["studio"].get("filename", "")
            enriched["language"] = ctx["studio"].get("language", "auto")

        # If widget has no logs but studio does
        if not enriched.get("logs") and ctx["studio"].get("logs"):
            enriched["logs"] = ctx["studio"]["logs"]

        # Inject repo context
        if not enriched.get("repoUrl") and ctx["workspace"].get("repo_url"):
            enriched["repoUrl"] = ctx["workspace"]["repo_url"]

        # Inject repo explorer summary
        if ctx["repo_explorer"].get("summary"):
            enriched["repo_summary"] = ctx["repo_explorer"]["summary"]
            enriched["repo_tech_stack"] = ctx["repo_explorer"].get("tech_stack", {})
            enriched["repo_name"] = ctx["repo_explorer"].get("repo_name", "")

        # Inject latest analysis
        if ctx["analysis"].get("last_summary"):
            enriched["analysis_summary"] = ctx["analysis"]["last_summary"]

        return enriched

    def get_qa_history(self, limit: int = 20) -> List[Dict[str, str]]:
        return self._qa_history[-limit:]

    # ─── AR Debug Explorer Context ────────────────────────

    def update_ar_context(self, scene_id: str, source_type: str,
                          title: str, summary: str):
        """Update shared context with the most recently viewed AR scene."""
        if "ar" not in self._context:
            self._context["ar"] = {}
        self._context["ar"] = {
            "scene_id": scene_id,
            "source_type": source_type,
            "title": title,
            "summary": summary[:500],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        logger.info("shared_context.ar_updated", scene_id=scene_id)


# Module-level singleton
shared_context = SharedContextStore()
