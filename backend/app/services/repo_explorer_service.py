"""
Devमित्र Repo Explorer — Service Layer

Handles repo ingestion, tech stack detection, structural analysis,
report generation, Mermaid diagrams, Q&A, and persistent history.
"""

import os
import re
import json
import uuid
import asyncio
import hashlib
import httpx
import structlog
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.shared_context_service import shared_context

logger = structlog.get_logger("automerge.repo_explorer")

# ─── Persistent Storage (JSON file-based for hackathon) ───
DATA_DIR = Path("./data/repo_explorer")
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "history.json"
REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    ".cache", ".venv", "venv", "env", ".env", ".idea", ".vscode",
    "coverage", ".nyc_output", "target", "out", ".turbo", ".parcel-cache",
}
SKIP_EXTS = {".pyc", ".pyo", ".exe", ".dll", ".so", ".o", ".class", ".jar",
             ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2",
             ".ttf", ".eot", ".mp3", ".mp4", ".zip", ".tar", ".gz", ".lock"}
MAX_FILE_SIZE = 50_000  # 50KB per file


def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []


def _save_history(history: list[dict]):
    HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str))


def _save_report(report_id: str, report: dict):
    (REPORTS_DIR / f"{report_id}.json").write_text(json.dumps(report, indent=2, default=str))


def _load_report(report_id: str) -> Optional[dict]:
    p = REPORTS_DIR / f"{report_id}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


# ─── GitHub Fetching ──────────────────────────────────────

def _parse_github_url(url: str) -> tuple[str, str]:
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    m = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if not m:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return m.group(1), m.group(2)


async def _fetch_repo_tree(owner: str, repo: str, token: str = "") -> list[dict]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1",
            headers=headers,
        )
        if r.status_code != 200:
            raise ValueError(f"GitHub API error {r.status_code}: {r.text[:200]}")
        return r.json().get("tree", [])


async def _fetch_file_content(owner: str, repo: str, path: str, token: str = "") -> str:
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
        )
        if r.status_code == 200:
            return r.text[:MAX_FILE_SIZE]
    return ""


async def _fetch_readme(owner: str, repo: str, token: str = "") -> str:
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if token:
        headers["Authorization"] = f"token {token}"
    async with httpx.AsyncClient(timeout=10) as client:
        for name in ["README.md", "readme.md", "README.rst", "README.txt", "README"]:
            r = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{name}",
                headers=headers,
            )
            if r.status_code == 200:
                return r.text[:10000]
    return ""


# ─── Tech Stack Detection ────────────────────────────────

_TECH_SIGNALS = {
    "package.json": {"keys": ["dependencies", "devDependencies"], "stack": "JavaScript/Node.js"},
    "requirements.txt": {"stack": "Python"},
    "pyproject.toml": {"stack": "Python"},
    "Pipfile": {"stack": "Python"},
    "Cargo.toml": {"stack": "Rust"},
    "go.mod": {"stack": "Go"},
    "pom.xml": {"stack": "Java"},
    "build.gradle": {"stack": "Java/Kotlin"},
    "Gemfile": {"stack": "Ruby"},
    "tsconfig.json": {"stack": "TypeScript"},
    "next.config.js": {"framework": "Next.js"},
    "next.config.mjs": {"framework": "Next.js"},
    "next.config.ts": {"framework": "Next.js"},
    "vite.config.ts": {"framework": "Vite"},
    "vite.config.js": {"framework": "Vite"},
    "angular.json": {"framework": "Angular"},
    "vue.config.js": {"framework": "Vue"},
    "nuxt.config.ts": {"framework": "Nuxt"},
    "svelte.config.js": {"framework": "Svelte"},
    "Dockerfile": {"infra": "Docker"},
    "docker-compose.yml": {"infra": "Docker Compose"},
    "docker-compose.yaml": {"infra": "Docker Compose"},
    ".github/workflows": {"infra": "GitHub Actions"},
    "vercel.json": {"infra": "Vercel"},
    "netlify.toml": {"infra": "Netlify"},
    "tailwind.config.js": {"styling": "Tailwind CSS"},
    "tailwind.config.ts": {"styling": "Tailwind CSS"},
}


