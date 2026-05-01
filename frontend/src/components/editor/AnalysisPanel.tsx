"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  X, Loader2, CheckCircle2, AlertCircle, Brain,
  Target, FileCode, Shield, Activity, GitPullRequest,
  Globe, GitBranch, ExternalLink, Clock, Fingerprint, ShieldAlert,
} from "lucide-react";
import { formatDuration, confidenceLabel } from "@/lib/utils";
import { STATUS_COLORS, STEP_LABELS } from "@/lib/types";
import type { JobDetail } from "@/lib/types";
import { PipelineTimeline } from "@/components/agent/PipelineTimeline";
import { ChronoTimeline } from "@/components/agent/ChronoTimeline";
import { BugMemoryPanel } from "@/components/agent/BugMemoryPanel";
import { PreventionPanel } from "@/components/agent/PreventionPanel";
import { DiffViewer } from "@/components/diff/DiffViewer";
import { LogViewer } from "@/components/logs/LogViewer";
import { CreatePRButton } from "@/components/github/CreatePRButton";

interface Props {
  job: JobDetail | null;
  loading: boolean;
  onClose: () => void;
  token?: string;
  baseBranch?: string;
}

export function AnalysisPanel({ job, loading, onClose, token, baseBranch }: Props) {
  return (
    <div className="flex flex-col h-full">
      {/* Panel header */}
      <div
        className="h-11 flex items-center justify-between px-4 border-b flex-shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}
      >
        <div className="flex items-center gap-2">
          <Brain size={14} style={{ color: "var(--accent-purple)" }} />
          <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
            Analysis Results
          </span>
          {job && (
            <span
              className="text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase"
              style={{
                color: STATUS_COLORS[job.status],
                background: `${STATUS_COLORS[job.status]}15`,
              }}
            >
              {job.status}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-md transition-colors"
          style={{ color: "var(--text-muted)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
        >
          <X size={14} />
        </button>
      </div>

      {/* Panel content */}
      <div className="flex-1 overflow-y-auto">
        {!job && loading ? (
          <LoadingState />
        ) : !job ? (
          <EmptyAnalysis />
        ) : (
          <AnalysisContent job={job} token={token} baseBranch={baseBranch} />
        )}
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 p-6">
      <div className="relative">
        <div
          className="w-12 h-12 rounded-2xl flex items-center justify-center"
          style={{ background: "var(--bg-elevated)" }}
        >
          <Loader2 size={20} className="animate-spin" style={{ color: "var(--accent-blue)" }} />
        </div>
        <div
          className="absolute -top-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center"
          style={{ background: "var(--accent-blue)" }}
        >
          <Brain size={9} color="white" />
        </div>
      </div>
      <div className="text-center">
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          AI Agent Working
        </p>
        <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
          Analyzing code and generating fix...
        </p>
      </div>
      <div className="w-full max-w-xs mt-4 space-y-2">
        {["Fetching file from repo", "Analyzing code", "Generating fix"].map((s, i) => (
          <div key={s} className="flex items-center gap-2 animate-pulse" style={{ animationDelay: `${i * 0.3}s` }}>
            <div className="w-4 h-4 rounded-full" style={{ background: "var(--bg-hover)" }} />
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>{s}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyAnalysis() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-3 p-6">
      <div
        className="w-12 h-12 rounded-2xl flex items-center justify-center"
        style={{ background: "var(--bg-elevated)" }}
      >
        <FileCode size={20} style={{ color: "var(--text-muted)" }} />
      </div>
      <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
        No analysis yet
      </p>
      <p className="text-xs text-center max-w-[200px]" style={{ color: "var(--text-muted)" }}>
        Submit a repo and logs to see results here
      </p>
    </div>
  );
}

function AnalysisContent({ job, token, baseBranch }: { job: JobDetail; token?: string; baseBranch?: string }) {
  const isActive = !["completed", "failed"].includes(job.status);

  return (
    <div className="p-4 space-y-4">
      {/* Repo info card (if from GitHub) */}
      {job.repo_owner && job.repo_name && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex items-center gap-3 p-3 rounded-xl"
          style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
        >
          <Globe size={16} style={{ color: "var(--accent-blue)" }} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
              {job.repo_owner}/{job.repo_name}
            </p>
            <div className="flex items-center gap-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
              <span className="flex items-center gap-1">
                <GitBranch size={9} /> {job.base_branch}
              </span>
              {job.target_file_path && (
                <span className="flex items-center gap-1">
                  <FileCode size={9} /> {job.target_file_path}
                </span>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Confidence score */}
      {job.confidence_score > 0 && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex items-center gap-3 p-3 rounded-xl"
          style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
        >
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, rgba(6,182,212,0.15), rgba(139,92,246,0.15))",
            }}
          >
            <span className="text-lg font-bold" style={{ color: "var(--accent-cyan)" }}>
              {Math.round(job.confidence_score * 100)}
            </span>
          </div>
          <div>
            <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              {confidenceLabel(job.confidence_score)} Confidence
            </p>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {job.failure_type} detected
            </p>
          </div>
        </motion.div>
      )}

      {/* Progress bar for active jobs */}
      {isActive && (
        <div className="h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-elevated)" }}>
          <div className="h-full rounded-full progress-bar-animated" style={{ width: getProgress(job.status) }} />
        </div>
      )}

      {/* ChronoDebugger Timeline */}
      <CollapsibleSection icon={<Clock size={14} />} title="ChronoDebugger" defaultOpen={isActive}>
        <ChronoTimeline job={job} />
      </CollapsibleSection>

      {/* Root Cause */}
      {job.root_cause && (
        <CollapsibleSection icon={<Target size={14} />} title="Root Cause" defaultOpen>
          <div
            className="p-3 rounded-lg text-sm leading-relaxed"
            style={{ background: "var(--bg-primary)", color: "var(--text-primary)", border: "1px solid var(--border-subtle)" }}
          >
            {job.root_cause}
          </div>
          {job.reasoning_trace && (
            <div
              className="mt-2 p-2.5 rounded-lg font-mono text-[11px] leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto"
              style={{ background: "var(--bg-primary)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}
            >
              {job.reasoning_trace}
            </div>
          )}
        </CollapsibleSection>
      )}

      {/* Generated Fix */}
      {job.patches.length > 0 && (
        <CollapsibleSection icon={<FileCode size={14} />} title="Generated Fix" defaultOpen>
          {job.patches.map((patch) => (
            <DiffViewer key={patch.id} patch={patch} />
          ))}
        </CollapsibleSection>
      )}

      {/* Validation */}
      {job.validation && (
        <CollapsibleSection icon={<Shield size={14} />} title="Validation" defaultOpen>
          <ValidationBadge validation={job.validation} />
        </CollapsibleSection>
      )}

      {/* PR Summary */}
      {job.summary && (
        <CollapsibleSection icon={<GitPullRequest size={14} />} title="PR Summary">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <GitPullRequest size={12} style={{ color: "var(--accent-purple)" }} />
              <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                {job.summary.pr_title}
              </span>
            </div>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>
              {job.summary.impact_assessment}
            </p>
            <pre
              className="text-[11px] p-2.5 rounded-lg font-mono whitespace-pre-wrap max-h-48 overflow-y-auto"
              style={{ background: "var(--bg-primary)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
            >
              {job.summary.pr_body}
            </pre>
          </div>
        </CollapsibleSection>
      )}

      {/* Bug Memory */}
      <CollapsibleSection icon={<Fingerprint size={14} />} title="Bug Memory">
        <BugMemoryPanel currentFailureType={job.failure_type} />
      </CollapsibleSection>

      {/* Proactive Prevention */}
      {job.status === "completed" && (
        <CollapsibleSection icon={<ShieldAlert size={14} />} title="Prevention">
          <PreventionPanel job={job} />
        </CollapsibleSection>
      )}

      {/* GitHub PR Link (if already created) */}
      {job.github_pr_url && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 rounded-xl"
          style={{ background: "var(--glow-green)", border: "1px solid rgba(34,197,94,0.15)" }}
        >
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 size={16} style={{ color: "var(--accent-green)" }} />
            <span className="text-sm font-semibold" style={{ color: "var(--accent-green)" }}>
              Pull Request Created
            </span>
          </div>
          <a
            href={job.github_pr_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-medium hover:underline"
            style={{ color: "var(--accent-blue)" }}
          >
            {job.github_pr_url} <ExternalLink size={10} />
          </a>
        </motion.div>
      )}

      {/* GitHub PR Action */}
      {job.status === "completed" && job.patches.length > 0 && !job.github_pr_url && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35 }}>
          <CreatePRButton jobId={job.id} token={token} baseBranch={baseBranch} />
        </motion.div>
      )}
    </div>
  );
}

/* ─── Helpers ─── */

function CollapsibleSection({
  icon, title, children, defaultOpen = false
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl overflow-hidden"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3.5 py-2.5 text-left transition-colors"
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        <span style={{ color: "var(--text-muted)" }}>{icon}</span>
        <span className="text-xs font-semibold flex-1" style={{ color: "var(--text-primary)" }}>
          {title}
        </span>
        <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && <div className="px-3.5 pb-3.5">{children}</div>}
    </motion.div>
  );
}

function ValidationBadge({ validation }: { validation: NonNullable<JobDetail["validation"]> }) {
  const passed = validation.status === "passed";
  return (
    <div className="space-y-2">
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-lg"
        style={{
          background: passed ? "var(--glow-green)" : "var(--glow-red)",
          border: `1px solid ${passed ? "var(--accent-green)" : "var(--accent-red)"}20`,
        }}
      >
        {passed ? (
          <CheckCircle2 size={14} style={{ color: "var(--accent-green)" }} />
        ) : (
          <AlertCircle size={14} style={{ color: "var(--accent-red)" }} />
        )}
        <span className="text-xs font-semibold" style={{ color: passed ? "var(--accent-green)" : "var(--accent-red)" }}>
          {passed ? "All Tests Passed" : "Tests Failed"}
        </span>
        <span className="text-[11px] ml-auto" style={{ color: "var(--text-muted)" }}>
          {validation.tests_passed}/{validation.tests_total} • {validation.duration_seconds.toFixed(1)}s
        </span>
      </div>
      {validation.stdout && (
        <pre
          className="text-[11px] p-2.5 rounded-lg font-mono leading-relaxed max-h-32 overflow-y-auto"
          style={{ background: "var(--bg-primary)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
        >
          {validation.stdout}
        </pre>
      )}
    </div>
  );
}

function getProgress(status: string): string {
  const m: Record<string, string> = {
    queued: "5%", analyzing: "20%", diagnosing: "40%",
    patching: "60%", validating: "75%", summarizing: "90%",
  };
  return m[status] || "100%";
}
