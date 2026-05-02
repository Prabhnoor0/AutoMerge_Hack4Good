"""
AR Debug Explorer — Scene Visualization Service

Pure transformation layer that converts existing structured outputs
(Studio, Repo Explorer, Deploy, Battle) into AR-compatible scene graphs.

Rules:
- Never executes code
- Never calls eval
- Never modifies source data
- Deterministic and safe
- Masks secrets/tokens
"""

import hashlib
import json
import re
import time
import structlog
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = structlog.get_logger("automerge.ar")

# ─── Persistence ──────────────────────────────────────────

DATA_DIR = Path("./data/ar")
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "history.json"


def _gen_scene_id(source_type: str, source_id: str) -> str:
    h = hashlib.md5(f"{source_type}:{source_id}".encode()).hexdigest()[:10]
    return f"ar_{h}"


def _load_history() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return []


def _save_history(history: list[dict]):
    HISTORY_FILE.write_text(json.dumps(history[:200], indent=2, default=str))


def _record_view(scene_id: str, source_type: str, source_id: str, title: str, summary: str):
    """Track scene generation in history."""
    history = _load_history()
    # Update existing or insert
    existing = next((h for h in history if h.get("scene_id") == scene_id), None)
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        existing["last_viewed_at"] = now
        existing["view_count"] = existing.get("view_count", 0) + 1
        existing["title"] = title
    else:
        history.insert(0, {
            "scene_id": scene_id,
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "summary": summary[:300],
            "created_at": now,
            "last_viewed_at": now,
            "view_count": 1,
        })
    _save_history(history)


def get_history() -> list[dict]:
    return _load_history()


def delete_history_item(scene_id: str) -> bool:
    history = _load_history()
    new = [h for h in history if h.get("scene_id") != scene_id]
    if len(new) < len(history):
        _save_history(new)
        return True
    return False


# ─── Sanitization ─────────────────────────────────────────

_SECRET_RE = re.compile(
    r'(?i)(api[_-]?key|secret|password|token|auth|private_key|credential)\s*[=:]\s*\S+',
)


def _mask(text: str) -> str:
    if not text:
        return text
    return _SECRET_RE.sub("[REDACTED]", text)


# ─── Scene Model Builder ─────────────────────────────────

def _node(id: str, label: str, type: str, status: str = "default",
          color: str = "#4f8ef7", description: str = "",
          severity: str = "", source_line: int | None = None,
          source_ref: str = "", metadata: dict | None = None,
          position_hint: dict | None = None) -> dict:
    return {
        "id": id,
        "label": label,
        "type": type,
        "status": status,
        "color": color,
        "position_hint": position_hint or {},
        "description": _mask(description),
        "source_line": source_line,
        "source_ref": source_ref,
        "severity": severity,
        "metadata": metadata or {},
    }


def _edge(source: str, target: str, label: str = "",
          weight: float = 1.0, style: str = "solid") -> dict:
    return {
        "from": source,
        "to": target,
        "label": label,
        "weight": weight,
        "style": style,
    }


def _timeline_step(label: str, detail: str = "", status: str = "default",
                   source_ref: str = "", timestamp: str = "") -> dict:
    return {
        "label": label,
        "timestamp": timestamp,
        "detail": _mask(detail),
        "status": status,
        "source_ref": source_ref,
    }


