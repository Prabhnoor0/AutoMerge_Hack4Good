"""
AutoMerge Database Models

SQLAlchemy ORM models for all core entities.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Float, Integer, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_id() -> str:
    """Generate a short unique ID."""
    return uuid.uuid4().hex[:12]


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account."""
    __tablename__ = "users"

    id = Column(String(12), primary_key=True, default=generate_id)
    email = Column(String(256), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    name = Column(String(128), default="")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    jobs = relationship("Job", back_populates="user")
    classroom_reports = relationship("ClassroomReport", back_populates="user")


class Job(Base):
    """Represents an autonomous fix job triggered by a failure."""
    __tablename__ = "jobs"

    id = Column(String(12), primary_key=True, default=generate_id)
    user_id = Column(String(12), ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(20), default="queued", nullable=False, index=True)
    failure_title = Column(String(256), nullable=False)
    failure_source = Column(String(64), default="manual")  # manual, ci, webhook
    failure_type = Column(String(64), default="unknown")    # test, build, type, runtime
    raw_logs = Column(Text, default="")
    confidence_score = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    mode = Column(String(16), default="standard")  # standard, demo
    root_cause = Column(Text, default="")
    reasoning_trace = Column(Text, default="")

    # GitHub repo fields
    repo_url = Column(String(512), default="")
    repo_owner = Column(String(128), default="")
    repo_name = Column(String(128), default="")
    base_branch = Column(String(128), default="main")
    target_file_path = Column(String(512), default="")
    github_pr_url = Column(String(512), default="")
    github_pr_number = Column(Integer, nullable=True)
    github_commit_sha = Column(String(64), default="")
    github_branch_name = Column(String(256), default="")

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="jobs")
    steps = relationship("PipelineStep", back_populates="job", order_by="PipelineStep.order_index")
    patches = relationship("Patch", back_populates="job")
    validation = relationship("ValidationResult", back_populates="job", uselist=False)
    summary = relationship("Summary", back_populates="job", uselist=False)


class PipelineStep(Base):
    """Individual step in the agent pipeline."""
    __tablename__ = "pipeline_steps"

    id = Column(String(12), primary_key=True, default=generate_id)
    job_id = Column(String(12), ForeignKey("jobs.id"), nullable=False, index=True)
    step_name = Column(String(64), nullable=False)
    status = Column(String(20), default="pending")  # pending, running, completed, failed, skipped
    input_data = Column(Text, default="{}")
    output_data = Column(Text, default="{}")
    error_message = Column(Text, default="")
    order_index = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0)

    job = relationship("Job", back_populates="steps")


class Patch(Base):
    """Generated code patch/diff for a fix."""
    __tablename__ = "patches"

    id = Column(String(12), primary_key=True, default=generate_id)
    job_id = Column(String(12), ForeignKey("jobs.id"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    original_code = Column(Text, default="")
    fixed_code = Column(Text, default="")
    diff_text = Column(Text, default="")
    explanation = Column(Text, default="")
    language = Column(String(32), default="python")

    job = relationship("Job", back_populates="patches")


class ValidationResult(Base):
    """Result of running the patch in a sandbox."""
    __tablename__ = "validation_results"

    id = Column(String(12), primary_key=True, default=generate_id)
    job_id = Column(String(12), ForeignKey("jobs.id"), nullable=False, unique=True)
    status = Column(String(20), default="pending")  # pending, running, passed, failed, error, timeout
    stdout = Column(Text, default="")
    stderr = Column(Text, default="")
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
    validated_at = Column(DateTime, nullable=True)

    job = relationship("Job", back_populates="validation")


class Summary(Base):
    """Human-readable summary and PR-ready description."""
    __tablename__ = "summaries"

    id = Column(String(12), primary_key=True, default=generate_id)
    job_id = Column(String(12), ForeignKey("jobs.id"), nullable=False, unique=True)
    title = Column(String(256), default="")
    root_cause = Column(Text, default="")
    fix_description = Column(Text, default="")
    pr_title = Column(String(256), default="")
    pr_body = Column(Text, default="")
    reasoning_trace = Column(Text, default="")
    impact_assessment = Column(Text, default="")

    # ── Precision Debugging Fields (additive) ──
    evidence_report_json = Column(Text, default="{}")      # Full evidence report as JSON
    triage_verdict = Column(String(32), default="")        # high_confidence, moderate, low_confidence, noise, likely_flaky
    confidence_calibrated = Column(Float, default=0.0)     # Final calibrated score 0.0–1.0
    reproducibility = Column(String(32), default="")       # reproducible, partially_reproducible, likely_flaky, non_reproducible
    flake_score = Column(Float, default=0.0)               # 0.0–1.0
    severity = Column(String(16), default="")              # critical, high, medium, low
    commit_trace_json = Column(Text, default="{}")         # Commit trace data as JSON
    why_real = Column(Text, default="[]")                  # JSON array of reasons
    why_noise = Column(Text, default="[]")                 # JSON array of reasons
    next_action = Column(Text, default="")                 # Suggested developer action

    job = relationship("Job", back_populates="summary")


class BugPattern(Base):
    """Recurring bug pattern memory for the agent."""
    __tablename__ = "bug_patterns"

    id = Column(String(12), primary_key=True, default=generate_id)
    pattern_signature = Column(String(256), nullable=False, unique=True)
    failure_type = Column(String(64), default="unknown")
    root_cause_category = Column(String(128), default="")
    fix_template = Column(Text, default="")
    occurrence_count = Column(Integer, default=1)
    last_seen = Column(DateTime, default=utc_now)
    resolution_rate = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utc_now, nullable=False)


class ClassroomReport(Base):
    """Learning report generated from recurring debugging patterns."""
    __tablename__ = "classroom_reports"

    id = Column(String(12), primary_key=True, default=generate_id)
    user_id = Column(String(12), ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(256), nullable=False)
    topic_name = Column(String(128), nullable=False)
    topic_category = Column(String(64), default="general")
    weakness_summary = Column(Text, default="")
    why_it_matters = Column(Text, default="")
    evidence = Column(Text, default="[]")          # JSON array of evidence strings
    resources = Column(Text, default="[]")          # JSON array of resource objects
    occurrence_count = Column(Integer, default=1)
    severity_score = Column(Float, default=0.5)     # 0.0 – 1.0
    status = Column(String(20), default="open")     # open, in_progress, completed
    revision_done = Column(Boolean, default=False)
    notes = Column(Text, default="")
    report_date = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="classroom_reports")
