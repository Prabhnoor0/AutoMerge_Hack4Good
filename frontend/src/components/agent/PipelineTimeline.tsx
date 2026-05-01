"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Clock, AlertCircle, SkipForward } from "lucide-react";
import { formatDuration } from "@/lib/utils";
import { STEP_LABELS, STATUS_COLORS } from "@/lib/types";
import type { PipelineStep } from "@/lib/types";

interface Props {
  steps: PipelineStep[];
  currentStatus: string;
}

const STEP_ICONS: Record<string, React.ReactNode> = {
  pending: <Clock size={14} />,
  running: <Loader2 size={14} className="animate-spin" />,
  completed: <CheckCircle2 size={14} />,
  failed: <AlertCircle size={14} />,
  skipped: <SkipForward size={14} />,
};

export function PipelineTimeline({ steps, currentStatus }: Props) {
  if (steps.length === 0) {
    return (
      <div className="flex items-center gap-2 py-4">
        <Loader2 size={14} className="animate-spin" style={{ color: "var(--accent-blue)" }} />
        <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Initializing pipeline...
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {steps.map((step, i) => {
        const color = STATUS_COLORS[step.status] || "var(--text-muted)";
        const isLast = i === steps.length - 1;
        const isActive = step.status === "running";

        return (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="flex items-stretch gap-3"
          >
            {/* Timeline line + dot */}
            <div className="flex flex-col items-center w-6 flex-shrink-0">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${isActive ? "ring-2 ring-offset-1" : ""}`}
                style={{
                  background: `${color}20`,
                  color: color,
                  ringColor: isActive ? color : undefined,
                  ringOffsetColor: "var(--bg-card)",
                } as React.CSSProperties}
              >
                {STEP_ICONS[step.status]}
              </div>
              {!isLast && (
                <div
                  className="w-px flex-1 min-h-[20px]"
                  style={{
                    background: step.status === "completed" ? `${color}40` : "var(--border-subtle)",
                  }}
                />
              )}
            </div>

            {/* Step content */}
            <div className={`flex-1 pb-4 ${isLast ? "pb-0" : ""}`}>
              <div className="flex items-center justify-between">
                <span
                  className="text-sm font-medium"
                  style={{ color: isActive ? "var(--text-primary)" : step.status === "completed" ? "var(--text-primary)" : "var(--text-muted)" }}
                >
                  {STEP_LABELS[step.step_name] || step.step_name}
                </span>
                <div className="flex items-center gap-2">
                  {step.duration_ms > 0 && (
                    <span className="text-[11px] font-mono" style={{ color: "var(--text-muted)" }}>
                      {formatDuration(step.duration_ms)}
                    </span>
                  )}
                  <span
                    className="text-[10px] font-semibold uppercase tracking-wider"
                    style={{ color }}
                  >
                    {step.status}
                  </span>
                </div>
              </div>

              {step.error_message && (
                <p className="text-xs mt-1 font-mono" style={{ color: "var(--accent-red)" }}>
                  {step.error_message}
                </p>
              )}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