def _detect_tech_stack(file_tree: list[dict], file_contents: dict[str, str]) -> dict:
    stack = {"languages": set(), "frameworks": set(), "infrastructure": set(),
             "styling": set(), "databases": set(), "dependencies": []}
    exts = {}
    for f in file_tree:
        if f.get("type") != "blob":
            continue
        path = f["path"]
        name = path.split("/")[-1]
        ext = os.path.splitext(name)[1].lower()
        exts[ext] = exts.get(ext, 0) + 1

        for signal_name, info in _TECH_SIGNALS.items():
            if name == signal_name or path.endswith(signal_name):
                if "stack" in info:
                    stack["languages"].add(info["stack"])
                if "framework" in info:
                    stack["frameworks"].add(info["framework"])
                if "infra" in info:
                    stack["infrastructure"].add(info["infra"])
                if "styling" in info:
                    stack["styling"].add(info["styling"])

    # Parse package.json for deps
    pkg = file_contents.get("package.json", "")
    if pkg:
        try:
            pkg_data = json.loads(pkg)
            deps = list((pkg_data.get("dependencies") or {}).keys())
            dev_deps = list((pkg_data.get("devDependencies") or {}).keys())
            stack["dependencies"] = deps[:20]
            for d in deps + dev_deps:
                if "react" in d:
                    stack["frameworks"].add("React")
                elif "vue" in d:
                    stack["frameworks"].add("Vue")
                elif "express" in d:
                    stack["frameworks"].add("Express")
                elif "fastapi" in d:
                    stack["frameworks"].add("FastAPI")
                elif "prisma" in d:
                    stack["databases"].add("Prisma ORM")
                elif "mongoose" in d:
                    stack["databases"].add("MongoDB")
                elif "sequelize" in d:
                    stack["databases"].add("Sequelize ORM")
                elif "tailwind" in d:
                    stack["styling"].add("Tailwind CSS")
        except Exception:
            pass

    # Parse requirements.txt
    req = file_contents.get("requirements.txt", "")
    if req:
        for line in req.strip().splitlines()[:30]:
            name = line.split("==")[0].split(">=")[0].split("~=")[0].strip()
            if name and not name.startswith("#"):
                stack["dependencies"].append(name)
                if name in ("fastapi", "flask", "django"):
                    stack["frameworks"].add(name.title())
                elif name in ("sqlalchemy", "alembic"):
                    stack["databases"].add("SQLAlchemy")
                elif name in ("pymongo", "motor"):
                    stack["databases"].add("MongoDB")

    # Ext-based language detection
    ext_lang = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".jsx": "React JSX", ".tsx": "React TSX", ".go": "Go",
                ".rs": "Rust", ".java": "Java", ".rb": "Ruby", ".cpp": "C++"}
    for ext, lang in ext_lang.items():
        if exts.get(ext, 0) > 0:
            stack["languages"].add(lang)

    return {k: sorted(v) if isinstance(v, set) else v for k, v in stack.items()}


# ─── Structural Analysis ─────────────────────────────────

def _build_folder_tree(file_tree: list[dict]) -> list[dict]:
    tree = []
    for f in sorted(file_tree, key=lambda x: x["path"]):
        path = f["path"]
        parts = path.split("/")
        if any(p in SKIP_DIRS for p in parts):
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext in SKIP_EXTS:
            continue
        tree.append({
            "path": path,
            "type": f.get("type", "blob"),
            "size": f.get("size", 0),
        })
    return tree[:500]  # Cap


def _analyze_structure(file_tree: list[dict], file_contents: dict[str, str]) -> dict:
    files = _build_folder_tree(file_tree)
    modules = set()
    routes = []
    components = []
    services = []
    configs = []
    entry_points = []

    for f in files:
        p = f["path"]
        name = p.split("/")[-1].lower()
        parts = p.split("/")
        if len(parts) >= 2:
            modules.add(parts[0] if parts[0] not in ("src", "app") else parts[1] if len(parts) > 2 else parts[0])
        if "route" in p.lower() or "router" in p.lower() or "api" in p.lower():
            routes.append(p)
        if "component" in p.lower():
            components.append(p)
        if "service" in p.lower():
            services.append(p)
        if name in ("config.py", "config.ts", "config.js", ".env.example",
                     "settings.py", "package.json", "tsconfig.json"):
            configs.append(p)
        if name in ("main.py", "app.py", "index.ts", "index.js", "server.py",
                     "page.tsx", "layout.tsx", "main.ts"):
            entry_points.append(p)

    return {
        "total_files": len(files),
        "modules": sorted(modules)[:20],
        "routes": routes[:20],
        "components": components[:20],
        "services": services[:20],
        "configs": configs[:10],
        "entry_points": entry_points[:10],
        "folder_tree": files[:200],
    }


# ─── Diagram Generation (Mermaid) ────────────────────────

def _generate_architecture_diagram(structure: dict, tech: dict) -> str:
    lines = ["graph TB"]
    lines.append('    subgraph Frontend["🖥️ Frontend"]')
    for c in structure.get("components", [])[:6]:
        safe = c.replace("/", "_").replace(".", "_").replace("-", "_")
        lines.append(f'        {safe}["{c.split("/")[-1]}"]')
    if not structure.get("components"):
        lines.append('        UI["UI Layer"]')
    lines.append("    end")
    lines.append('    subgraph Backend["⚙️ Backend"]')
    for r in structure.get("routes", [])[:6]:
        safe = r.replace("/", "_").replace(".", "_").replace("-", "_")
        lines.append(f'        {safe}["{r.split("/")[-1]}"]')
    if not structure.get("routes"):
        lines.append('        API["API Layer"]')
    lines.append("    end")
    lines.append('    subgraph Services["🔧 Services"]')
    for s in structure.get("services", [])[:6]:
        safe = s.replace("/", "_").replace(".", "_").replace("-", "_")
        lines.append(f'        {safe}["{s.split("/")[-1]}"]')
    if not structure.get("services"):
        lines.append('        SVC["Service Layer"]')
    lines.append("    end")
    lines.append("    Frontend --> Backend")
    lines.append("    Backend --> Services")
    return "\n".join(lines)


def _generate_folder_diagram(structure: dict) -> str:
    lines = ["graph LR"]
    tree = structure.get("folder_tree", [])
    top_dirs = set()
    for f in tree[:100]:
        parts = f["path"].split("/")
        if len(parts) >= 1:
            top_dirs.add(parts[0])
    for d in sorted(top_dirs)[:12]:
        safe = d.replace("-", "_").replace(".", "_")
        lines.append(f'    ROOT --> {safe}["{d}/"]')
    return "\n".join(lines)


