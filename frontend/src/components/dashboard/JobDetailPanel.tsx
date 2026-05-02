// "use client";

// import { useState } from "react";
// import { motion } from "framer-motion";
// import {
//   CheckCircle2, AlertCircle, Clock, Shield, FileCode,
//   Brain, Target, GitPullRequest, Activity,
//   Fingerprint, ShieldAlert,
// } from "lucide-react";
// import { formatDuration, formatTime, confidenceLabel } from "@/lib/utils";
// import { STATUS_COLORS, STEP_LABELS } from "@/lib/types";
// import type { JobDetail } from "@/lib/types";
// import { PipelineTimeline } from "@/components/agent/PipelineTimeline";
// import { ChronoTimeline } from "@/components/agent/ChronoTimeline";
// import { BugMemoryPanel } from "@/components/agent/BugMemoryPanel";
// import { PreventionPanel } from "@/components/agent/PreventionPanel";
// import { EvidencePanel } from "@/components/agent/EvidencePanel";
// import { DiffViewer } from "@/components/diff/DiffViewer";
// import { LogViewer } from "@/components/logs/LogViewer";
// import { CreatePRButton } from "@/components/github/CreatePRButton";

// interface Props {
//   job: JobDetail;
//   loading: boolean;
// }

// export function JobDetailPanel({ job, loading }: Props) {
//   const isActive = !["completed", "failed"].includes(job.status);

//   return (
//     <div className="p-6 space-y-6 max-w-5xl mx-auto">
//       {/* Header */}
//       <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
//         <div className="flex items-start justify-between gap-4">
//           <div className="min-w-0 flex-1">
//             <h2 className="text-lg font-bold leading-tight" style={{ color: "var(--text-primary)" }}>
//               {job.failure_title}
//             </h2>
//             <div className="flex items-center gap-3 mt-2">
//               <StatusBadge status={job.status} />
//               <span className="text-xs" style={{ color: "var(--text-muted)" }}>
//                 {job.failure_type} • {job.failure_source}
//               </span>
//               <span className="text-xs" style={{ color: "var(--text-muted)" }}>
//                 {formatTime(job.created_at)}
//               </span>
//             </div>
//           </div>

//           {/* Confidence meter */}
//           {job.confidence_score > 0 && (
//             <div className="flex-shrink-0 text-right">
//               <div className="text-2xl font-bold" style={{ color: "var(--accent-cyan)" }}>
//                 {Math.round(job.confidence_score * 100)}%
//               </div>
//               <div className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
//                 {confidenceLabel(job.confidence_score)} Confidence
//               </div>
//               {job.summary?.triage_verdict && (
//                 <div
//                   className="mt-1 text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider inline-block"
//                   style={{
//                     color: getVerdictColor(job.summary.triage_verdict),
//                     background: `${getVerdictColor(job.summary.triage_verdict)}15`,
//                   }}
//                 >
//                   {job.summary.triage_verdict.replace(/_/g, " ")}
//                 </div>
//               )}
//             </div>
//           )}
//         </div>

//         {/* Progress bar for active jobs */}
//         {isActive && (
//           <div className="mt-4 h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-elevated)" }}>
//             <div className="h-full rounded-full progress-bar-animated" style={{ width: getProgressWidth(job.status) }} />
//           </div>
//         )}
//       </motion.div>

//       {/* ChronoDebugger Timeline */}
//       <Section icon={<Clock size={16} />} title="ChronoDebugger — Time-Travel Trace" delay={0.05}>
//         <ChronoTimeline job={job} />
//       </Section>

//       {/* Root Cause Analysis */}
//       {job.root_cause && (
//         <Section icon={<Brain size={16} />} title="Root Cause Analysis" delay={0.1}>
//           <div className="space-y-3">
//             <div className="p-4 rounded-lg" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
//               <div className="flex items-start gap-3">
//                 <Target size={16} className="mt-0.5 flex-shrink-0" style={{ color: "var(--accent-amber)" }} />
//                 <div>
//                   <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
//                     {job.root_cause}
//                   </p>
//                 </div>
//               </div>
//             </div>
//             {job.reasoning_trace && (
//               <div className="p-3 rounded-lg font-mono text-xs leading-relaxed whitespace-pre-wrap"
//                 style={{ background: "var(--bg-primary)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}>
//                 {job.reasoning_trace}
//               </div>
//             )}
//           </div>
//         </Section>
//       )}

