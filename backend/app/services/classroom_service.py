"""
Classroom Service Module

Generates learning reports from the user's debugging history.
Analyzes jobs, failures, bug patterns, and root causes to identify
recurring weakness areas and produce structured learning reports.
"""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, BugPattern, ClassroomReport, generate_id, utc_now


# ─── Topic Knowledge Base ────────────────────────────────────
# Maps failure patterns to human-friendly topic names, categories,
# explanations, and curated real resources.

TOPIC_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "async_handling": {
        "topic_name": "Async & Promise Handling",
        "topic_category": "concurrency",
        "why_it_matters": (
            "Async bugs cause race conditions, unhandled promise rejections, and silent failures. "
            "They are among the hardest bugs to reproduce because they depend on timing."
        ),
        "resources": [
            {
                "title": "JavaScript Async/Await - The Modern Way",
                "url": "https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Asynchronous/Promises",
                "type": "docs",
                "why_this_helps": "Official MDN guide covering Promises and async/await from fundamentals to advanced patterns.",
            },
            {
                "title": "Python asyncio Documentation",
                "url": "https://docs.python.org/3/library/asyncio.html",
                "type": "docs",
                "why_this_helps": "Complete reference for Python's async runtime, event loops, and task management.",
            },
            {
                "title": "Fireship — Async Await in 100 Seconds",
                "url": "https://www.youtube.com/watch?v=vn3tm0quoqE",
                "type": "youtube",
                "why_this_helps": "Extremely fast visual explainer to solidify the mental model of async execution.",
            },
            {
                "title": "Traversy Media — Async JS Crash Course",
                "url": "https://www.youtube.com/watch?v=PoRJizFvM7s",
                "type": "youtube",
                "why_this_helps": "Practical walkthrough of callbacks, promises, and async/await with real examples.",
            },
        ],
    },
    "type_safety": {
        "topic_name": "Type Safety & Annotations",
        "topic_category": "type_system",
        "why_it_matters": (
            "Missing or incorrect type annotations cause silent runtime crashes and make code harder to refactor. "
            "Strict typing catches entire classes of bugs at compile time."
        ),
        "resources": [
            {
                "title": "TypeScript Handbook — Everyday Types",
                "url": "https://www.typescriptlang.org/docs/handbook/2/everyday-types.html",
                "type": "docs",
                "why_this_helps": "Core reference for understanding TypeScript's type system and writing safe code.",
            },
            {
                "title": "Python typing Module Documentation",
                "url": "https://docs.python.org/3/library/typing.html",
                "type": "docs",
                "why_this_helps": "Official guide to Python type hints including generics, protocols, and type narrowing.",
            },
            {
                "title": "Matt Pocock — Total TypeScript Tips",
                "url": "https://www.youtube.com/watch?v=RvBRMbyt_30",
                "type": "youtube",
                "why_this_helps": "Advanced TypeScript patterns from one of the best TS educators.",
            },
        ],
    },
    "error_handling": {
        "topic_name": "Error Handling & Defensive Programming",
        "topic_category": "reliability",
        "why_it_matters": (
            "Bare except blocks, missing try-catch, and swallowed errors lead to silent failures. "
            "Proper error handling is the difference between a debuggable app and a mystery crash."
        ),
        "resources": [
            {
                "title": "Python Exception Handling Best Practices",
                "url": "https://docs.python.org/3/tutorial/errors.html",
                "type": "docs",
                "why_this_helps": "Python's official tutorial on exceptions, custom errors, and clean error handling.",
            },
            {
                "title": "Error Handling in JavaScript — MDN",
                "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Control_flow_and_error_handling",
                "type": "docs",
                "why_this_helps": "Covers try/catch/finally, error types, and error propagation in JS.",
            },
            {
                "title": "Codevolution — Error Handling in React",
                "url": "https://www.youtube.com/watch?v=DNYXgtZBRPE",
                "type": "youtube",
                "why_this_helps": "Practical guide to error boundaries and error state management in React apps.",
            },
        ],
    },
    "null_safety": {
        "topic_name": "Null Safety & Data Access",
        "topic_category": "data_integrity",
        "why_it_matters": (
            "Accessing properties on null or undefined is the #1 runtime crash in JavaScript. "
            "In Python, missing dictionary keys and None values cause similar failures."
        ),
        "resources": [
            {
                "title": "Optional Chaining (?.) — MDN",
                "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Optional_chaining",
                "type": "docs",
                "why_this_helps": "Learn the ?. and ?? operators that eliminate most null-reference crashes.",
            },
            {
                "title": "Python dict.get() and defaultdict",
                "url": "https://docs.python.org/3/library/stdtypes.html#dict.get",
                "type": "docs",
                "why_this_helps": "Safe dictionary access patterns to avoid KeyError in Python.",
            },
            {
                "title": "Web Dev Simplified — Nullish Coalescing",
                "url": "https://www.youtube.com/watch?v=v2tJ3nzXRsg",
                "type": "youtube",
                "why_this_helps": "Quick visual explanation of JavaScript's nullish coalescing and optional chaining.",
            },
        ],
    },
    "testing": {
        "topic_name": "Testing & Assertion Failures",
        "topic_category": "quality",
        "why_it_matters": (
            "Failing tests mean the code doesn't match the spec. Repeated test failures usually indicate "
            "edge cases that are not being considered during development."
        ),
        "resources": [
            {
                "title": "pytest Documentation — Getting Started",
                "url": "https://docs.pytest.org/en/stable/getting-started.html",
                "type": "docs",
                "why_this_helps": "The standard Python testing framework used by most professional projects.",
            },
            {
                "title": "Jest Documentation — Getting Started",
                "url": "https://jestjs.io/docs/getting-started",
                "type": "docs",
                "why_this_helps": "The standard JavaScript testing framework for React and Node.js projects.",
            },
            {
                "title": "Fireship — Testing in 100 Seconds",
                "url": "https://www.youtube.com/watch?v=u6QfIXgjwGQ",
                "type": "youtube",
                "why_this_helps": "Fast overview of unit testing, integration testing, and E2E testing concepts.",
            },
        ],
    },
    "build_config": {
        "topic_name": "Build & Configuration Issues",
        "topic_category": "tooling",
        "why_it_matters": (
            "Build failures block the entire development cycle. Understanding build tools, config files, "
            "and dependency management prevents wasted time on environment issues."
        ),
        "resources": [
            {
                "title": "TypeScript tsconfig.json Reference",
                "url": "https://www.typescriptlang.org/tsconfig",
                "type": "docs",
                "why_this_helps": "Complete reference for every TypeScript compiler option.",
            },
            {
                "title": "Vite Configuration Guide",
                "url": "https://vite.dev/config/",
                "type": "docs",
                "why_this_helps": "Understand how modern JS build tools work and how to configure them.",
            },
            {
                "title": "Theo — Why Does My Build Fail?",
                "url": "https://www.youtube.com/watch?v=jh9MfWMBbCo",
                "type": "youtube",
                "why_this_helps": "Practical debugging of common build and bundler issues.",
            },
        ],
    },
    "git_workflow": {
        "topic_name": "Git & GitHub Workflow",
        "topic_category": "workflow",
        "why_it_matters": (
            "Poor Git practices cause merge conflicts, lost work, and broken CI pipelines. "
            "Mastering branching, PRs, and CI/CD is essential for professional development."
        ),
        "resources": [
            {
                "title": "GitHub Docs — About Pull Requests",
                "url": "https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests",
                "type": "docs",
                "why_this_helps": "Official GitHub guide to creating and managing pull requests.",
            },
            {
                "title": "Atlassian — Git Branching Strategies",
                "url": "https://www.atlassian.com/git/tutorials/comparing-workflows",
                "type": "article",
                "why_this_helps": "Compare GitFlow, trunk-based, and feature branch workflows.",
            },
            {
                "title": "Fireship — Git It? (Git Explained in 100 Seconds)",
                "url": "https://www.youtube.com/watch?v=hwP7WQkmECE",
                "type": "youtube",
                "why_this_helps": "Fast visual refresher on Git fundamentals.",
            },
        ],
    },
}