def _generate_request_flow(structure: dict) -> str:
    lines = ["sequenceDiagram"]
    lines.append("    participant User")
    lines.append("    participant Frontend")
    lines.append("    participant API")
    lines.append("    participant Service")
    lines.append("    participant DB")
    lines.append("    User->>Frontend: Interact with UI")
    lines.append("    Frontend->>API: HTTP Request")
    lines.append("    API->>Service: Business Logic")
    lines.append("    Service->>DB: Query/Mutate")
    lines.append("    DB-->>Service: Result")
    lines.append("    Service-->>API: Response Data")
    lines.append("    API-->>Frontend: JSON Response")
    lines.append("    Frontend-->>User: Render UI")
    return "\n".join(lines)


def _generate_dependency_diagram(tech: dict) -> str:
    lines = ["graph TD"]
    lines.append('    APP["Application"]')
    for lang in tech.get("languages", [])[:5]:
        safe = lang.replace(" ", "_").replace("/", "_").replace(".", "_")
        lines.append(f'    APP --> {safe}["{lang}"]')
    for fw in tech.get("frameworks", [])[:5]:
        safe = fw.replace(" ", "_").replace("/", "_").replace(".", "_")
        lines.append(f'    APP --> {safe}["{fw}"]')
    for db in tech.get("databases", [])[:3]:
        safe = db.replace(" ", "_").replace("/", "_").replace(".", "_")
        lines.append(f'    APP --> {safe}["{db}"]')
    return "\n".join(lines)


def _generate_execution_flow(structure: dict, tech: dict) -> str:
    """Execution lifecycle diagram."""
    lines = ["graph TD"]
    lines.append('    START(["App Start"]) --> CONFIG["Load Config"]')
    lines.append('    CONFIG --> INIT["Initialize Services"]')
    if structure.get("routes"):
        lines.append('    INIT --> ROUTES["Register Routes"]')
        lines.append('    ROUTES --> LISTEN["Listen for Requests"]')
        lines.append('    LISTEN --> HANDLER["Route Handler"]')
        lines.append('    HANDLER --> SERVICE["Service Logic"]')
        lines.append('    SERVICE --> RESPONSE["Send Response"]')
    else:
        lines.append('    INIT --> RUN["Execute Main Logic"]')
        lines.append('    RUN --> OUTPUT["Produce Output"]')
    return "\n".join(lines)


def _generate_contributor_map(structure: dict) -> str:
    """What to read first as a contributor."""
    lines = ["graph LR"]
    lines.append('    START(["Start Here"]) --> README["README.md"]')
    if structure.get("entry_points"):
        ep = structure["entry_points"][0].split("/")[-1].replace(".", "_")
        lines.append(f'    README --> EP["{structure["entry_points"][0].split("/")[-1]}"]')
    else:
        lines.append('    README --> EP["Entry Point"]')
    if structure.get("routes"):
        lines.append(f'    EP --> ROUTES["Routes ({len(structure["routes"])} files)"]')
    if structure.get("services"):
        lines.append(f'    ROUTES --> SERVICES["Services ({len(structure["services"])} files)"]')
    if structure.get("components"):
        lines.append(f'    EP --> UI["Components ({len(structure["components"])} files)"]')
    return "\n".join(lines)


# ─── Report Generation (Deep & Contribution-Friendly) ────

def _summarize_file(path: str, content: str) -> dict:
    """Generate a rich summary for a single file based on its content."""
    lines = content.strip().splitlines()
    line_count = len(lines)
    name = path.split("/")[-1]
    ext = os.path.splitext(name)[1].lower()

    # Detect purpose from content signals
    purpose_signals = []
    lower_content = content[:4000].lower()

    if ext in (".py", ".ts", ".js", ".tsx", ".jsx"):
        if "def main" in lower_content or "if __name__" in lower_content:
            purpose_signals.append("Application entry point")
        if "router" in lower_content or "@app." in lower_content or "apiRouter" in lower_content:
            purpose_signals.append("API route definitions")
        if "class " in lower_content and ("model" in name.lower() or "schema" in name.lower()):
            purpose_signals.append("Data model / schema definitions")
        if "import " in lower_content and ("service" in name.lower()):
            purpose_signals.append("Business logic service")
        if "component" in name.lower() or "export default function" in lower_content or "export function" in lower_content:
            purpose_signals.append("UI component")
        if "useState" in lower_content or "useEffect" in lower_content:
            purpose_signals.append("React stateful component")
        if "test" in name.lower() or "spec" in name.lower():
            purpose_signals.append("Test file")
        if "config" in name.lower() or "settings" in name.lower():
            purpose_signals.append("Configuration")
        if "middleware" in name.lower():
            purpose_signals.append("Middleware layer")
        if "util" in name.lower() or "helper" in name.lower():
            purpose_signals.append("Utility / helper functions")

    # Extract key exports, functions, classes
    functions = []
    classes = []
    for line in lines[:200]:
        stripped = line.strip()
        if stripped.startswith("def ") or stripped.startswith("async def "):
            fn_name = stripped.split("(")[0].replace("def ", "").replace("async ", "").strip()
            if not fn_name.startswith("_"):
                functions.append(fn_name)
        elif stripped.startswith("class "):
            cls_name = stripped.split("(")[0].split(":")[0].replace("class ", "").strip()
            classes.append(cls_name)
        elif "export function " in stripped or "export default function " in stripped:
            fn_match = stripped.split("function ")[1].split("(")[0].strip() if "function " in stripped else ""
            if fn_match:
                functions.append(fn_match)

    purpose = "; ".join(purpose_signals[:3]) if purpose_signals else "General source file"

    return {
        "path": path,
        "name": name,
        "lines": line_count,
        "purpose": purpose,
        "functions": functions[:10],
        "classes": classes[:5],
        "importance": _score_file_importance(path, content, purpose_signals),
    }


