"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Loader2, GitMerge, Code2, LayoutDashboard,
  Search, GitBranch, FileCode, Terminal,
  Zap, Shield, Eye, EyeOff, Globe, Lock,
  ChevronRight, AlertCircle, CheckCircle2,
} from "lucide-react";
import { api } from "@/lib/api";
import { useJobDetail } from "@/hooks/useJobs";
import { AnalysisPanel } from "@/components/editor/AnalysisPanel";
import { useDevmitra } from "@/store/DevmitraContext";
import type { RepoValidateResult } from "@/lib/types";

const LANGUAGES = [
  { value: "auto", label: "Auto-detect" },
  { value: "python", label: "Python" },
  { value: "typescript", label: "TypeScript" },
  { value: "javascript", label: "JavaScript" },
  { value: "java", label: "Java" },
  { value: "go", label: "Go" },
  { value: "rust", label: "Rust" },
  { value: "cpp", label: "C++" },
];

type WorkflowStep = "input" | "validating" | "analyzing" | "results";

export default function WorkspacePage() {
  // Form state
  const [repoUrl, setRepoUrl] = useState("");
  const [token, setToken] = useState("");
  const [baseBranch, setBaseBranch] = useState("main");
  const [filePath, setFilePath] = useState("");
  const [logs, setLogs] = useState("");
  const [language, setLanguage] = useState("auto");
  const [showToken, setShowToken] = useState(false);

  // Workflow state
  const [step, setStep] = useState<WorkflowStep>("input");
  const [repoInfo, setRepoInfo] = useState<RepoValidateResult | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);

  const { job, loading: jobLoading } = useJobDetail(jobId);
  const { setContext } = useDevmitra();

  useEffect(() => {
    setContext({
      repoUrl,
      filename: filePath,
      language,
      logs
    });
  }, [repoUrl, filePath, language, logs, setContext]);

  // Validate repo
  const handleValidate = useCallback(async () => {
    if (!repoUrl || !token) return;
    setError(null);
    setValidating(true);
    setStep("validating");
    try {
      const result = await api.validateRepo({ repo_url: repoUrl, token });
      setRepoInfo(result);
      if (!result.valid) {
        setError(result.error || "Validation failed");
        setStep("input");
      }
    } catch (e: any) {
      setError(e.message || "Validation failed");
      setStep("input");
    } finally {
      setValidating(false);
    }
  }, [repoUrl, token]);

  // Run analysis
  const handleAnalyze = useCallback(async () => {
    if (!repoUrl || !token) return;
    setError(null);
    setStep("analyzing");
    try {
      const result = await api.analyzeRepo({
        repo_url: repoUrl,
        token,
        base_branch: baseBranch,
        file_path: filePath,
        logs,
        language,
        mode: filePath ? "manual" : "auto",
      });
      setJobId(result.id);
      setStep("results");
    } catch (e: any) {
      setError(e.message || "Analysis failed");
      setStep("input");
    }
  }, [repoUrl, token, baseBranch, filePath, logs, language]);

  // Create PR
  const handleCreatePR = useCallback(async () => {
    if (!jobId || !token) return;
    try {
      const result = await api.createRepoPR({
        job_id: jobId,
        token,
        base_branch: baseBranch,
      });
      return result;
    } catch (e: any) {
      throw e;
    }
  }, [jobId, token, baseBranch]);

  const canValidate = repoUrl.trim().length > 0 && token.trim().length > 0;
  const canAnalyze = repoInfo?.valid && (logs.trim().length > 0 || filePath.trim().length > 0);

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-primary)" }}>
      {/* Main workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Input Panel */}
        <div className={`flex flex-col ${step === "results" && job ? "w-[480px]" : "flex-1 max-w-3xl mx-auto"} transition-all duration-300`}>
          <div className="flex-1 overflow-y-auto p-6">
            {/* Hero section */}
            {step === "input" && !repoInfo?.valid && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mb-8 text-center">
                <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
                  Autonomous Code Debugger
                </h1>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  Paste a GitHub repo URL and error logs — AutoMerge will analyze, fix, and open a PR.
                </p>
              </motion.div>
            )}

            {/* Error banner */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="mb-4 flex items-center gap-2 p-3 rounded-xl text-xs font-medium"
                  style={{ background: "var(--glow-red)", color: "var(--accent-red)", border: "1px solid rgba(239,68,68,0.2)" }}
                >
                  <AlertCircle size={14} />
                  <span className="flex-1">{error}</span>
                  <button onClick={() => setError(null)} className="underline opacity-70 hover:opacity-100">
                    Dismiss
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Step 1: Repository + Token */}
            <div className="space-y-4">
              <SectionCard title="Repository" icon={<Globe size={14} />} badge={repoInfo?.valid ? "Connected" : undefined}>
                <div className="space-y-3">
                  <div>
                    <label className="text-[11px] font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                      GitHub Repository URL
                    </label>
                    <input
                      value={repoUrl}
                      onChange={(e) => { setRepoUrl(e.target.value); setRepoInfo(null); }}
                      placeholder="https://github.com/owner/repo  or  owner/repo"
                      className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono outline-none transition-all"
                      style={{
                        background: "var(--bg-primary)",
                        border: "1px solid var(--border)",
                        color: "var(--text-primary)",
                      }}
                      onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
                      onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                      Personal Access Token
                    </label>
                    <div className="relative">
                      <input
                        type={showToken ? "text" : "password"}
                        value={token}
                        onChange={(e) => { setToken(e.target.value); setRepoInfo(null); }}
                        placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                        className="w-full px-3.5 py-2.5 pr-10 rounded-xl text-sm font-mono outline-none transition-all"
                        style={{
                          background: "var(--bg-primary)",
                          border: "1px solid var(--border)",
                          color: "var(--text-primary)",
                        }}
                        onFocus={(e) => (e.currentTarget.style.borderColor = "var(--accent-blue)")}
                        onBlur={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
                      />
                      <button
                        onClick={() => setShowToken(!showToken)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 rounded"
                        style={{ color: "var(--text-muted)" }}
                      >
                        {showToken ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                    <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>
                      Needs <code>repo</code> scope. Never stored — used only for this session.
                    </p>
                  </div>

                  {/* Validate button */}
                  {!repoInfo?.valid && (
                    <button
                      onClick={handleValidate}
                      disabled={!canValidate || validating}
                      className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all w-full justify-center"
                      style={{
                        background: !canValidate || validating
                          ? "var(--bg-elevated)"
                          : "linear-gradient(135deg, #4f8ef7, #6366f1)",
                        color: "white",
                        opacity: !canValidate || validating ? 0.5 : 1,
                        cursor: !canValidate || validating ? "not-allowed" : "pointer",
                      }}
                    >
                      {validating ? (
                        <><Loader2 size={13} className="animate-spin" /> Validating...</>
                      ) : (
                        <><Shield size={13} /> Validate Connection</>
                      )}
                    </button>
                  )}

                  {/* Repo info card */}
                  {repoInfo?.valid && (
                    <motion.div
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-3 p-3 rounded-xl"
                      style={{ background: "var(--glow-green)", border: "1px solid rgba(34,197,94,0.15)" }}
                    >
                      <CheckCircle2 size={16} style={{ color: "var(--accent-green)" }} />
                      <div className="flex-1">
                        <p className="text-xs font-semibold" style={{ color: "var(--accent-green)" }}>
                          Connected to {repoInfo.repo}
                        </p>
                        <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                          {repoInfo.private ? "Private" : "Public"} • as @{repoInfo.username}
                          {repoInfo.is_mock && " • Mock Mode"}
                        </p>
                      </div>
                      <button
                        onClick={() => { setRepoInfo(null); setToken(""); }}
                        className="text-[10px] font-medium px-2 py-1 rounded"
                        style={{ color: "var(--text-muted)", background: "var(--bg-elevated)" }}
                      >
                        Change
                      </button>
                    </motion.div>
                  )}
                </div>
              </SectionCard>

              {/* Step 2: Analysis Config (visible after validation) */}
              <AnimatePresence>
                {repoInfo?.valid && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="space-y-4"
                  >
                    <SectionCard title="Analysis Configuration" icon={<Search size={14} />}>
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div>
                            <label className="text-[11px] font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                              Base Branch
                            </label>
                            <div className="relative">
                              <GitBranch size={12} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
                              <input
                                value={baseBranch}
                                onChange={(e) => setBaseBranch(e.target.value)}
                                placeholder="main"
                                className="w-full pl-8 pr-3 py-2 rounded-lg text-xs font-mono outline-none"
                                style={{
                                  background: "var(--bg-primary)",
                                  border: "1px solid var(--border)",
                                  color: "var(--text-primary)",
                                }}
                              />
                            </div>
                          </div>
                          <div>
                            <label className="text-[11px] font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                              Language
                            </label>
                            <select
                              value={language}
                              onChange={(e) => setLanguage(e.target.value)}
                              className="w-full px-3 py-2 rounded-lg text-xs font-medium outline-none"
                              style={{
                                background: "var(--bg-primary)",
                                border: "1px solid var(--border)",
                                color: "var(--text-primary)",
                              }}
                            >
                              {LANGUAGES.map((l) => (
                                <option key={l.value} value={l.value}>{l.label}</option>
                              ))}
                            </select>
                          </div>
                        </div>

                        <div>
                          <label className="text-[11px] font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                            Target File Path
                            <span className="font-normal ml-1" style={{ color: "var(--text-muted)" }}>(optional — auto-detected from logs)</span>
                          </label>
                          <div className="relative">
                            <FileCode size={12} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--text-muted)" }} />
                            <input
                              value={filePath}
                              onChange={(e) => setFilePath(e.target.value)}
                              placeholder="src/utils/calculate.py"
                              className="w-full pl-8 pr-3 py-2 rounded-lg text-xs font-mono outline-none"
                              style={{
                                background: "var(--bg-primary)",
                                border: "1px solid var(--border)",
                                color: "var(--text-primary)",
                              }}
                            />
                          </div>
                        </div>

                        <div>
                          <label className="text-[11px] font-medium block mb-1.5" style={{ color: "var(--text-secondary)" }}>
                            Error Logs / Console Output / Failing Test Output
                          </label>
                          <div className="relative">
                            <Terminal size={12} className="absolute left-3 top-3" style={{ color: "var(--text-muted)" }} />
                            <textarea
                              value={logs}
                              onChange={(e) => setLogs(e.target.value)}
                              placeholder={`Paste your error logs, console output, or test output here...\n\nExample:\n$ python -m pytest tests/test_utils.py\nFAILED tests/test_utils.py::test_calculate_total\nAssertionError: assert 100.0 == 125.00`}
                              rows={8}
                              className="w-full pl-8 pr-3 py-2.5 rounded-xl text-xs font-mono outline-none resize-y leading-relaxed"
                              style={{
                                background: "var(--bg-primary)",
                                border: "1px solid var(--border)",
                                color: "var(--text-primary)",
                                minHeight: 120,
                              }}
                            />
                          </div>
                        </div>
                      </div>
                    </SectionCard>

                    {/* Run Analysis button */}
                    <button
                      onClick={handleAnalyze}
                      disabled={!canAnalyze || step === "analyzing"}
                      className="flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-semibold transition-all w-full justify-center"
                      style={{
                        background: !canAnalyze || step === "analyzing"
                          ? "var(--bg-elevated)"
                          : "linear-gradient(135deg, #4f8ef7, #6366f1)",
                        color: "white",
                        opacity: !canAnalyze || step === "analyzing" ? 0.5 : 1,
                        cursor: !canAnalyze || step === "analyzing" ? "not-allowed" : "pointer",
                        boxShadow: canAnalyze && step !== "analyzing" ? "0 4px 20px rgba(79,142,247,0.3)" : "none",
                      }}
                    >
                      {step === "analyzing" ? (
                        <><Loader2 size={16} className="animate-spin" /> Analyzing Repository...</>
                      ) : (
                        <><Zap size={16} /> Run Analysis</>
                      )}
                    </button>

                    {!canAnalyze && repoInfo?.valid && (
                      <p className="text-[11px] text-center" style={{ color: "var(--text-muted)" }}>
                        Provide error logs or a target file path to start analysis
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>

        {/* Right: Results panel */}
        <AnimatePresence>
          {step === "results" && jobId && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: "55%", opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="border-l flex flex-col overflow-hidden"
              style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
            >
              <AnalysisPanel
                job={job}
                loading={jobLoading}
                onClose={() => {
                  setStep("input");
                  setJobId(null);
                }}
                token={token}
                baseBranch={baseBranch}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

/* ─── Section Card Component ─── */

function SectionCard({
  title,
  icon,
  badge,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-2xl p-5"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center gap-2 mb-4">
        <span style={{ color: "var(--accent-blue)" }}>{icon}</span>
        <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
          {title}
        </h3>
        {badge && (
          <span
            className="text-[10px] font-semibold px-2 py-0.5 rounded-full ml-auto"
            style={{ background: "var(--glow-green)", color: "var(--accent-green)" }}
          >
            {badge}
          </span>
        )}
      </div>
      {children}
    </div>
  );
}
