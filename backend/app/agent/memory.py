"""
Bug Memory Module

Stores and retrieves recurring bug patterns for the agent to learn from.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BugPattern


async def record_pattern(db: AsyncSession, state: dict[str, Any]) -> None:
    """Record a bug pattern from a completed pipeline run."""
    failure_type = state.get("failure_type", "unknown")
    primary_signal = state.get("primary_signal", {})
    signal_type = primary_signal.get("type", "unknown")

    # Create a signature from failure type + signal
    signature = f"{failure_type}:{signal_type}"

    # Check if pattern already exists
    result = await db.execute(
        select(BugPattern).where(BugPattern.pattern_signature == signature)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.occurrence_count += 1
        existing.last_seen = datetime.now(timezone.utc)
        # Update resolution rate
        validation = state.get("validation", {})
        if validation.get("status") == "passed":
            total = existing.occurrence_count
            existing.resolution_rate = ((existing.resolution_rate * (total - 1)) + 1.0) / total
    else:
        pattern = BugPattern(
            pattern_signature=signature,
            failure_type=failure_type,
            root_cause_category=state.get("root_cause", "")[:128],
            fix_template=state.get("patch", {}).get("explanation", ""),
            occurrence_count=1,
            resolution_rate=1.0 if state.get("validation", {}).get("status") == "passed" else 0.0,
        )
        db.add(pattern)

    await db.commit()


async def find_similar_patterns(db: AsyncSession, failure_type: str, signal_type: str) -> list[dict]:
    """Find similar bug patterns from memory."""
    result = await db.execute(
        select(BugPattern)
        .where(BugPattern.failure_type == failure_type)
        .order_by(BugPattern.occurrence_count.desc())
        .limit(5)
    )
    patterns = result.scalars().all()

    return [
        {
            "signature": p.pattern_signature,
            "category": p.root_cause_category,
            "occurrences": p.occurrence_count,
            "resolution_rate": p.resolution_rate,
        }
        for p in patterns
    ]