def _score_file_importance(path: str, content: str, signals: list) -> int:
    """Score 0-100 how important this file is for understanding the repo."""
    score = 20
    name = path.split("/")[-1].lower()
    if name in ("main.py", "app.py", "index.ts", "index.js", "server.py", "page.tsx", "layout.tsx"):
        score += 30
    if "route" in name or "router" in name or "api" in name:
        score += 20
    if "service" in name:
        score += 15
    if name in ("package.json", "requirements.txt", "config.py", "settings.py"):
        score += 25
    if "entry point" in " ".join(signals).lower():
        score += 20
    lines = len(content.strip().splitlines())
    if lines > 50:
        score += 10
    if lines > 200:
        score += 5
    return min(100, score)


def _build_folder_explanations(structure: dict) -> list[dict]:
    """Explain what each top-level folder likely does."""
    tree = structure.get("folder_tree", [])
    folder_map: dict[str, list] = {}
    for f in tree:
        parts = f["path"].split("/")
        top = parts[0]
        folder_map.setdefault(top, []).append(f["path"])

    FOLDER_HINTS = {
        "src": "Main source code directory",
        "app": "Application core — may contain routes, pages, or entry points",
        "components": "Reusable UI components",
        "pages": "Page-level components or route views",
        "routes": "API route definitions / endpoint handlers",
        "services": "Business logic and service layer",
        "models": "Data models, schemas, and database entities",
        "lib": "Shared libraries, utilities, and helper functions",
        "utils": "Utility functions used across the codebase",
        "hooks": "Custom React hooks for state and side-effects",
        "store": "State management (Redux, Context, Zustand, etc.)",
        "config": "Configuration files and environment settings",
        "public": "Static assets served directly (images, fonts, etc.)",
        "tests": "Test suites and test utilities",
        "test": "Test suites and test utilities",
        "backend": "Backend / server-side code",
        "frontend": "Frontend / client-side code",
        "api": "API layer — endpoint handlers or client-side API calls",
        "middleware": "Middleware for request processing",
        "database": "Database configuration, migrations, and seeds",
        "scripts": "Build, deploy, or automation scripts",
        "docs": "Documentation files",
        "assets": "Static assets (images, styles, fonts)",
        "styles": "CSS / styling files",
        "types": "TypeScript type definitions",
        "schemas": "Data validation schemas",
        "views": "View templates or page components",
        "controllers": "Request controllers (MVC pattern)",
        "sandbox": "Sandboxed execution or isolated environments",
        "agent": "AI agent or automated task logic",
        "demo": "Demo data, scripts, or mock scenarios",
        "data": "Data storage, fixtures, or seed data",
    }

    explanations = []
    for folder in sorted(folder_map.keys())[:20]:
        file_count = len(folder_map[folder])
        hint = FOLDER_HINTS.get(folder.lower(), f"Contains {file_count} file(s)")
        explanations.append({
            "folder": folder,
            "file_count": file_count,
            "explanation": hint,
            "sample_files": [p.split("/")[-1] for p in folder_map[folder][:5]],
        })
    return explanations