# Maps failure_type / root_cause keywords → topic keys
FAILURE_TO_TOPIC: list[tuple[list[str], str]] = [
    (["async", "await", "promise", "coroutine", "event loop", "asyncio"], "async_handling"),
    (["type", "typescript", "annotation", "typing", "typecheck", "type error", "type_error"], "type_safety"),
    (["except", "error handling", "try", "catch", "bare except", "exception"], "error_handling"),
    (["null", "none", "undefined", "keyerror", "key error", "nonetype", "optional", "dict access"], "null_safety"),
    (["test", "assert", "assertion", "expect", "test_failure", "spec", "pytest", "jest"], "testing"),
    (["build", "compile", "config", "import", "module", "build_error", "syntax"], "build_config"),
    (["git", "github", "branch", "merge", "pr", "pull request", "commit", "workflow"], "git_workflow"),
]


def _classify_topic(failure_type: str, root_cause: str, signature: str) -> str | None:
    """Map a failure to a topic key using keyword matching."""
    combined = f"{failure_type} {root_cause} {signature}".lower()
    for keywords, topic_key in FAILURE_TO_TOPIC:
        if any(kw in combined for kw in keywords):
            return topic_key
    return None


async def generate_reports(db: AsyncSession) -> list[ClassroomReport]:
    """Scan job history and bug patterns to generate/refresh classroom reports."""

    # 1. Gather evidence from jobs
    jobs_result = await db.execute(
        select(Job).where(Job.status.in_(["completed", "failed"])).order_by(Job.created_at.desc()).limit(200)
    )
    jobs = jobs_result.scalars().all()

    # 2. Gather evidence from bug patterns
    patterns_result = await db.execute(
        select(BugPattern).order_by(BugPattern.occurrence_count.desc()).limit(100)
    )
    patterns = patterns_result.scalars().all()

    # 3. Aggregate by topic
    topic_data: dict[str, dict[str, Any]] = {}

    for job in jobs:
        topic_key = _classify_topic(
            job.failure_type or "",
            job.root_cause or "",
            job.failure_title or "",
        )
        if not topic_key:
            continue

        if topic_key not in topic_data:
            topic_data[topic_key] = {"count": 0, "evidence": [], "severity_sum": 0.0}

        td = topic_data[topic_key]
        td["count"] += 1
        td["severity_sum"] += job.confidence_score or 0.5

        # Build evidence string
        evidence_line = f"Job \"{job.failure_title}\" ({job.failure_type}) — {job.root_cause[:100] if job.root_cause else 'no root cause recorded'}"
        if len(td["evidence"]) < 5:
            td["evidence"].append(evidence_line)

    for pattern in patterns:
        topic_key = _classify_topic(
            pattern.failure_type or "",
            pattern.root_cause_category or "",
            pattern.pattern_signature or "",
        )
        if not topic_key:
            continue

        if topic_key not in topic_data:
            topic_data[topic_key] = {"count": 0, "evidence": [], "severity_sum": 0.0}

        td = topic_data[topic_key]
        td["count"] += pattern.occurrence_count
        td["severity_sum"] += (1.0 - pattern.resolution_rate) * pattern.occurrence_count

        evidence_line = f"Bug pattern \"{pattern.pattern_signature}\" seen {pattern.occurrence_count}× (resolution rate: {int(pattern.resolution_rate * 100)}%)"
        if len(td["evidence"]) < 5:
            td["evidence"].append(evidence_line)

    # 4. Create or update reports
    created_reports: list[ClassroomReport] = []

    for topic_key, data in topic_data.items():
        if topic_key not in TOPIC_KNOWLEDGE:
            continue

        knowledge = TOPIC_KNOWLEDGE[topic_key]

        # Check if a report for this topic already exists and is not completed
        existing_result = await db.execute(
            select(ClassroomReport).where(
                ClassroomReport.topic_name == knowledge["topic_name"],
                ClassroomReport.status != "completed",
            )
        )
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Update existing report
            existing.occurrence_count = data["count"]
            existing.severity_score = min(round(data["severity_sum"] / max(data["count"], 1), 2), 1.0)
            existing.evidence = json.dumps(data["evidence"])
            existing.updated_at = utc_now()
        else:
            # Create new report
            severity = min(round(data["severity_sum"] / max(data["count"], 1), 2), 1.0)
            report = ClassroomReport(
                id=generate_id(),
                title=f"Improve Your {knowledge['topic_name']}",
                topic_name=knowledge["topic_name"],
                topic_category=knowledge["topic_category"],
                weakness_summary=f"AutoMerge detected {data['count']} instance(s) of issues related to {knowledge['topic_name'].lower()}. This pattern indicates a recurring weakness area that would benefit from focused study.",
                why_it_matters=knowledge["why_it_matters"],
                evidence=json.dumps(data["evidence"]),
                resources=json.dumps(knowledge["resources"]),
                occurrence_count=data["count"],
                severity_score=severity,
                status="open",
                revision_done=False,
                report_date=utc_now(),
            )
            db.add(report)
            created_reports.append(report)

    await db.commit()
    return created_reports
