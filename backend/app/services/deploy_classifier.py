"""
AutoDeploy — Repository Classification Service

Analyzes repository files to detect project type (frontend, backend, ML, DB)
and recommends suitable free deployment platforms.
"""

import os
import re
from dataclasses import dataclass, field, asdict
from typing import Any


# ─── Platform Registry ────────────────────────────────────

PLATFORMS = {
    "frontend": [
        {"id": "vercel", "name": "Vercel", "icon": "▲", "tier": "free", "best_for": ["Next.js", "React", "Vue", "Svelte"]},
        {"id": "netlify", "name": "Netlify", "icon": "◆", "tier": "free", "best_for": ["Static", "React", "Vue", "Gatsby"]},
        {"id": "cloudflare_pages", "name": "Cloudflare Pages", "icon": "☁", "tier": "free", "best_for": ["Static", "React", "Vue"]},
        {"id": "github_pages", "name": "GitHub Pages", "icon": "⬡", "tier": "free", "best_for": ["Static", "Jekyll"]},
    ],
    "backend": [
        {"id": "render", "name": "Render", "icon": "◉", "tier": "free", "best_for": ["FastAPI", "Flask", "Express", "Django"]},
        {"id": "koyeb", "name": "Koyeb", "icon": "◈", "tier": "free", "best_for": ["Python", "Node.js", "Go"]},
        {"id": "deno_deploy", "name": "Deno Deploy", "icon": "🦕", "tier": "free", "best_for": ["Deno", "TypeScript"]},
        {"id": "cloudflare_workers", "name": "Cloudflare Workers", "icon": "☁", "tier": "free", "best_for": ["Serverless", "JS"]},
    ],
    "ml": [
        {"id": "huggingface", "name": "Hugging Face Spaces", "icon": "🤗", "tier": "free", "best_for": ["Gradio", "Streamlit", "ML demos"]},
        {"id": "lightning_ai", "name": "Lightning AI", "icon": "⚡", "tier": "free", "best_for": ["PyTorch", "Training"]},
    ],
    "database": [
        {"id": "supabase", "name": "Supabase", "icon": "⚡", "tier": "free", "best_for": ["Postgres", "Auth", "Realtime"]},
        {"id": "mongodb_atlas", "name": "MongoDB Atlas", "icon": "🍃", "tier": "free", "best_for": ["MongoDB", "NoSQL"]},
        {"id": "neon", "name": "Neon", "icon": "🐘", "tier": "free", "best_for": ["Postgres", "Serverless DB"]},
    ],
    "advanced": [
        {"id": "oracle_cloud", "name": "Oracle Cloud", "icon": "☁", "tier": "free", "best_for": ["VPS", "Always Free"]},
        {"id": "google_cloud", "name": "Google Cloud", "icon": "G", "tier": "free_trial", "best_for": ["GCP", "Cloud Run"]},
        {"id": "aws_free", "name": "AWS Free Tier", "icon": "A", "tier": "free_tier", "best_for": ["EC2", "Lambda", "S3"]},
    ],
}


# ─── Detection Patterns ──────────────────────────────────

FRONTEND_SIGNALS = {
    "next": {"framework": "Next.js", "files": ["next.config.js", "next.config.mjs", "next.config.ts"], "deps": ["next"]},
    "react": {"framework": "React", "files": [], "deps": ["react", "react-dom"]},
    "vue": {"framework": "Vue", "files": ["vue.config.js", "nuxt.config.js"], "deps": ["vue"]},
    "angular": {"framework": "Angular", "files": ["angular.json"], "deps": ["@angular/core"]},
    "svelte": {"framework": "Svelte", "files": ["svelte.config.js"], "deps": ["svelte"]},
    "vite": {"framework": "Vite", "files": ["vite.config.ts", "vite.config.js"], "deps": ["vite"]},
    "gatsby": {"framework": "Gatsby", "files": ["gatsby-config.js"], "deps": ["gatsby"]},
}