def _generate_report(
    owner: str, repo: str, readme: str,
    tech: dict, structure: dict, file_contents: dict[str, str],
) -> dict:
    total = structure["total_files"]
    langs = ", ".join(tech.get("languages", ["Unknown"]))
    frameworks = ", ".join(tech.get("frameworks", [])) or "None detected"
    infra = ", ".join(tech.get("infrastructure", [])) or "None detected"
    styling = ", ".join(tech.get("styling", [])) or "None detected"
    databases = ", ".join(tech.get("databases", [])) or "None detected"

    # ─── README analysis ──────────────────────────────────
    readme_summary = ""
    readme_problem = ""
    has_readme = bool(readme and len(readme.strip()) > 20)
    if has_readme:
        paragraphs = [p.strip() for p in readme.split("\n\n") if p.strip()]
        readme_summary = paragraphs[0][:800] if paragraphs else ""
        # Try to find a "problem" or "about" section
        for p in paragraphs[1:5]:
            pl = p.lower()
            if any(k in pl for k in ["problem", "solves", "purpose", "why", "about", "what is"]):
                readme_problem = p[:500]
                break
        if not readme_problem and len(paragraphs) > 1:
            readme_problem = paragraphs[1][:500]

    # ─── Executive summary ────────────────────────────────
    what_it_does = readme_summary or f"A {langs} project with {total} source files."
    if tech.get("frameworks"):
        what_it_does += f" Built with {frameworks}."

    # ─── Problem statement ────────────────────────────────
    problem_statement = readme_problem or (
        f"Based on structural analysis, this appears to be a {langs} application "
        f"{'using ' + frameworks if frameworks != 'None detected' else ''}. "
        f"The README does not explicitly state the problem being solved, "
        f"so the purpose is inferred from the codebase structure and dependencies."
    )

    # ─── File summaries ───────────────────────────────────
    important_files = []
    for path, content in file_contents.items():
        if content:
            summary = _summarize_file(path, content)
            important_files.append(summary)
    important_files.sort(key=lambda x: x["importance"], reverse=True)

    # ─── Folder explanations ──────────────────────────────
    folder_explanations = _build_folder_explanations(structure)

    # ─── What to read first ───────────────────────────────
    read_first = []
    for f in important_files[:8]:
        if f["importance"] >= 40:
            read_first.append({
                "path": f["path"],
                "reason": f["purpose"],
                "importance": f["importance"],
            })

    # ─── Execution flow ──────────────────────────────────
    has_frontend = bool(structure.get("components")) or any(
        ".tsx" in f["path"] or ".jsx" in f["path"] for f in structure.get("folder_tree", [])[:100]
    )
    has_backend = bool(structure.get("routes")) or bool(structure.get("services"))

    if has_frontend and has_backend:
        execution_flow = (
            f"This is a full-stack application. The frontend ({', '.join(f for f in tech.get('frameworks', []) if f in ('React', 'Next.js', 'Vue', 'Angular', 'Svelte')) or 'UI layer'}) "
            f"communicates with the backend ({', '.join(f for f in tech.get('frameworks', []) if f in ('FastAPI', 'Express', 'Flask', 'Django')) or 'API layer'}) "
            f"via HTTP API calls. The backend processes requests through route handlers → service layer → data/storage, "
            f"then returns structured JSON responses that the frontend renders into the UI."
        )
        data_flow = (
            f"Data flows from user interaction in the UI → API client calls → "
            f"backend route handlers → service/business logic → database or file storage → "
            f"response back through the same chain. State management on the frontend "
            f"{'likely uses React hooks/context' if 'React' in str(tech.get('frameworks', [])) else 'handles local state'} "
            f"to keep the UI synchronized with backend data."
        )
    elif has_backend:
        execution_flow = (
            f"This is a backend/API application. Requests arrive at route handlers, "
            f"pass through any middleware, get processed by service functions, "
            f"interact with storage/databases, and return structured responses."
        )
        data_flow = "Data flows through: HTTP request → route handler → service logic → storage → response."
    else:
        execution_flow = (
            f"This appears to be a frontend-only or library project. "
            f"The main execution starts from the entry point files and flows through the component/module tree."
        )
        data_flow = "Data flows through component props, state management, and any client-side storage."

    # ─── Frontend-backend interaction ─────────────────────
    if has_frontend and has_backend:
        fb_interaction = (
            f"The frontend makes HTTP requests (likely using fetch or axios) to the backend API endpoints. "
            f"Routes are defined in {', '.join(f'`{r}`' for r in structure.get('routes', [])[:3]) or 'the route files'}. "
            f"The backend processes these requests through service functions in "
            f"{', '.join(f'`{s}`' for s in structure.get('services', [])[:3]) or 'the service layer'}, "
            f"and returns JSON responses. CORS is likely configured to allow cross-origin requests during development."
        )
    else:
        fb_interaction = "This project does not have a clear frontend-backend split, or both are in the same layer."

    # ─── Contributor guide ────────────────────────────────
    safe_to_edit = []
    avoid_editing = []
    for f in important_files:
        if f["importance"] < 50 and "config" not in f["path"].lower():
            safe_to_edit.append(f["path"])
        if f["importance"] >= 70 or "config" in f["path"].lower() or "main" in f["name"].lower():
            avoid_editing.append(f["path"])

    contributor_guide = {
        "start_reading": [f["path"] for f in read_first[:5]],
        "entry_points": structure.get("entry_points", [])[:5],
        "route_files": structure.get("routes", [])[:5],
        "business_logic": structure.get("services", [])[:5],
        "ui_files": structure.get("components", [])[:5],
        "safe_to_edit_first": safe_to_edit[:5],
        "avoid_unless_necessary": avoid_editing[:5],
        "typical_request_flow": (
            "User action → Frontend event handler → API call → Backend route → "
            "Service function → Data layer → Response → UI update"
        ),
        "first_contribution_tasks": [
            "Add a new unit test for an existing service function",
            "Improve error messages in API route handlers",
            "Add input validation to an existing endpoint",
            "Write JSDoc or docstrings for undocumented functions",
            "Add loading states or error handling in a UI component",
        ],
    }

    # ─── Health & confidence scores ───────────────────────
    health_score = _calculate_health_score(structure, tech, readme, file_contents)
    arch_confidence = min(100, 30 + (20 if has_frontend and has_backend else 10) +
                          (15 if structure.get("services") else 0) +
                          (15 if structure.get("routes") else 0) +
                          (10 if structure.get("configs") else 0) +
                          (10 if has_readme else 0))

    # ─── Module ranking ──────────────────────────────────
    module_ranking = []
    for mod in structure.get("modules", [])[:15]:
        file_count = sum(1 for f in structure.get("folder_tree", []) if f["path"].startswith(mod + "/"))
        module_ranking.append({"module": mod, "file_count": file_count})
    module_ranking.sort(key=lambda x: x["file_count"], reverse=True)

    return {
        "what_it_does": what_it_does,
        "problem_statement": problem_statement,
        "executive_summary": what_it_does,
        "tech_stack": tech,
        "languages": langs,
        "frameworks": frameworks,
        "infrastructure": infra,
        "styling": styling,
        "databases": databases,
        "total_files": total,
        "modules": structure.get("modules", []),
        "module_ranking": module_ranking[:10],
        "routes": structure.get("routes", []),
        "components": structure.get("components", []),
        "services": structure.get("services", []),
        "entry_points": structure.get("entry_points", []),
        "important_files": important_files[:20],
        "read_first": read_first[:6],
        "folder_explanations": folder_explanations,
        "execution_flow": execution_flow,
        "data_flow": data_flow,
        "frontend_backend_interaction": fb_interaction,
        "contributor_guide": contributor_guide,
        "readme_summary": readme_summary[:2000],
        "readme_full": readme[:5000] if readme else "",
        "has_readme": has_readme,
        "health_score": health_score,
        "architecture_confidence": arch_confidence,
        "risks": _detect_risks(structure, tech, file_contents),
        "strengths": _detect_strengths(structure, tech, readme, file_contents),
        "suggested_improvements": _suggest_improvements(structure, tech, readme, file_contents),
        "conclusion": _build_conclusion(owner, repo, tech, structure, health_score),
    }


