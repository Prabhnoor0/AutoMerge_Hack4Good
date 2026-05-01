/* ─── TypeScript types matching backend schemas ─── */

export interface Job {
  id: string;
  status: JobStatus;
  failure_title: string;
  failure_source: string;
  failure_type: string;
  confidence_score: number;
  retry_count: number;
  max_retries: number;
  mode: string;
  root_cause: string;
  repo_url: string;
  repo_owner: string;
  repo_name: string;
  base_branch: string;
  target_file_path: string;
  github_pr_url: string;
  github_pr_number: number | null;
  github_commit_sha: string;
  github_branch_name: string;
  created_at: string;
  updated_at: string;
}

export interface JobDetail extends Job {
  raw_logs: string;
  reasoning_trace: string;
  steps: PipelineStep[];
  patches: Patch[];
  validation: ValidationResult | null;
  summary: Summary | null;
}

export interface PipelineStep {
  id: string;
  step_name: string;
  status: StepStatus;
  output_data: string;
  error_message: string;
  order_index: number;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number;
}

export interface Patch {
  id: string;
  file_path: string;
  original_code: string;
  fixed_code: string;
  diff_text: string;
  explanation: string;
  language: string;
}

export interface ValidationResult {
  id: string;
  status: string;
  stdout: string;
  stderr: string;
  tests_passed: number;
  tests_failed: number;
  tests_total: number;
  duration_seconds: number;
  validated_at: string | null;
}

export interface Summary {
  id: string;
  title: string;
  root_cause: string;
  fix_description: string;
  pr_title: string;
  pr_body: string;
  reasoning_trace: string;
  impact_assessment: string;

  // Precision debugging fields
  evidence_report_json?: string;
  triage_verdict?: string;
  confidence_calibrated?: number;
  reproducibility?: string;
  flake_score?: number;
  severity?: string;
  commit_trace_json?: string;
  why_real?: string;
  why_noise?: string;
  next_action?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  demo_mode: boolean;
  integrations: Record<string, boolean>;
}

export interface SystemDiagnostics {
  total_jobs: number;
  jobs_by_status: Record<string, number>;
  total_patterns: number;
  avg_confidence: number;
  success_rate: number;
}

export type JobStatus =
  | "queued"
  | "analyzing"
  | "diagnosing"
  | "patching"
  | "validating"
  | "summarizing"
  | "retrying"
  | "completed"
  | "failed";

export type StepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped";

export const STEP_LABELS: Record<string, string> = {
  log_parsing: "Log Parsing",
  signal_extraction: "Signal Extraction",
  failure_classification: "Failure Classification",
  precision_triage: "Precision Triage",
  reproduction_assessment: "Reproduction Assessment",
  root_cause_analysis: "Root Cause Analysis",
  patch_generation: "Patch Generation",
  patch_validation: "Patch Validation",
  commit_tracing: "Commit Tracing",
  evidence_aggregation: "Evidence Aggregation",
  summary_generation: "Summary Generation",
};

export const STATUS_COLORS: Record<string, string> = {
  queued: "#6b7280",
  analyzing: "#3b82f6",
  diagnosing: "#8b5cf6",
  patching: "#f59e0b",
  validating: "#06b6d4",
  summarizing: "#10b981",
  retrying: "#f97316",
  completed: "#22c55e",
  failed: "#ef4444",
  pending: "#6b7280",
  running: "#3b82f6",
  skipped: "#9ca3af",
};

// ─── GitHub Repo Types ──────────────────────────────────

export interface RepoAnalysisInput {
  repo_url: string;
  token: string;
  base_branch: string;
  file_path: string;
  logs: string;
  language: string;
  mode: string;
}

export interface RepoValidateResult {
  valid: boolean;
  stage?: string;
  error?: string;
  username?: string;
  repo?: string;
  default_branch?: string;
  private?: boolean;
  permissions?: Record<string, boolean>;
  is_mock?: boolean;
}

export interface PRResult {
  success: boolean;
  branch?: { branch: string; url: string; sha: string; mock?: boolean };
  commit?: { commit_sha: string; file_path: string; mock?: boolean };
  pr?: { pr_number: number; pr_url: string; state: string; mock?: boolean };
  is_mock?: boolean;
  error?: string;
}

export interface MergeResult {
  success: boolean;
  merged?: boolean;
  sha?: string;
  is_mock?: boolean;
  error?: string;
}

// ─── Bug Pattern / Memory Types ─────────────────────────

export interface BugPattern {
  id: string;
  pattern_signature: string;
  failure_type: string;
  root_cause_category: string;
  occurrence_count: number;
  resolution_rate: number;
  last_seen: string;
}

// ─── ChronoDebugger Types ───────────────────────────────

export interface ChronoEvent {
  step_name: string;
  label: string;
  status: StepStatus;
  duration_ms: number;
  detail: string;
  started_at: string | null;
  completed_at: string | null;
}

// ─── Classroom Types ────────────────────────────────────

export interface ClassroomResource {
  title: string;
  url: string;
  type: "youtube" | "docs" | "article" | "practice";
  why_this_helps: string;
}

export interface ClassroomReport {
  id: string;
  title: string;
  topic_name: string;
  topic_category: string;
  weakness_summary: string;
  why_it_matters: string;
  evidence: string[];
  resources: ClassroomResource[];
  occurrence_count: number;
  severity_score: number;
  status: "open" | "in_progress" | "completed";
  revision_done: boolean;
  notes: string;
  report_date: string;
  created_at: string;
  updated_at: string;
}

export interface ClassroomSummary {
  total_reports: number;
  open_reports: number;
  revision_done_count: number;
  completed_count: number;
}