//       {/* Precision Evidence Panel */}
//       {job.summary && job.summary.triage_verdict && (
//         <Section icon={<Shield size={16} />} title="Debugging Evidence — Precision Analysis" delay={0.12}>
//           <EvidencePanel summary={job.summary} />
//         </Section>
//       )}

//       {/* Patch Diff */}
//       {job.patches.length > 0 && (
//         <Section icon={<FileCode size={16} />} title="Generated Fix" delay={0.15}>
//           {job.patches.map((patch) => (
//             <DiffViewer key={patch.id} patch={patch} />
//           ))}
//         </Section>
//       )}

//       {/* Validation Results */}
//       {job.validation && (
//         <Section icon={<Shield size={16} />} title="Validation Results" delay={0.2}>
//           <ValidationPanel validation={job.validation} />
//         </Section>
//       )}

//       {/* Log Viewer */}
//       {job.raw_logs && (
//         <Section icon={<AlertCircle size={16} />} title="Raw Logs" delay={0.25} defaultCollapsed>
//           <LogViewer logs={job.raw_logs} />
//         </Section>
//       )}

//       {/* Bug Memory — Recurring Patterns */}
//       <Section icon={<Fingerprint size={16} />} title="Bug Memory — Pattern Intelligence" delay={0.25}>
//         <BugMemoryPanel currentFailureType={job.failure_type} />
//       </Section>

//       {/* Proactive Prevention */}
//       {job.status === "completed" && (
//         <Section icon={<ShieldAlert size={16} />} title="Proactive Prevention" delay={0.3}>
//           <PreventionPanel job={job} />
//         </Section>
//       )}

//       {/* PR Summary */}
//       {job.summary && (
//         <Section icon={<GitPullRequest size={16} />} title="PR Summary" delay={0.35}>
//           <PRSummary summary={job.summary} />
//         </Section>
//       )}

//       {/* GitHub PR Action */}
//       {job.status === "completed" && job.patches.length > 0 && (
//         <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
//           <CreatePRButton jobId={job.id} />
//         </motion.div>
//       )}
//     </div>
//   );
// }

// /* ─── Sub-components ─── */

// function Section({
//   icon, title, children, delay = 0, defaultCollapsed = false
// }: {
//   icon: React.ReactNode;
//   title: string;
//   children: React.ReactNode;
//   delay?: number;
//   defaultCollapsed?: boolean;
// }) {
//   const [collapsed, setCollapsed] = useState(defaultCollapsed);

//   return (
//     <motion.div
//       initial={{ opacity: 0, y: 8 }}
//       animate={{ opacity: 1, y: 0 }}
//       transition={{ delay }}
//       className="glass-card overflow-hidden"
//     >
//       <button
//         onClick={() => setCollapsed(!collapsed)}
//         className="w-full flex items-center gap-2.5 px-5 py-3.5 transition-colors"
//         style={{ color: "var(--text-secondary)" }}
//         onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
//         onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
//       >
//         {icon}
//         <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
//           {title}
//         </span>
//         <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
//           {collapsed ? "▸" : "▾"}
//         </span>
//       </button>
//       {!collapsed && (
//         <div className="px-5 pb-5">
//           {children}
//         </div>
//       )}
//     </motion.div>
//   );
// }



// function StatusBadge({ status }: { status: string }) {
//   const color = STATUS_COLORS[status] || "var(--text-muted)";
//   const isActive = !["completed", "failed"].includes(status);
//   return (
//     <span
//       className="inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded-md uppercase tracking-wider"
//       style={{ color, background: `${color}15` }}
//     >
//       <span
//         className={`status-dot ${isActive ? "running" : ""}`}
//         style={{ background: color, width: 6, height: 6 }}
//       />
//       {status}
//     </span>
//   );
// }