def _calculate_health_score(structure, tech, readme, file_contents) -> int:
    score = 30
    if readme and len(readme.strip()) > 50:
        score += 15
    if structure.get("configs"):
        score += 10
    if structure.get("services"):
        score += 10
    if structure.get("routes"):
        score += 5
    if structure.get("components"):
        score += 5
    if any("test" in f["path"].lower() for f in structure.get("folder_tree", [])):
        score += 10
    if tech.get("infrastructure"):
        score += 5
    if structure["total_files"] > 5:
        score += 5
    if any(".env" in f["path"] for f in structure.get("folder_tree", [])):
        score += 5
    return min(100, score)


def _detect_risks(structure, tech, file_contents) -> list[str]:
    risks = []
    if not structure.get("configs"):
        risks.append("No configuration files detected — may be difficult to configure for different environments")
    if structure["total_files"] > 200:
        risks.append("Large codebase with 200+ files — consider modularization to reduce coupling")
    if not any("test" in f["path"].lower() for f in structure.get("folder_tree", [])):
        risks.append("No test files found — low test coverage increases regression risk")
    if not any(".env" in f["path"] or "config" in f["path"].lower() for f in structure.get("folder_tree", [])):
        risks.append("No environment configuration — secrets or settings may be hardcoded")
    if not structure.get("services") and structure.get("routes"):
        risks.append("Routes exist without a dedicated service layer — business logic may be mixed into handlers")
    # Check for large files
    for path, content in file_contents.items():
        if len(content.splitlines()) > 500:
            risks.append(f"`{path}` is very large ({len(content.splitlines())} lines) — consider splitting")
            break
    if not any("middleware" in f["path"].lower() for f in structure.get("folder_tree", [])):
        if structure.get("routes"):
            risks.append("No middleware detected — auth, logging, and error handling may be inconsistent")
    return risks[:8]


def _detect_strengths(structure, tech, readme, file_contents=None) -> list[str]:
    strengths = []
    if readme and len(readme.strip()) > 100:
        strengths.append("Well-documented with a detailed README file")
    elif readme:
        strengths.append("Has basic README documentation")
    if tech.get("infrastructure"):
        strengths.append(f"Production-ready infrastructure: {', '.join(tech['infrastructure'])}")
    if structure.get("services"):
        strengths.append("Clean service-layer architecture separating business logic from routes")
    if structure.get("routes") and structure.get("components"):
        strengths.append("Clear frontend/backend separation with dedicated route and component files")
    if any("test" in f["path"].lower() for f in structure.get("folder_tree", [])):
        strengths.append("Has test infrastructure for quality assurance")
    if tech.get("styling"):
        strengths.append(f"Consistent styling approach using {', '.join(tech['styling'])}")
    if structure.get("configs"):
        strengths.append("Proper configuration management with dedicated config files")
    if len(structure.get("modules", [])) >= 3:
        strengths.append(f"Well-modularized codebase with {len(structure['modules'])} distinct modules")
    return strengths[:8]


def _suggest_improvements(structure, tech, readme, file_contents) -> list[str]:
    improvements = []
    if not readme or len(readme.strip()) < 50:
        improvements.append("Add a comprehensive README with setup instructions, features, and contributing guide")
    if not any("test" in f["path"].lower() for f in structure.get("folder_tree", [])):
        improvements.append("Add unit and integration tests to ensure code reliability")
    if not tech.get("infrastructure"):
        improvements.append("Add Docker or CI/CD configuration for consistent deployments")
    if not structure.get("services") and structure.get("routes"):
        improvements.append("Extract business logic from route handlers into a dedicated service layer")
    if structure["total_files"] > 150 and len(structure.get("modules", [])) < 4:
        improvements.append("Consider further modularization — the codebase is large relative to module count")
    if not any("type" in f["path"].lower() or "schema" in f["path"].lower() for f in structure.get("folder_tree", [])):
        improvements.append("Add TypeScript types or validation schemas for better type safety")
    improvements.append("Add API documentation (e.g., OpenAPI/Swagger) for all backend endpoints")
    improvements.append("Implement structured logging for better debugging in production")
    return improvements[:8]


