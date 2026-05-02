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

  // ─── AutoDeploy ─────────────────────────────────────────

  deployAnalyze: (repo_url: string, token: string = "") =>
    request<any>("/deploy/analyze", {
      method: "POST",
      body: JSON.stringify({ repo_url, token }),
    }),

  deployPreview: (repo_url: string, platform_id: string = "", token: string = "") =>
    request<any>("/deploy/preview", {
      method: "POST",
      body: JSON.stringify({ repo_url, platform_id, token }),
    }),

  deployStart: (data: { repo_url: string; platform_id: string; token?: string; platform_token?: string; env_vars?: Record<string, string> }) =>
    request<any>("/deploy/start", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  deployRuns: () =>
    request<any>("/deploy/runs"),

  deployGetRun: (id: string) =>
    request<any>(`/deploy/runs/${id}`),

  deployRetry: (id: string, platform_token: string = "", env_vars?: Record<string, string>) =>
    request<any>(`/deploy/runs/${id}/retry`, {
      method: "POST",
      body: JSON.stringify({ platform_token, env_vars }),
    }),

  deployEnableAuto: (id: string, platform_token: string = "") =>
    request<any>(`/deploy/runs/${id}/auto-deploy`, {
      method: "POST",
      body: JSON.stringify({ platform_token }),
    }),

  deployPlatforms: () =>
    request<any>("/deploy/platforms"),

  // ─── BugFix Arena / Battle ──────────────────────────────

  battleCreate: (host_name: string, challenge_id: string = "") =>
    request<any>("/battle/create", { method: "POST", body: JSON.stringify({ host_name, challenge_id }) }),

  battleJoin: (room_code: string, player_name: string) =>
    request<any>("/battle/join", { method: "POST", body: JSON.stringify({ room_code, player_name }) }),

  battleStart: (session_id: string) =>
    request<any>(`/battle/${session_id}/start`, { method: "POST" }),

  battleSubmit: (session_id: string, player_id: string, code: string, explanation: string = "") =>
    request<any>(`/battle/${session_id}/submit`, { method: "POST", body: JSON.stringify({ player_id, code, explanation }) }),

  battleGetState: (session_id: string) =>
    request<any>(`/battle/${session_id}/state`),

  battleGetResult: (session_id: string) =>
    request<any>(`/battle/${session_id}/result`),

  battleFinish: (session_id: string) =>
    request<any>(`/battle/${session_id}/finish`, { method: "POST" }),

  battleLeaderboard: () =>
    request<any>("/battle/meta/leaderboard"),

  battleChallenges: () =>
    request<any>("/battle/meta/challenges"),

  // ─── AR Debug Explorer ──────────────────────────────────

  arStudioScene: (jobId: string) =>
    request<any>(`/ar/scene/studio/${jobId}`),

  arStudioSceneLive: (result: any) =>
    request<any>("/ar/scene/studio/live", { method: "POST", body: JSON.stringify(result) }),

  arRepoScene: (reportId: string) =>
    request<any>(`/ar/scene/repo/${reportId}`),

  arDeployScene: (runId: string) =>
    request<any>(`/ar/scene/deploy/${runId}`),

  arBattleScene: (sessionId: string) =>
    request<any>(`/ar/scene/battle/${sessionId}`),

  arHistory: () =>
    request<any>("/ar/history"),

  arDeleteHistory: (sceneId: string) =>
    request<any>(`/ar/history/${sceneId}`, { method: "DELETE" }),

  // ─── Sandbox Execution ──────────────────────────────────

  sandboxRun: (data: { code: string; language?: string; test_code?: string; filename?: string; mode?: string; timeout?: number; memory_limit?: string; cpu_limit?: string; network_disabled?: boolean; source_feature?: string }) =>
    request<any>("/sandbox/run", { method: "POST", body: JSON.stringify(data) }),

  sandboxTest: (data: { code: string; language?: string; test_code?: string; timeout?: number }) =>
    request<any>("/sandbox/test", { method: "POST", body: JSON.stringify(data) }),

  sandboxRuns: (limit?: number) =>
    request<any>(`/sandbox/runs?limit=${limit || 50}`),

  sandboxGetRun: (runId: string) =>
    request<any>(`/sandbox/runs/${runId}`),

  sandboxDeleteRun: (runId: string) =>
    request<any>(`/sandbox/runs/${runId}`, { method: "DELETE" }),

  // ─── Chrome Extension API ────────────────────────────────

  extensionAnalyze: (data: {
    code: string; language?: string; filename?: string; source_type?: string;
    page_url?: string; repo_url?: string; selected_text?: string;
    session_id?: string; extension_version?: string;
  }) => request<any>("/extension/analyze", { method: "POST", body: JSON.stringify(data) }),

  extensionExplain: (data: { code: string; language?: string; filename?: string; page_url?: string }) =>
    request<any>("/extension/explain", { method: "POST", body: JSON.stringify(data) }),

  extensionHistory: (limit?: number) =>
    request<any>(`/extension/history?limit=${limit || 50}`),

  extensionReport: (analysisId: string) =>
    request<any>(`/extension/runs/${analysisId}`),

  extensionDeleteReport: (analysisId: string) =>
    request<any>(`/extension/runs/${analysisId}`, { method: "DELETE" }),

  extensionHealth: () =>
    request<any>("/extension/health"),
};