// function ValidationPanel({ validation }: { validation: NonNullable<JobDetail["validation"]> }) {
//   const passed = validation.status === "passed";
//   return (
//     <div className="space-y-3">
//       <div className="flex items-center gap-4">
//         <div
//           className="flex items-center gap-2 px-3 py-2 rounded-lg"
//           style={{
//             background: passed ? "var(--glow-green)" : "var(--glow-red)",
//             border: `1px solid ${passed ? "var(--accent-green)" : "var(--accent-red)"}30`,
//           }}
//         >
//           {passed ? (
//             <CheckCircle2 size={16} style={{ color: "var(--accent-green)" }} />
//           ) : (
//             <AlertCircle size={16} style={{ color: "var(--accent-red)" }} />
//           )}
//           <span className="text-sm font-semibold" style={{ color: passed ? "var(--accent-green)" : "var(--accent-red)" }}>
//             {passed ? "All Tests Passed" : "Tests Failed"}
//           </span>
//         </div>
//         <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
//           <span>
//             <span className="font-semibold" style={{ color: "var(--accent-green)" }}>
//               {validation.tests_passed}
//             </span>{" "}
//             passed
//           </span>
//           <span>
//             <span className="font-semibold" style={{ color: validation.tests_failed > 0 ? "var(--accent-red)" : "var(--text-muted)" }}>
//               {validation.tests_failed}
//             </span>{" "}
//             failed
//           </span>
//           <span>{validation.tests_total} total</span>
//           <span>{validation.duration_seconds.toFixed(2)}s</span>
//         </div>
//       </div>

//       {validation.stdout && (
//         <pre
//           className="text-xs p-3 rounded-lg overflow-x-auto max-h-48 overflow-y-auto font-mono leading-relaxed"
//           style={{ background: "var(--bg-primary)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
//         >
//           {validation.stdout}
//         </pre>
//       )}
//     </div>
//   );
// }

// function PRSummary({ summary }: { summary: NonNullable<JobDetail["summary"]> }) {
//   return (
//     <div className="space-y-3">
//       <div className="p-4 rounded-lg" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
//         <div className="flex items-center gap-2 mb-2">
//           <GitPullRequest size={14} style={{ color: "var(--accent-purple)" }} />
//           <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
//             {summary.pr_title}
//           </span>
//         </div>
//         <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
//           {summary.impact_assessment}
//         </p>
//       </div>

//       <div
//         className="p-4 rounded-lg font-mono text-xs leading-relaxed whitespace-pre-wrap"
//         style={{ background: "var(--bg-primary)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
//       >
//         {summary.pr_body}
//       </div>
//     </div>
//   );
// }

// function getProgressWidth(status: string): string {
//   const map: Record<string, string> = {
//     queued: "5%",
//     analyzing: "20%",
//     diagnosing: "40%",
//     patching: "60%",
//     validating: "75%",
//     summarizing: "90%",
//     retrying: "65%",
//   };
//   return map[status] || "100%";
// }

// function getVerdictColor(verdict: string): string {
//   const map: Record<string, string> = {
//     high_confidence: "var(--accent-green)",
//     moderate_confidence: "var(--accent-cyan)",
//     low_confidence: "var(--accent-amber)",
//     likely_flaky: "var(--accent-amber)",
//     noise: "var(--text-muted)",
//     low_signal: "var(--text-muted)",
//   };
//   return map[verdict] || "var(--text-secondary)";
// }