def _build_conclusion(owner, repo, tech, structure, health_score) -> str:
    langs = ", ".join(tech.get("languages", []))
    fw = ", ".join(tech.get("frameworks", []))
    total = structure["total_files"]
    quality = "well-structured" if health_score >= 70 else "functional but could benefit from improvement"
    return (
        f"**{owner}/{repo}** is a {quality} {langs} project "
        f"{'built with ' + fw + ' ' if fw else ''}containing {total} source files. "
        f"It scores **{health_score}/100** on the health index. "
        f"The codebase shows {len(structure.get('modules', []))} distinct modules with "
        f"{len(structure.get('routes', []))} route files, {len(structure.get('services', []))} services, "
        f"and {len(structure.get('components', []))} components. "
        f"See the contributor guide above for onboarding recommendations."
    )


# ─── Q&A Engine ───────────────────────────────────────────

def _answer_question(question: str, report: dict, structure: dict,
                     file_contents: dict[str, str]) -> str:
    q = question.lower().strip()

    if any(k in q for k in ["what does", "what is", "purpose", "about"]):
        return (f"**{report.get('what_it_does', 'Unknown')}**\n\n"
                f"**Tech Stack:** {report.get('languages', 'N/A')}\n"
                f"**Frameworks:** {report.get('frameworks', 'N/A')}\n"
                f"**Files:** {report.get('total_files', 0)}")

    if any(k in q for k in ["tech stack", "technology", "built with", "language"]):
        tech = report.get("tech_stack", {})
        parts = [f"**Languages:** {', '.join(tech.get('languages', []))}",
                 f"**Frameworks:** {', '.join(tech.get('frameworks', []))}",
                 f"**Infrastructure:** {', '.join(tech.get('infrastructure', []))}",
                 f"**Dependencies:** {', '.join(tech.get('dependencies', [])[:10])}"]
        return "\n".join(parts)

    if any(k in q for k in ["route", "api", "endpoint"]):
        routes = report.get("routes", [])
        if routes:
            return "**API Routes/Endpoints:**\n" + "\n".join(f"- `{r}`" for r in routes[:15])
        return "No explicit route files detected in this repository."

    if any(k in q for k in ["component", "ui", "frontend", "page"]):
        comps = report.get("components", [])
        if comps:
            return "**UI Components:**\n" + "\n".join(f"- `{c}`" for c in comps[:15])
        return "No explicit component files detected."

    if any(k in q for k in ["structure", "folder", "tree", "architecture"]):
        modules = report.get("modules", [])
        return ("**Project Modules:**\n" + "\n".join(f"- `{m}/`" for m in modules[:15]) +
                f"\n\n**Total files:** {report.get('total_files', 0)}")

    if any(k in q for k in ["entry", "start", "main", "run"]):
        eps = report.get("entry_points", [])
        if eps:
            return "**Entry Points:**\n" + "\n".join(f"- `{e}`" for e in eps)
        return "No clear entry points detected."

    if any(k in q for k in ["risk", "issue", "problem", "gap"]):
        risks = report.get("risks", [])
        if risks:
            return "**Detected Risks:**\n" + "\n".join(f"- ⚠️ {r}" for r in risks)
        return "No major risks detected."

    if any(k in q for k in ["strength", "good", "positive"]):
        strengths = report.get("strengths", [])
        if strengths:
            return "**Strengths:**\n" + "\n".join(f"- ✅ {s}" for s in strengths)
        return "Analysis ongoing."

    # File-specific question
    for f_path, content in file_contents.items():
        fname = f_path.split("/")[-1].lower()
        if fname in q:
            lines = content.splitlines()
            return (f"**`{f_path}`** ({len(lines)} lines)\n\n"
                    f"```\n{content[:2000]}\n```")

    return (f"Based on my analysis of **{report.get('what_it_does', 'this repository')}**:\n\n"
            f"This is a {report.get('languages', 'multi-language')} project with "
            f"{report.get('total_files', 0)} files. "
            f"The main frameworks are {report.get('frameworks', 'not detected')}.\n\n"
            f"Try asking about: tech stack, routes, components, structure, risks, or entry points.")


# ─── Main Pipeline ────────────────────────────────────────