BACKEND_SIGNALS = {
    "fastapi": {"framework": "FastAPI", "files": [], "deps": ["fastapi", "uvicorn"], "code": ["from fastapi", "import fastapi"]},
    "flask": {"framework": "Flask", "files": [], "deps": ["flask"], "code": ["from flask", "import flask"]},
    "django": {"framework": "Django", "files": ["manage.py", "settings.py"], "deps": ["django"], "code": ["from django"]},
    "express": {"framework": "Express", "files": [], "deps": ["express"], "code": ["require('express')", "require(\"express\")"]},
    "nestjs": {"framework": "NestJS", "files": [], "deps": ["@nestjs/core"], "code": []},
}

ML_SIGNALS = {
    "gradio": {"framework": "Gradio", "deps": ["gradio"], "code": ["import gradio", "gr.Interface"]},
    "streamlit": {"framework": "Streamlit", "deps": ["streamlit"], "code": ["import streamlit", "st."]},
    "torch": {"framework": "PyTorch", "deps": ["torch", "pytorch"], "code": ["import torch"]},
    "tensorflow": {"framework": "TensorFlow", "deps": ["tensorflow", "tf"], "code": ["import tensorflow"]},
    "transformers": {"framework": "Transformers", "deps": ["transformers"], "code": ["from transformers"]},
    "sklearn": {"framework": "Scikit-learn", "deps": ["scikit-learn", "sklearn"], "code": ["from sklearn"]},
}

DB_SIGNALS = {
    "postgres": {"type": "PostgreSQL", "deps": ["psycopg2", "psycopg2-binary", "asyncpg", "pg"], "env": ["DATABASE_URL", "POSTGRES"]},
    "mongodb": {"type": "MongoDB", "deps": ["pymongo", "motor", "mongoose", "mongodb"], "env": ["MONGO_URI", "MONGODB_URI"]},
    "sqlite": {"type": "SQLite", "deps": ["sqlite3"], "env": []},
    "supabase": {"type": "Supabase", "deps": ["supabase"], "env": ["SUPABASE_URL", "SUPABASE_KEY"]},
    "prisma": {"type": "Prisma", "deps": ["prisma", "@prisma/client"], "env": ["DATABASE_URL"]},
    "sqlalchemy": {"type": "SQLAlchemy", "deps": ["sqlalchemy", "alembic"], "env": ["DATABASE_URL"]},
    "redis": {"type": "Redis", "deps": ["redis", "ioredis"], "env": ["REDIS_URL"]},
}