def _build_scene(source_type: str, source_id: str, title: str,
                 summary: str, nodes: list, edges: list,
                 timeline: list, metrics: list, warnings: list,
                 annotations: list, confidence: float = 0,
                 fallback_text: str = "") -> dict:
    scene_id = _gen_scene_id(source_type, source_id)
    now = datetime.now(timezone.utc).isoformat()
    _record_view(scene_id, source_type, source_id, title, summary)
    return {
        "scene_id": scene_id,
        "source_type": source_type,
        "source_id": source_id,
        "title": title,
        "summary": _mask(summary),
        "confidence": confidence,
        "nodes": nodes,
        "edges": edges,
        "timeline": timeline,
        "metrics": metrics,
        "warnings": [_mask(w) for w in warnings],
        "annotations": annotations,
        "fallback_text": _mask(fallback_text),
        "created_at": now,
        "updated_at": now,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STUDIO → AR SCENE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def studio_to_scene(job_id: str, result: dict) -> dict:
    """Transform a Studio analysis result into an AR scene."""
    nodes = []
    edges = []
    timeline = []
    metrics = []
    warnings = []
    annotations = []

    lang = result.get("language", "unknown")
    root_cause = result.get("root_cause", "No root cause")
    confidence = result.get("confidence", 0)
    issues = result.get("issues", [])

    # ── Root Cause Node (center)
    nodes.append(_node(
        "root_cause", root_cause[:80], "root_cause",
        status="error" if issues else "success",
        color="#ef4444" if issues else "#22c55e",
        description=root_cause,
        position_hint={"x": 0, "y": 0, "z": 0, "layer": "center"},
    ))

    # ── Issue Nodes
    sev_colors = {"error": "#ef4444", "warning": "#f59e0b", "bug": "#f97316",
                  "security": "#a855f7", "info": "#3b82f6"}
    for i, issue in enumerate(issues[:15]):
        sev = issue.get("severity", "info")
        nid = f"issue_{i}"
        nodes.append(_node(
            nid, issue.get("message", "Issue")[:60], "issue",
            status=sev, color=sev_colors.get(sev, "#6b7280"),
            description=issue.get("explanation", ""),
            severity=sev,
            source_line=issue.get("line"),
            source_ref=issue.get("source_line", ""),
            metadata={"fix_hint": issue.get("fix_hint", ""), "category": issue.get("category", "")},
            position_hint={"x": 0, "y": 0, "z": 0, "layer": "issues", "index": i},
        ))
        edges.append(_edge("root_cause", nid, f"causes", style="dashed"))

    # ── Fix Node
    if result.get("diff_text"):
        changes = result.get("changes", [])
        nodes.append(_node(
            "fix", f"Fix: {len(changes)} change(s)", "fix",
            status="success", color="#22c55e",
            description=result.get("fix_explanation", ""),
            position_hint={"x": 0, "y": 0, "z": 0, "layer": "fix"},
        ))
        edges.append(_edge("root_cause", "fix", "resolved by"))

    # ── Validation Node
    v = result.get("validation")
    if v:
        passed = v.get("tests_passed", 0)
        total = v.get("tests_total", 0)
        v_status = "success" if v.get("status") == "passed" else "warning"
        nodes.append(_node(
            "validation", f"Validation: {passed}/{total} passed", "checkpoint",
            status=v_status,
            color="#22c55e" if v_status == "success" else "#f59e0b",
            description=v.get("stdout", "")[:500],
            metadata={"re_parse_backend": v.get("re_parse_backend", "")},
            position_hint={"x": 0, "y": 0, "z": 0, "layer": "validation"},
        ))
        if result.get("diff_text"):
            edges.append(_edge("fix", "validation", "validated"))

    # ── Reasoning Trace → Timeline
    trace = result.get("reasoning_trace", "")
    for line in trace.split("\n"):
        line = line.strip()
        if line:
            status = "success" if "passed" in line.lower() or "clean" in line.lower() else "info"
            if "error" in line.lower() or "fail" in line.lower():
                status = "error"
            timeline.append(_timeline_step(line, status=status))

    # ── Metrics
    metrics.append({"label": "Confidence", "value": f"{confidence:.0%}", "color": "#4f8ef7"})
    metrics.append({"label": "Language", "value": lang.upper(), "color": "#8b5cf6"})
    metrics.append({"label": "Issues", "value": str(len(issues)), "color": "#ef4444" if issues else "#22c55e"})
    if result.get("duration_ms"):
        metrics.append({"label": "Duration", "value": f"{result['duration_ms']}ms", "color": "#6b7280"})

    # ── AI Mentor Annotations
    for key, label in [("ai_explanation", "AI Explanation"), ("ai_fix_hint", "AI Fix Hint"),
                       ("ai_root_cause", "AI Root Cause"), ("ai_test_suggestion", "AI Test")]:
        val = result.get(key, "")
        if val:
            annotations.append({"label": label, "content": _mask(val), "type": "ai"})

    # ── Refactor / Quality
    for s in result.get("refactor_suggestions", [])[:5]:
        annotations.append({"label": f"Refactor: {s.get('category','')}", "content": s.get("suggestion",""), "type": "refactor"})
    for s in result.get("quality_suggestions", [])[:5]:
        annotations.append({"label": f"Quality: {s.get('category','')}", "content": s.get("suggestion",""), "type": "quality"})

    fallback = f"Studio Analysis: {root_cause}\nLanguage: {lang}\nIssues: {len(issues)}\nConfidence: {confidence:.0%}"
    return _build_scene("studio", job_id, f"Studio: {lang.title()} Analysis",
                        root_cause, nodes, edges, timeline, metrics, warnings,
                        annotations, confidence, fallback)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REPO EXPLORER → AR SCENE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def repo_to_scene(report_id: str, data: dict) -> dict:
    nodes = []
    edges = []
    timeline = []
    metrics = []
    warnings = []
    annotations = []

    report = data.get("report", {})
    structure = data.get("structure", {})
    repo_name = data.get("repo_name", "Repository")

    summary = report.get("what_it_does", "Repository analysis")
    health = report.get("health_score", 0)
    total_files = report.get("total_files", 0)

    # ── Root Node
    nodes.append(_node(
        "repo_root", repo_name, "root",
        status="success" if health >= 70 else "warning",
        color="#4f8ef7",
        description=summary,
        position_hint={"x": 0, "y": 0, "z": 0, "layer": "center"},
    ))

    # ── Module/Folder Nodes
    modules = report.get("modules", [])
    for i, mod in enumerate(modules[:12]):
        nid = f"mod_{i}"
        nodes.append(_node(
            nid, mod, "folder",
            status="default", color="#8b5cf6",
            position_hint={"x": 0, "y": 0, "z": 0, "layer": "modules", "index": i},
        ))
        edges.append(_edge("repo_root", nid, "contains"))

    # ── Entry Points
    eps = report.get("entry_points", [])
    for i, ep in enumerate(eps[:5]):
        nid = f"entry_{i}"
        nodes.append(_node(
            nid, ep, "entry_point",
            status="highlight", color="#22c55e",
            position_hint={"x": 0, "y": 0, "z": 0, "layer": "entry_points", "index": i},
        ))
        edges.append(_edge("repo_root", nid, "starts from", style="dashed"))

    # ── Routes
    routes = report.get("routes", [])
    for i, route in enumerate(routes[:10]):
        nid = f"route_{i}"
        nodes.append(_node(nid, route, "route", color="#06b6d4",
                           position_hint={"x": 0, "y": 0, "z": 0, "layer": "routes", "index": i}))

    # ── Components
    comps = report.get("components", [])
    for i, comp in enumerate(comps[:10]):
        nid = f"comp_{i}"
        nodes.append(_node(nid, comp, "component", color="#f59e0b",
                           position_hint={"x": 0, "y": 0, "z": 0, "layer": "components", "index": i}))

    # ── Risks
    risks = report.get("risks", [])
    for r in risks:
        warnings.append(r)

    # ── Strengths
    strengths = report.get("strengths", [])
    for s in strengths:
        annotations.append({"label": "Strength", "content": s, "type": "strength"})

    # ── Metrics
    metrics.append({"label": "Health", "value": str(health), "color": "#22c55e" if health >= 70 else "#f59e0b"})
    metrics.append({"label": "Files", "value": str(total_files), "color": "#6b7280"})
    metrics.append({"label": "Languages", "value": report.get("languages", ""), "color": "#8b5cf6"})

    fallback = f"Repo: {repo_name}\n{summary}\nHealth: {health}/100\nFiles: {total_files}"
    return _build_scene("repo", report_id, f"Repo: {repo_name}",
                        summary, nodes, edges, timeline, metrics,
                        warnings, annotations, health / 100, fallback)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DEPLOY → AR SCENE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def deploy_to_scene(run_id: str, run_data: dict, analysis: dict | None = None) -> dict:
    nodes = []
    edges = []
    timeline = []
    metrics = []
    warnings = []
    annotations = []

    repo_name = run_data.get("repo_name", "Project")
    platform = run_data.get("platform_name", run_data.get("platform", ""))
    status = run_data.get("status", "unknown")
    readiness = run_data.get("readiness_score", 0)

    # ── Main Deploy Node
    s_color = "#22c55e" if status == "deployed" else "#ef4444" if status == "failed" else "#f59e0b"
    nodes.append(_node(
        "deploy_main", f"Deploy: {repo_name}", "deploy",
        status=status, color=s_color,
        description=f"Platform: {platform}\nStatus: {status}",
        position_hint={"x": 0, "y": 0, "z": 0, "layer": "center"},
    ))

    # ── Platform Node
    nodes.append(_node(
        "platform", platform or "Unknown Platform", "platform",
        status="default", color="#8b5cf6",
        position_hint={"x": 0, "y": 0, "z": 0, "layer": "platform"},
    ))
    edges.append(_edge("deploy_main", "platform", "deploys to"))

    # ── Simulation checks from analysis
    if analysis:
        sim = analysis.get("simulation", {})
        checks = sim.get("checks", [])
        for i, ck in enumerate(checks[:10]):
            ck_status = ck.get("status", "info")
            ck_color = {"pass": "#22c55e", "fail": "#ef4444", "warn": "#f59e0b"}.get(ck_status, "#3b82f6")
            nid = f"check_{i}"
            nodes.append(_node(
                nid, ck.get("name", "Check"), "check",
                status=ck_status, color=ck_color,
                description=ck.get("detail", ""),
                position_hint={"x": 0, "y": 0, "z": 0, "layer": "checks", "index": i},
            ))
            edges.append(_edge("deploy_main", nid, "verified"))

        # Classification
        clf = analysis.get("classification", {})
        if clf:
            annotations.append({"label": "Project Type", "content": clf.get("project_type", ""), "type": "classification"})
            for w in clf.get("warnings", []):
                warnings.append(w)

        # Env scan
        env = analysis.get("env_scan", {})
        missing = env.get("missing_vars", [])
        if missing:
            warnings.append(f"Missing env vars: {', '.join(missing[:5])}")

    # ── Deploy Logs → Timeline
    logs = run_data.get("logs", [])
    for log in logs[:20]:
        st = "success" if "✓" in log or "success" in log.lower() else "info"
        if "✗" in log or "error" in log.lower() or "fail" in log.lower():
            st = "error"
        timeline.append(_timeline_step(_mask(log), status=st))

    # ── Metrics
    metrics.append({"label": "Readiness", "value": str(readiness), "color": "#22c55e" if readiness >= 70 else "#ef4444"})
    metrics.append({"label": "Status", "value": status.upper(), "color": s_color})
    metrics.append({"label": "Platform", "value": platform, "color": "#8b5cf6"})

    if run_data.get("error"):
        warnings.append(_mask(run_data["error"]))

    fallback = f"Deploy: {repo_name} → {platform}\nStatus: {status}\nReadiness: {readiness}/100"
    return _build_scene("deploy", run_id, f"Deploy: {repo_name}",
                        f"Deploying to {platform} — {status}",
                        nodes, edges, timeline, metrics, warnings,
                        annotations, readiness / 100, fallback)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BATTLE → AR SCENE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def battle_to_scene(session_id: str, session: dict) -> dict:
    nodes = []
    edges = []
    timeline = []
    metrics = []
    warnings = []
    annotations = []

    challenge = session.get("challenge", {})
    participants = session.get("participants", [])
    status = session.get("status", "unknown")
    winner_id = session.get("winner")

    title_text = challenge.get("title", "Battle")

    # ── Challenge Node (center)
    nodes.append(_node(
        "challenge", title_text, "challenge",
        status="active" if status == "running" else "finished",
        color="#f59e0b",
        description=challenge.get("description", ""),
        metadata={"difficulty": challenge.get("difficulty", ""), "language": challenge.get("language", "")},
        position_hint={"x": 0, "y": 0, "z": 0, "layer": "center"},
    ))

    # ── Player Nodes
    colors = ["#4f8ef7", "#ef4444", "#22c55e", "#8b5cf6"]
    for i, p in enumerate(participants):
        pid = p.get("id", f"player_{i}")
        is_winner = pid == winner_id
        score = (p.get("score") or {}).get("total", 0)
        p_color = "#fbbf24" if is_winner else colors[i % len(colors)]
        nodes.append(_node(
            pid, p.get("name", f"Player {i+1}"), "player",
            status="winner" if is_winner else "submitted" if p.get("submitted") else "active",
            color=p_color,
            description=f"Score: {score}" if score else "",
            metadata={
                "is_host": p.get("is_host", False),
                "submitted": p.get("submitted", False),
                "score": score,
                "time_taken": (p.get("submission") or {}).get("time_taken"),
            },
            position_hint={"x": 0, "y": 0, "z": 0, "layer": "players", "index": i},
        ))
        edges.append(_edge("challenge", pid, "competes"))

        # Score breakdown
        score_data = p.get("score")
        if score_data and isinstance(score_data, dict):
            for line in score_data.get("breakdown", []):
                annotations.append({"label": f"{p.get('name','')}: {line}", "content": "", "type": "score"})

    # ── Timeline
    if session.get("created_at"):
        timeline.append(_timeline_step("Battle Created", status="info", timestamp=session["created_at"]))
    if session.get("started_at"):
        timeline.append(_timeline_step("Battle Started", status="active", timestamp=session["started_at"]))
    for p in participants:
        sub = p.get("submission")
        if sub and sub.get("submitted_at"):
            timeline.append(_timeline_step(
                f"{p.get('name','')} Submitted ({sub.get('time_taken',0):.0f}s)",
                status="success", timestamp=sub["submitted_at"]
            ))
    if session.get("finished_at"):
        timeline.append(_timeline_step("Battle Finished", status="finished", timestamp=session["finished_at"]))

    # ── Metrics
    metrics.append({"label": "Status", "value": status.upper(), "color": "#f59e0b"})
    metrics.append({"label": "Time Limit", "value": f"{session.get('time_limit', 300)}s", "color": "#6b7280"})
    metrics.append({"label": "Players", "value": str(len(participants)), "color": "#4f8ef7"})
    if winner_id:
        winner_name = next((p.get("name", "") for p in participants if p.get("id") == winner_id), "")
        metrics.append({"label": "Winner", "value": winner_name, "color": "#fbbf24"})

    fallback = f"Battle: {title_text}\nStatus: {status}\nPlayers: {len(participants)}"
    return _build_scene("battle", session_id, f"Battle: {title_text}",
                        f"BugFix Arena — {title_text}",
                        nodes, edges, timeline, metrics, warnings,
                        annotations, 0, fallback)


# ─── Fallback Scene ───────────────────────────────────────

def error_scene(source_type: str, source_id: str, error_msg: str) -> dict:
    """Generate a graceful error/fallback scene."""
    return _build_scene(
        source_type, source_id,
        f"Error loading {source_type} scene",
        error_msg,
        nodes=[_node("error", "Data unavailable", "error", status="error", color="#ef4444",
                      description=error_msg)],
        edges=[], timeline=[], metrics=[], warnings=[error_msg],
        annotations=[], confidence=0,
        fallback_text=f"Could not load {source_type} scene for {source_id}: {error_msg}",
    )