async def analyze_repository(repo_url: str, token: str = "") -> dict:
    """Full repo analysis pipeline. Returns a complete report."""
    owner, repo = _parse_github_url(repo_url)
    report_id = hashlib.md5(f"{owner}/{repo}".encode()).hexdigest()[:12]

    # Check cache
    cached = _load_report(report_id)
    if cached:
        logger.info("repo_explorer.cache_hit", repo=f"{owner}/{repo}")
        return cached

    logger.info("repo_explorer.ingesting", repo=f"{owner}/{repo}")

    # Fetch tree
    tree = await _fetch_repo_tree(owner, repo, token)
    if not tree:
        raise ValueError("Could not fetch repository tree. Check URL and access.")

    # Filter relevant files
    relevant = []
    for f in tree:
        if f.get("type") != "blob":
            continue
        parts = f["path"].split("/")
        if any(p in SKIP_DIRS for p in parts):
            continue
        ext = os.path.splitext(f["path"])[1].lower()
        if ext in SKIP_EXTS:
            continue
        relevant.append(f)

    # Fetch key file contents (top priority files only)
    priority_names = {
        "package.json", "requirements.txt", "pyproject.toml", "tsconfig.json",
        "README.md", "readme.md", "main.py", "app.py", "index.ts", "index.js",
        "server.py", "config.py", "settings.py", "next.config.js", "next.config.mjs",
        "vite.config.ts", "Dockerfile", "docker-compose.yml", ".env.example",
    }
    fetch_paths = [f["path"] for f in relevant
                   if f["path"].split("/")[-1] in priority_names][:25]
    # Also fetch first few route/service/component files
    for f in relevant:
        p = f["path"].lower()
        if len(fetch_paths) >= 35:
            break
        if any(k in p for k in ["route", "service", "component", "page.tsx", "layout.tsx"]):
            if f["path"] not in fetch_paths:
                fetch_paths.append(f["path"])

    file_contents = {}
    tasks = [_fetch_file_content(owner, repo, p, token) for p in fetch_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for path, content in zip(fetch_paths, results):
        if isinstance(content, str) and content:
            file_contents[path] = content

    readme = await _fetch_readme(owner, repo, token)

    # Analysis
    tech = _detect_tech_stack(tree, file_contents)
    structure = _analyze_structure(tree, file_contents)
    report = _generate_report(owner, repo, readme, tech, structure, file_contents)

    # ── AutoMerge Mentor: LLM enhancement ──
    from app.config import settings
    if settings.has_llm:
        try:
            from app.services import llm_service
            paths = [f["path"] for f in tree]
            ai_summary = await llm_service.generate_repo_summary(repo, tech, paths, readme)
            if ai_summary:
                report["what_it_does"] = ai_summary
                report["llm_enhanced"] = True
        except Exception as e:
            logger.warning("repo_explorer.llm_summary_failed", error=str(e)[:200])

    # Diagrams
    diagrams = {
        "architecture": _generate_architecture_diagram(structure, tech),
        "folder_tree": _generate_folder_diagram(structure),
        "request_flow": _generate_request_flow(structure),
        "dependencies": _generate_dependency_diagram(tech),
        "execution_flow": _generate_execution_flow(structure, tech),
        "contributor_map": _generate_contributor_map(structure),
    }

    result = {
        "id": report_id,
        "repo_url": repo_url,
        "owner": owner,
        "repo_name": repo,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "report": report,
        "structure": structure,
        "diagrams": diagrams,
        "file_contents": {k: v[:5000] for k, v in file_contents.items()},
        "readme": readme[:5000],
        "qa_history": [],
    }

    _save_report(report_id, result)

    # Update history
    history = _load_history()
    history = [h for h in history if h.get("id") != report_id]
    history.insert(0, {
        "id": report_id,
        "repo_url": repo_url,
        "owner": owner,
        "repo_name": repo,
        "analyzed_at": result["analyzed_at"],
        "languages": report.get("languages", ""),
        "total_files": report.get("total_files", 0),
        "health_score": report.get("health_score", 0),
    })
    _save_history(history[:50])

    # Push to shared context so Devमित्र widget gains repo awareness
    shared_context.update_repo_explorer_context(
        report_id=report_id,
        repo_name=repo,
        summary=report.get("what_it_does", ""),
        tech_stack=tech,
    )

    return result


async def ask_repo_question(report_id: str, question: str) -> dict:
    """Answer a question about a previously analyzed repo."""
    data = _load_report(report_id)
    if not data:
        return {"answer": "Report not found. Please analyze the repository first.", "sources": []}

    answer = None
    from app.config import settings
    if settings.has_llm:
        try:
            from app.services import llm_service
            context = {
                "repo_name": data.get("repo_name", ""),
                "repo_summary": data.get("report", {}).get("what_it_does", ""),
                "analysis_summary": f"Languages: {data.get('report', {}).get('languages', '')}, Files: {data.get('structure', {}).get('total_files', 0)}",
            }
            
            # If asking about a specific file, include it
            for f_path, content in data.get("file_contents", {}).items():
                if f_path.split("/")[-1].lower() in question.lower():
                    context["filename"] = f_path
                    context["code"] = content[:1500]
                    break
                    
            answer = await llm_service.generate_chat_reply(question, context)
        except Exception as e:
            logger.warning("repo_explorer.llm_qa_failed", error=str(e)[:200])

    if not answer:
        answer = _answer_question(
            question, data["report"], data["structure"], data.get("file_contents", {})
        )

    # Persist Q&A
    data.setdefault("qa_history", []).append({
        "question": question,
        "answer": answer,
        "asked_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_report(report_id, data)

    return {"answer": answer, "sources": data["report"].get("entry_points", [])[:5]}


def get_history() -> list[dict]:
    return _load_history()


def get_report(report_id: str) -> Optional[dict]:
    return _load_report(report_id)


def delete_history_item(report_id: str) -> bool:
    history = _load_history()
    history = [h for h in history if h.get("id") != report_id]
    _save_history(history)
    p = REPORTS_DIR / f"{report_id}.json"
    if p.exists():
        p.unlink()
    return True