@dataclass
class ProjectClassification:
    project_type: str = "unknown"           # frontend, backend, fullstack, ml, static
    frontend_type: str | None = None        # Next.js, React, Vue, etc.
    backend_type: str | None = None         # FastAPI, Express, etc.
    ml_type: str | None = None              # Gradio, PyTorch, etc.
    database_type: str | None = None        # PostgreSQL, MongoDB, etc.
    is_static: bool = False
    is_monorepo: bool = False
    recommended_platforms: list[dict] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    detected_files: list[str] = field(default_factory=list)
    detected_deps: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    build_command: str | None = None
    start_command: str | None = None
    required_env_vars: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def classify_repository(file_tree: list[dict], file_contents: dict[str, str]) -> ProjectClassification:
    """
    Classify a repository by analyzing its file tree and key file contents.

    Args:
        file_tree: List of {path, type, size} dicts from GitHub tree API
        file_contents: Dict of filepath -> content for key files

    Returns:
        ProjectClassification with type, recommendations, and reasoning
    """
    result = ProjectClassification()
    file_paths = [f["path"] for f in file_tree]
    file_names = {os.path.basename(p).lower() for p in file_paths}

    # Gather all dependency names
    all_deps = _extract_dependencies(file_contents)
    result.detected_deps = list(all_deps)[:30]

    # Check for monorepo signals
    top_dirs = {p.split("/")[0] for p in file_paths if "/" in p}
    if {"frontend", "backend"}.issubset(top_dirs) or {"client", "server"}.issubset(top_dirs):
        result.is_monorepo = True
        result.reasoning.append("Monorepo detected (frontend/backend or client/server directories)")

    # ─── Detect frontend ─────────────────────────────
    for key, sig in FRONTEND_SIGNALS.items():
        if any(f in file_names for f in sig["files"]) or any(d in all_deps for d in sig["deps"]):
            result.frontend_type = sig["framework"]
            result.reasoning.append(f"Frontend: {sig['framework']} detected")
            break

    # ─── Detect backend ──────────────────────────────
    for key, sig in BACKEND_SIGNALS.items():
        if any(d in all_deps for d in sig["deps"]):
            result.backend_type = sig["framework"]
            result.reasoning.append(f"Backend: {sig['framework']} detected via dependencies")
            break
        # Check code patterns
        for code_pat in sig.get("code", []):
            for content in file_contents.values():
                if code_pat.lower() in content.lower():
                    result.backend_type = sig["framework"]
                    result.reasoning.append(f"Backend: {sig['framework']} detected via code pattern")
                    break
            if result.backend_type:
                break

    # ─── Detect ML ────────────────────────────────────
    for key, sig in ML_SIGNALS.items():
        if any(d in all_deps for d in sig["deps"]):
            result.ml_type = sig["framework"]
            result.reasoning.append(f"ML/AI: {sig['framework']} detected")
            break
        for code_pat in sig.get("code", []):
            for content in file_contents.values():
                if code_pat.lower() in content.lower():
                    result.ml_type = sig["framework"]
                    result.reasoning.append(f"ML/AI: {sig['framework']} detected via code")
                    break
            if result.ml_type:
                break

    # ─── Detect database ─────────────────────────────
    for key, sig in DB_SIGNALS.items():
        if any(d in all_deps for d in sig["deps"]):
            result.database_type = sig["type"]
            result.reasoning.append(f"Database: {sig['type']} detected")
            result.required_env_vars.extend(sig["env"])
            break

    # ─── Detect entry points ─────────────────────────
    entry_names = ["main.py", "app.py", "server.py", "index.ts", "index.js", "manage.py"]
    for p in file_paths:
        if os.path.basename(p).lower() in entry_names:
            result.entry_points.append(p)

    # ─── Detect build/start commands ─────────────────
    pkg_json = file_contents.get("package.json", "")
    if pkg_json:
        if '"build"' in pkg_json:
            result.build_command = "npm run build"
        if '"start"' in pkg_json:
            result.start_command = "npm start"
        elif '"dev"' in pkg_json:
            result.start_command = "npm run dev"

    if "requirements.txt" in file_names or "pyproject.toml" in file_names:
        result.start_command = result.start_command or "python main.py"

    # ─── Determine project type ──────────────────────
    if result.ml_type:
        result.project_type = "ml"
    elif result.frontend_type and result.backend_type:
        result.project_type = "fullstack"
    elif result.frontend_type:
        result.project_type = "frontend"
        # Check if static-only
        if result.frontend_type in ("React", "Vue", "Svelte") and not result.backend_type:
            has_api_dir = any("api/" in p or "server" in p for p in file_paths)
            if not has_api_dir:
                result.is_static = True
    elif result.backend_type:
        result.project_type = "backend"
    elif "index.html" in file_names and not result.backend_type:
        result.project_type = "static"
        result.is_static = True
        result.reasoning.append("Static site detected (index.html without backend)")
    else:
        result.project_type = "unknown"
        result.warnings.append("Could not confidently classify this project")

    # ─── Recommend platforms ─────────────────────────
    result.recommended_platforms = _recommend_platforms(result)

    # ─── Confidence score ────────────────────────────
    signals = sum([
        bool(result.frontend_type),
        bool(result.backend_type),
        bool(result.ml_type),
        bool(result.database_type),
        bool(result.entry_points),
        bool(result.build_command or result.start_command),
        len(result.detected_deps) > 3,
    ])
    result.confidence = min(1.0, signals / 5.0)

    # ─── Warnings ────────────────────────────────────
    if not result.entry_points:
        result.warnings.append("No clear entry point detected (main.py, app.py, index.ts, etc.)")
    if not result.build_command and not result.start_command:
        result.warnings.append("No build or start command detected")
    if result.is_monorepo:
        result.warnings.append("Monorepo detected — deploy each part separately for best results")

    result.detected_files = file_paths[:50]
    return result


