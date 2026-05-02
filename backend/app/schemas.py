"""
AutoMerge Pydantic Schemas

Request/response schemas for all API endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ─── Job Schemas ───────────────────────────────────────────

class FailureInput(BaseModel):
    """Input for creating a new fix job from a failure."""
    title: str = Field(..., min_length=1, max_length=256, description="Short failure title")
    logs: str = Field(..., min_length=1, description="Raw build/test logs")
    source: str = Field(default="manual", description="Origin: manual, ci, webhook")
    failure_type: str = Field(default="auto", description="Type: test, build, type, runtime, auto")
    mode: str = Field(default="standard", description="Mode: standard or demo")


class CodeSubmission(BaseModel):
    """Input for submitting code for analysis."""
    code: str = Field(..., min_length=1, description="Source code to analyze")
    language: str = Field(default="python", description="Programming language")
    filename: str | None = Field(default=None, description="Optional filename")


# ─── GitHub Repo Schemas ──────────────────────────────────

class RepoAnalysisRequest(BaseModel):
    """Input for analyzing a GitHub repository."""
    repo_url: str = Field(..., min_length=1, description="GitHub repo URL or owner/repo")
    token: str = Field(..., min_length=1, description="GitHub personal access token")
    base_branch: str = Field(default="main", description="Base branch to analyze")
    file_path: str = Field(default="", description="Target file path (auto-detect if empty)")
    logs: str = Field(default="", description="Error logs or console output")
    language: str = Field(default="auto", description="Programming language (auto-detect if empty)")
    mode: str = Field(default="auto", description="Mode: auto-detect or manual file path")


class RepoValidateRequest(BaseModel):
    """Input for validating repo access."""
    repo_url: str = Field(..., min_length=1, description="GitHub repo URL or owner/repo")
    token: str = Field(..., min_length=1, description="GitHub personal access token")


class PRCreateRequest(BaseModel):
    """Request to create a PR for a completed job."""
    job_id: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1, description="GitHub token")
    base_branch: str = Field(default="main")


class PRMergeRequest(BaseModel):
    """Request to merge an existing PR."""
    job_id: str = Field(..., min_length=1)
    token: str = Field(..., min_length=1, description="GitHub token")
    merge_method: str = Field(default="squash", description="merge, squash, or rebase")


# ─── Job Response Schemas ─────────────────────────────────

class JobResponse(BaseModel):
    """Job summary for list/detail views."""
    id: str
    user_id: str | None = None
    status: str
    failure_title: str
    failure_source: str
    failure_type: str
    confidence_score: float
    retry_count: int
    max_retries: int
    mode: str
    root_cause: str
    repo_url: str = ""
    repo_owner: str = ""
    repo_name: str = ""
    base_branch: str = "main"
    target_file_path: str = ""
    github_pr_url: str = ""
    github_pr_number: int | None = None
    github_commit_sha: str = ""
    github_branch_name: str = ""
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobDetailResponse(JobResponse):
    """Full job detail with related entities."""
    raw_logs: str
    reasoning_trace: str
    steps: list["PipelineStepResponse"]
    patches: list["PatchResponse"]
    validation: "ValidationResponse | None"
    summary: "SummaryResponse | None"

    model_config = {"from_attributes": True}


# ─── Pipeline Step Schemas ─────────────────────────────────

class PipelineStepResponse(BaseModel):
    """Individual pipeline step status."""
    id: str
    step_name: str
    status: str
    output_data: str
    error_message: str
    order_index: int
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int

    model_config = {"from_attributes": True}


# ─── Patch Schemas ─────────────────────────────────────────

class PatchResponse(BaseModel):
    """Generated code patch."""
    id: str
    file_path: str
    original_code: str
    fixed_code: str
    diff_text: str
    explanation: str
    language: str

    model_config = {"from_attributes": True}


# ─── Validation Schemas ───────────────────────────────────

class ValidationResponse(BaseModel):
    """Sandbox validation result."""
    id: str
    status: str
    stdout: str
    stderr: str
    tests_passed: int
    tests_failed: int
    tests_total: int
    duration_seconds: float
    validated_at: datetime | None

    model_config = {"from_attributes": True}


# ─── Summary Schemas ──────────────────────────────────────

class SummaryResponse(BaseModel):
    """Human-readable fix summary with precision evidence."""
    id: str
    title: str
    root_cause: str
    fix_description: str
    pr_title: str
    pr_body: str
    reasoning_trace: str
    impact_assessment: str

    # Precision debugging fields (additive)
    evidence_report_json: str = "{}"
    triage_verdict: str = ""
    confidence_calibrated: float = 0.0
    reproducibility: str = ""
    flake_score: float = 0.0
    severity: str = ""
    commit_trace_json: str = "{}"
    why_real: str = "[]"
    why_noise: str = "[]"
    next_action: str = ""

    model_config = {"from_attributes": True}


# ─── Bug Pattern Schemas ──────────────────────────────────

class BugPatternResponse(BaseModel):
    """Recurring bug pattern."""
    id: str
    pattern_signature: str
    failure_type: str
    root_cause_category: str
    occurrence_count: int
    resolution_rate: float
    last_seen: datetime

    model_config = {"from_attributes": True}


# ─── System Schemas ───────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    database: str = "connected"
    demo_mode: bool = True
    integrations: dict[str, bool] = {}


class SystemDiagnostics(BaseModel):
    """System diagnostics response."""
    total_jobs: int = 0
    jobs_by_status: dict[str, int] = {}
    total_patterns: int = 0
    avg_confidence: float = 0.0
    success_rate: float = 0.0


class DemoTriggerRequest(BaseModel):
    """Request to trigger a demo scenario."""
    scenario: str = Field(default="test_failure", description="Scenario: test_failure, build_error, type_error")


class DemoTriggerResponse(BaseModel):
    """Response from triggering a demo."""
    job_id: str
    message: str


# ─── Classroom Schemas ────────────────────────────────────

class ResourceItem(BaseModel):
    """A curated learning resource."""
    title: str
    url: str
    type: str = "article"        # youtube, docs, article, practice
    why_this_helps: str = ""


class ClassroomReportResponse(BaseModel):
    """Full classroom report."""
    id: str
    user_id: str | None = None
    title: str
    topic_name: str
    topic_category: str
    weakness_summary: str
    why_it_matters: str
    evidence: list[str]
    resources: list[ResourceItem]
    occurrence_count: int
    severity_score: float
    status: str
    revision_done: bool
    notes: str
    report_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClassroomReportUpdate(BaseModel):
    """Partial update for a classroom report."""
    status: str | None = None
    revision_done: bool | None = None
    notes: str | None = None


class ClassroomSummary(BaseModel):
    """High-level stats for the classroom dashboard."""
    total_reports: int = 0
    open_reports: int = 0
    revision_done_count: int = 0
    completed_count: int = 0

