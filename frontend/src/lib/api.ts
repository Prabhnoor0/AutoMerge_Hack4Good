/* ─── API Client for AutoMerge Backend ─── */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error: ${res.status}`);
  }
  return res.json();
}

import type {
  Job,
  JobDetail,
  HealthResponse,
  SystemDiagnostics,
  RepoAnalysisInput,
  RepoValidateResult,
  PRResult,
  MergeResult,
  BugPattern,
  ClassroomReport,
  ClassroomSummary,
} from "./types";

export const api = {
  // System
  health: () => request<HealthResponse>("/health"),
  diagnostics: () => request<SystemDiagnostics>("/diagnostics"),

  // Jobs
  listJobs: (status?: string) =>
    request<Job[]>(`/jobs${status ? `?status=${status}` : ""}`),

  getJob: (id: string) => request<JobDetail>(`/jobs/${id}`),

  deleteJob: (id: string) =>
    request<{ message: string }>(`/jobs/${id}`, { method: "DELETE" }),

  // Failures
  ingestFailure: (data: {
    title: string;
    logs: string;
    source?: string;
    failure_type?: string;
    mode?: string;
  }) =>
    request<Job>("/failures", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Demo
  triggerDemo: (scenario: string = "test_failure") =>
    request<{ job_id: string; message: string }>("/demo/trigger", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),

  // Code Analysis (legacy workspace)
  submitCode: (data: { code: string; language: string; filename?: string }) =>
    request<Job>("/code/analyze", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // ─── GitHub Repo Workflow ────────────────────────────

  // Validate repo URL + token
  validateRepo: (data: { repo_url: string; token: string }) =>
    request<RepoValidateResult>("/github/repo/validate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Analyze a GitHub repo (fetch file → run pipeline)
  analyzeRepo: (data: RepoAnalysisInput) =>
    request<Job>("/github/repo/analyze", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Create PR for a completed job
  createRepoPR: (data: { job_id: string; token: string; base_branch?: string }) =>
    request<PRResult>("/github/pr/create", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Merge an existing PR
  mergeRepoPR: (data: { job_id: string; token: string; merge_method?: string }) =>
    request<MergeResult>("/github/pr/merge", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // ─── Legacy GitHub Integration ───────────────────────

  githubStatus: () =>
    request<{ connected: boolean; mode: string; owner: string; repo: string }>("/github/status"),

  githubConnect: (data: { token: string; owner: string; repo: string }) =>
    request<{ success: boolean; message: string; mode: string }>("/github/connect", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  githubDisconnect: () =>
    request<{ success: boolean; mode: string }>("/github/disconnect", {
      method: "POST",
    }),

  githubCreatePR: (jobId: string, baseBranch: string = "main") =>
    request<PRResult>("/github/create-pr", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, base_branch: baseBranch }),
    }),

  // ─── Code Debug Studio ─────────────────────────────────

  studioSubmit: (data: any) =>
    request<any>("/studio/submit", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  studioDemo: (sample: string, modes: string[]) =>
    request<any>("/studio/demo", {
      method: "POST",
      body: JSON.stringify({ sample, modes }),
    }),

  studioGetResult: (jobId: string) =>
    request<any>(`/studio/${jobId}`),

  // ─── Bug Patterns / Memory ─────────────────────────────

  bugPatterns: () =>
    request<BugPattern[]>("/patterns"),

  // ─── Devमित्र ──────────────────────────────────────────

  devmitraChat: (message: string, context: any, sessionId?: string) =>
    request<any>("/devmitra/chat", {
      method: "POST",
      body: JSON.stringify({ message, context, session_id: sessionId || null }),
    }),

  devmitraUpdateContext: (sessionId: string, context: any) =>
    request<any>("/devmitra/context", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, context }),
    }),

  devmitraResetSession: (sessionId: string) =>
    request<any>("/devmitra/session/reset", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),

  devmitraContextStatus: () =>
    request<any>("/devmitra/context/status"),

  // ─── Classroom ──────────────────────────────────────────

  classroomReports: (status?: string) =>
    request<ClassroomReport[]>(`/classroom/reports${status ? `?status=${status}` : ""}`),

  classroomSummary: () =>
    request<ClassroomSummary>("/classroom/summary"),

  classroomRefresh: () =>
    request<ClassroomReport[]>("/classroom/reports/refresh", { method: "POST" }),

  classroomGetReport: (id: string) =>
    request<ClassroomReport>(`/classroom/reports/${id}`),

  classroomUpdateReport: (id: string, data: { status?: string; revision_done?: boolean; notes?: string }) =>
    request<ClassroomReport>(`/classroom/reports/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  classroomDeleteReport: (id: string) =>
    request<{ message: string }>(`/classroom/reports/${id}`, { method: "DELETE" }),

  // ─── Devमित्र Repo Explorer ─────────────────────────────

  repoExplorerAnalyze: (repo_url: string, token: string = "") =>
    request<any>("/repo-explorer/analyze", {
      method: "POST",
      body: JSON.stringify({ repo_url, token }),
    }),

  repoExplorerAsk: (report_id: string, question: string) =>
    request<any>("/repo-explorer/ask", {
      method: "POST",
      body: JSON.stringify({ report_id, question }),
    }),

  repoExplorerHistory: () =>
    request<any>("/repo-explorer/history"),

  repoExplorerReport: (report_id: string) =>
    request<any>(`/repo-explorer/report/${report_id}`),

  repoExplorerDeleteHistory: (report_id: string) =>
    request<any>(`/repo-explorer/history/${report_id}`, { method: "DELETE" }),
};