def _extract_dependencies(file_contents: dict[str, str]) -> set[str]:
    """Extract dependency names from package.json, requirements.txt, etc."""
    deps = set()

    # package.json
    pkg = file_contents.get("package.json", "")
    if pkg:
        for match in re.findall(r'"([^"@][^"]*)":\s*"[\^~]?[\d.]', pkg):
            deps.add(match.lower())

    # requirements.txt
    req = file_contents.get("requirements.txt", "")
    if req:
        for line in req.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                name = re.split(r'[>=<!\[]', line)[0].strip().lower()
                if name:
                    deps.add(name)

    # pyproject.toml
    pyproj = file_contents.get("pyproject.toml", "")
    if pyproj:
        for match in re.findall(r'"([a-zA-Z0-9_-]+)', pyproj):
            deps.add(match.lower())

    return deps


def _recommend_platforms(c: ProjectClassification) -> list[dict]:
    """Select best platforms based on classification."""
    recs = []

    if c.project_type in ("frontend", "static"):
        if c.frontend_type == "Next.js":
            recs.append({**PLATFORMS["frontend"][0], "reason": "Vercel is the native host for Next.js", "match": 95})
        elif c.is_static:
            recs.append({**PLATFORMS["frontend"][2], "reason": "Cloudflare Pages excels at static sites", "match": 90})
            recs.append({**PLATFORMS["frontend"][3], "reason": "GitHub Pages is free for static sites", "match": 80})
        else:
            recs.append({**PLATFORMS["frontend"][0], "reason": "Vercel supports most frontend frameworks", "match": 85})
            recs.append({**PLATFORMS["frontend"][1], "reason": "Netlify is a great alternative for frontends", "match": 80})

    if c.project_type in ("backend", "fullstack"):
        if c.backend_type in ("FastAPI", "Flask", "Django"):
            recs.append({**PLATFORMS["backend"][0], "reason": f"Render supports {c.backend_type} with free tier", "match": 90})
            recs.append({**PLATFORMS["backend"][1], "reason": f"Koyeb supports Python backends", "match": 75})
        elif c.backend_type in ("Express", "NestJS"):
            recs.append({**PLATFORMS["backend"][0], "reason": f"Render supports Node.js backends", "match": 85})
        else:
            recs.append({**PLATFORMS["backend"][0], "reason": "Render is a versatile backend host", "match": 80})

    if c.project_type == "ml":
        if c.ml_type in ("Gradio", "Streamlit"):
            recs.append({**PLATFORMS["ml"][0], "reason": f"HuggingFace Spaces natively supports {c.ml_type}", "match": 95})
        else:
            recs.append({**PLATFORMS["ml"][0], "reason": "HuggingFace Spaces for ML demos", "match": 80})
            recs.append({**PLATFORMS["ml"][1], "reason": "Lightning AI for training workloads", "match": 70})

    if c.database_type:
        if c.database_type in ("PostgreSQL", "SQLAlchemy", "Prisma"):
            recs.append({**PLATFORMS["database"][0], "reason": "Supabase offers free Postgres hosting", "match": 85})
            recs.append({**PLATFORMS["database"][2], "reason": "Neon offers serverless Postgres", "match": 80})
        elif c.database_type == "MongoDB":
            recs.append({**PLATFORMS["database"][1], "reason": "MongoDB Atlas free tier for MongoDB", "match": 90})
        elif c.database_type == "Supabase":
            recs.append({**PLATFORMS["database"][0], "reason": "Already uses Supabase", "match": 95})

    if c.project_type == "fullstack" and c.frontend_type:
        recs.append({**PLATFORMS["frontend"][0], "reason": f"Deploy {c.frontend_type} frontend to Vercel", "match": 80})

    # Sort by match score
    recs.sort(key=lambda x: x.get("match", 0), reverse=True)
    return recs[:6]
