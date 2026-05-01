"use client";

import { motion } from "framer-motion";
import {
  Clock, GitCommit, Search, Zap, FileCode, Shield, Brain,
  CheckCircle2, AlertCircle, ChevronRight,
} from "lucide-react";
import { formatDuration } from "@/lib/utils";
import { STEP_LABELS, STATUS_COLORS } from "@/lib/types";
import type { PipelineStep, JobDetail } from "@/lib/types";

interface Props {
  job: JobDetail;
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  log_parsing: <Search size={14} />,
  signal_extraction: <Zap size={14} />,
  failure_classification: <GitCommit size={14} />,
  root_cause_analysis: <Brain size={14} />,
  patch_generation: <FileCode size={14} />,
  patch_validation: <Shield size={14} />,
  summary_generation: <CheckCircle2 size={14} />,
};

function getStepInsight(step: PipelineStep, job: JobDetail): string {
  const parsed = tryParseJSON(step.output_data);
  switch (step.step_name) {
    case "log_parsing":
      return parsed?.error_lines
        ? `Extracted ${parsed.error_lines.length} error signal(s) from raw logs`
        : "Parsed raw logs to identify failure boundaries";
    case "signal_extraction":
      return parsed?.primary_signal?.type
        ? `Primary signal: ${parsed.primary_signal.type} — ${parsed.primary_signal.message || "detected"}`
        : "Extracted key signals from parsed output";
    case "failure_classification":
      return `Classified as: ${job.failure_type || "unknown"} failure`;
    case "root_cause_analysis":
      return job.root_cause
        ? `Root cause identified: ${job.root_cause.slice(0, 120)}`
        : "Analyzed code patterns to determine origin";
    case "patch_generation":
      return job.patches.length > 0
        ? `Generated fix for ${job.patches[0]?.file_path || "target file"}`
        : "Attempted to generate a code patch";
    case "patch_validation":
      return job.validation
        ? `Validation: ${job.validation.tests_passed}/${job.validation.tests_total} tests passed`
        : "Ran fix through validation sandbox";
    case "summary_generation":
      return job.summary?.pr_title
        ? `PR ready: "${job.summary.pr_title}"`
        : "Generated human-readable summary";
    default:
      return "Processing step completed";
  }
}

function tryParseJSON(str: string): any {
  try { return JSON.parse(str); } catch { return null; }
}

export function ChronoTimeline({ job }: Props) {
  const steps = job.steps;
  if (steps.length === 0) return null;

  const totalDuration = steps.reduce((acc, s) => acc + s.duration_ms, 0);
  const completedSteps = steps.filter((s) => s.status === "completed");
  const failedSteps = steps.filter((s) => s.status === "failed");

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
          <Clock size={13} style={{ color: "var(--accent-cyan)" }} />
          <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
            {formatDuration(totalDuration)}
          </span>
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>total</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
          <CheckCircle2 size={13} style={{ color: "var(--accent-green)" }} />
          <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
            {completedSteps.length}/{steps.length}
          </span>
          <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>steps</span>
        </div>
        {failedSteps.length > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "var(--glow-red)" }}>
            <AlertCircle size={13} style={{ color: "var(--accent-red)" }} />
            <span className="text-xs font-semibold" style={{ color: "var(--accent-red)" }}>
              {failedSteps.length} failed
            </span>
          </div>
        )}
      </div>

      {/* Duration bar visualization */}
      {totalDuration > 0 && (
        <div className="flex h-2 rounded-full overflow-hidden gap-px" style={{ background: "var(--bg-elevated)" }}>
          {steps.map((step) => {
            const width = Math.max((step.duration_ms / totalDuration) * 100, 2);
            const color = STATUS_COLORS[step.status] || "var(--text-muted)";
            return (
              <motion.div
                key={step.id}
                initial={{ width: 0 }}
                animate={{ width: `${width}%` }}
                transition={{ duration: 0.5, delay: step.order_index * 0.08 }}
                className="h-full rounded-sm"
                style={{ background: color, opacity: 0.7 }}
                title={`${STEP_LABELS[step.step_name] || step.step_name}: ${formatDuration(step.duration_ms)}`}
              />
            );
          })}
        </div>
      )}

      {/* Timeline events */}
      <div className="space-y-0">
        {steps.map((step, i) => {
          const color = STATUS_COLORS[step.status] || "var(--text-muted)";
          const isLast = i === steps.length - 1;
          const insight = getStepInsight(step, job);

          return (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06 }}
              className="flex items-stretch gap-3"
            >
              {/* Timeline connector */}
              <div className="flex flex-col items-center w-7 flex-shrink-0">
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
                  style={{ background: `${color}20`, color }}
                >
                  {STEP_ICONS[step.step_name] || <GitCommit size={14} />}
                </div>
                {!isLast && (
                  <div
                    className="w-px flex-1 min-h-[16px]"
                    style={{ background: step.status === "completed" ? `${color}30` : "var(--border-subtle)" }}
                  />
                )}
              </div>

              {/* Event content */}
              <div className={`flex-1 ${isLast ? "pb-0" : "pb-3"}`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                    {STEP_LABELS[step.step_name] || step.step_name}
                  </span>
                  <div className="flex items-center gap-2">
                    {step.duration_ms > 0 && (
                      <span className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>
                        {formatDuration(step.duration_ms)}
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-xs mt-0.5 leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {insight}
                </p>
                {step.error_message && (
                  <p className="text-xs mt-1 font-mono px-2 py-1 rounded" style={{ color: "var(--accent-red)", background: "var(--glow-red)" }}>
                    {step.error_message}
                  </p>
                )}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Bug origin badge */}
      {job.root_cause && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="flex items-start gap-3 p-3.5 rounded-xl"
          style={{ background: "linear-gradient(135deg, rgba(139,92,246,0.08), rgba(79,142,247,0.08))", border: "1px solid rgba(139,92,246,0.15)" }}
        >
          <Brain size={16} className="mt-0.5 flex-shrink-0" style={{ color: "var(--accent-purple)" }} />
          <div>
            <p className="text-xs font-semibold" style={{ color: "var(--accent-purple)" }}>
              Bug Origin Traced
            </p>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--text-secondary)" }}>
              {job.root_cause}
            </p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