"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { motion } from "framer-motion";
import {
  CheckCircle2,
  AlertCircle,
  Clock,
  Shield,
  FileCode,
  Brain,
  Target,
  GitPullRequest,
  Fingerprint,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { formatTime, confidenceLabel } from "@/lib/utils";
import { STATUS_COLORS } from "@/lib/types";
import type { JobDetail } from "@/lib/types";
import { ChronoTimeline } from "@/components/agent/ChronoTimeline";
import { BugMemoryPanel } from "@/components/agent/BugMemoryPanel";
import { PreventionPanel } from "@/components/agent/PreventionPanel";
import { EvidencePanel } from "@/components/agent/EvidencePanel";
import { DiffViewer } from "@/components/diff/DiffViewer";
import { LogViewer } from "@/components/logs/LogViewer";
import { CreatePRButton } from "@/components/github/CreatePRButton";
import { BugCreatureCard } from "./BugCreatureCard";
import { NeuralPipeline } from "../pipeline/NeuralPipeline";

interface Props {
  job: JobDetail;
  loading: boolean;
}

export function JobDetailPanel({ job, loading }: Props) {
  const isActive = !["completed", "failed"].includes(job.status);
  const primaryDiffText = job.patches[0]?.diff_text;

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-lg font-bold leading-tight" style={{ color: "var(--text-primary)" }}>
                {job.failure_title}
              </h2>
              {loading && (
                <span
                  className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full"
                  style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}
                >
                  <Loader2 size={10} className="animate-spin" />
                  Updating
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <StatusBadge status={job.status} />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {job.failure_type} • {job.failure_source}
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {formatTime(job.created_at)}
              </span>
            </div>
          </div>

          {job.confidence_score > 0 && (
            <div className="flex-shrink-0 text-right">
              <div className="text-2xl font-bold" style={{ color: "var(--accent-cyan)" }}>
                {Math.round(job.confidence_score * 100)}%
              </div>
              <div className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
                {confidenceLabel(job.confidence_score)} Confidence
              </div>

              {job.summary?.triage_verdict && (
                <div
                  className="mt-1 text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase tracking-wider inline-block"
                  style={{
                    color: getVerdictColor(job.summary.triage_verdict),
                    background: `${getVerdictColor(job.summary.triage_verdict)}15`,
                  }}
                >
                  {job.summary.triage_verdict.replace(/_/g, " ")}
                </div>
              )}
            </div>
          )}
        </div>

        {isActive && (
          <div className="mt-4 h-1 rounded-full overflow-hidden" style={{ background: "var(--bg-elevated)" }}>
            <div
              className="h-full rounded-full progress-bar-animated"
              style={{ width: getProgressWidth(job.status) }}
            />
          </div>
        )}
      </motion.div>

      <div className="my-8">
        <NeuralPipeline currentStatus={job.status} />
      </div>

      <div className="my-6">
        <BugCreatureCard job={job} />
      </div>

      <Section icon={<Clock size={16} />} title="ChronoDebugger — Time-Travel Trace" delay={0.05}>
        <ChronoTimeline job={job} />
      </Section>

      {job.root_cause && (
        <Section icon={<Brain size={16} />} title="Root Cause Analysis" delay={0.1}>
          <div className="space-y-3">
            <div
              className="p-4 rounded-lg"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
            >
              <div className="flex items-start gap-3">
                <Target size={16} className="mt-0.5 flex-shrink-0" style={{ color: "var(--accent-amber)" }} />
                <div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    {job.root_cause}
                  </p>
                </div>
              </div>
            </div>

            {job.reasoning_trace && (
              <div
                className="p-3 rounded-lg font-mono text-xs leading-relaxed whitespace-pre-wrap"
                style={{
                  background: "var(--bg-primary)",
                  color: "var(--text-secondary)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                {job.reasoning_trace}
              </div>
            )}
          </div>
        </Section>
      )}

      {job.summary?.triage_verdict && (
        <Section icon={<Shield size={16} />} title="Debugging Evidence — Precision Analysis" delay={0.12}>
          <EvidencePanel summary={job.summary} />
        </Section>
      )}

      {job.patches.length > 0 && (
        <Section icon={<FileCode size={16} />} title="Generated Fix" delay={0.15}>
          {job.patches.map((patch) => (
            <DiffViewer key={patch.id} patch={patch} />
          ))}
        </Section>
      )}

      {job.validation && (
        <Section icon={<Shield size={16} />} title="Validation Results" delay={0.2}>
          <ValidationPanel validation={job.validation} />
        </Section>
      )}

      {job.raw_logs && (
        <Section icon={<AlertCircle size={16} />} title="Raw Logs" delay={0.25} defaultCollapsed>
          <LogViewer logs={job.raw_logs} />
        </Section>
      )}

      <Section icon={<Fingerprint size={16} />} title="Bug Memory — Pattern Intelligence" delay={0.25}>
        <BugMemoryPanel currentFailureType={job.failure_type} />
      </Section>

      {job.status === "completed" && (
        <Section icon={<ShieldAlert size={16} />} title="Proactive Prevention" delay={0.3}>
          <PreventionPanel job={job} />
        </Section>
      )}

      {job.summary && (
        <Section icon={<GitPullRequest size={16} />} title="PR Summary" delay={0.35}>
          <PRSummary summary={job.summary} />
        </Section>
      )}

      {job.status === "completed" && job.patches.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          <CreatePRButton jobId={job.id} diffText={primaryDiffText} />
        </motion.div>
      )}
    </div>
  );
}

function Section({
  icon,
  title,
  children,
  delay = 0,
  defaultCollapsed = false,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  delay?: number;
  defaultCollapsed?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="glass-card overflow-hidden"
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-2.5 px-5 py-3.5 transition-colors"
        style={{ color: "var(--text-secondary)" }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        {icon}
        <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {title}
        </span>
        <span className="ml-auto text-xs" style={{ color: "var(--text-muted)" }}>
          {collapsed ? "▸" : "▾"}
        </span>
      </button>

      {!collapsed && <div className="px-5 pb-5">{children}</div>}
    </motion.div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || "var(--text-muted)";
  const isActive = !["completed", "failed"].includes(status);

  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-1 rounded-md uppercase tracking-wider"
      style={{ color, background: `${color}15` }}
    >
      <span
        className={`status-dot ${isActive ? "running" : ""}`}
        style={{ background: color, width: 6, height: 6 }}
      />
      {status}
    </span>
  );
}

function ValidationPanel({ validation }: { validation: NonNullable<JobDetail["validation"]> }) {
  const passed = validation.status === "passed";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-4 flex-wrap">
        <div
          className="flex items-center gap-2 px-3 py-2 rounded-lg"
          style={{
            background: passed ? "var(--glow-green)" : "var(--glow-red)",
            border: `1px solid ${passed ? "var(--accent-green)" : "var(--accent-red)"}30`,
          }}
        >
          {passed ? (
            <CheckCircle2 size={16} style={{ color: "var(--accent-green)" }} />
          ) : (
            <AlertCircle size={16} style={{ color: "var(--accent-red)" }} />
          )}
          <span
            className="text-sm font-semibold"
            style={{ color: passed ? "var(--accent-green)" : "var(--accent-red)" }}
          >
            {passed ? "All Tests Passed" : "Tests Failed"}
          </span>
        </div>

        <div className="flex items-center gap-4 text-xs flex-wrap" style={{ color: "var(--text-muted)" }}>
          <span>
            <span className="font-semibold" style={{ color: "var(--accent-green)" }}>
              {validation.tests_passed}
            </span>{" "}
            passed
          </span>
          <span>
            <span
              className="font-semibold"
              style={{ color: validation.tests_failed > 0 ? "var(--accent-red)" : "var(--text-muted)" }}
            >
              {validation.tests_failed}
            </span>{" "}
            failed
          </span>
          <span>{validation.tests_total} total</span>
          <span>{validation.duration_seconds.toFixed(2)}s</span>
        </div>
      </div>

      {validation.stdout && (
        <pre
          className="text-xs p-3 rounded-lg overflow-x-auto max-h-48 overflow-y-auto font-mono leading-relaxed"
          style={{
            background: "var(--bg-primary)",
            color: "var(--text-secondary)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          {validation.stdout}
        </pre>
      )}
    </div>
  );
}

function PRSummary({ summary }: { summary: NonNullable<JobDetail["summary"]> }) {
  return (
    <div className="space-y-3">
      <div
        className="p-4 rounded-lg"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <GitPullRequest size={14} style={{ color: "var(--accent-purple)" }} />
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {summary.pr_title}
          </span>
        </div>
        <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
          {summary.impact_assessment}
        </p>
      </div>

      <div
        className="p-4 rounded-lg font-mono text-xs leading-relaxed whitespace-pre-wrap"
        style={{
          background: "var(--bg-primary)",
          color: "var(--text-secondary)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {summary.pr_body}
      </div>
    </div>
  );
}

function getProgressWidth(status: string): string {
  const map: Record<string, string> = {
    queued: "5%",
    analyzing: "20%",
    diagnosing: "40%",
    patching: "60%",
    validating: "75%",
    summarizing: "90%",
    retrying: "65%",
  };
  return map[status] || "100%";
}

function getVerdictColor(verdict: string): string {
  const map: Record<string, string> = {
    high_confidence: "var(--accent-green)",
    moderate_confidence: "var(--accent-cyan)",
    low_confidence: "var(--accent-amber)",
    likely_flaky: "var(--accent-amber)",
    noise: "var(--text-muted)",
    low_signal: "var(--text-muted)",
  };
  return map[verdict] || "var(--text-secondary)";
}