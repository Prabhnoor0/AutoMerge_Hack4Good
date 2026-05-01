"use client";

import { motion } from "framer-motion";
import { ShieldAlert, Eye, Lightbulb } from "lucide-react";
import type { JobDetail } from "@/lib/types";

interface Props {
  job: JobDetail;
}

interface RiskItem {
  icon: React.ReactNode;
  title: string;
  description: string;
  severity: "high" | "medium" | "low";
}

function generateRiskHints(job: JobDetail): RiskItem[] {
  const risks: RiskItem[] = [];

  // Derive risks from failure type
  if (job.failure_type === "test_failure") {
    risks.push({
      icon: <Eye size={14} />,
      title: "Missing Edge Case Coverage",
      description:
        "This test failure suggests uncovered edge cases. Consider adding boundary-value tests and null-input scenarios to prevent regressions.",
      severity: "high",
    });
    risks.push({
      icon: <Lightbulb size={14} />,
      title: "Add Input Validation Guards",
      description:
        "Functions that process external input should validate types and ranges before operating on data.",
      severity: "medium",
    });
  }

  if (job.failure_type === "build_error" || job.failure_type === "type_error") {
    risks.push({
      icon: <ShieldAlert size={14} />,
      title: "Strengthen Type Safety",
      description:
        "Enable stricter compiler options (e.g. strict: true in tsconfig.json, or mypy --strict) to catch type mismatches before they reach CI.",
      severity: "high",
    });
    risks.push({
      icon: <Lightbulb size={14} />,
      title: "Add Pre-Commit Hooks",
      description:
        "Use lint-staged + husky to run type checks before every commit, catching build errors at development time.",
      severity: "medium",
    });
  }

  if (job.failure_type === "runtime_error") {
    risks.push({
      icon: <Eye size={14} />,
      title: "Null Reference Risk",
      description:
        "Runtime errors frequently stem from null or undefined access. Consider using optional chaining (?.) and nullish coalescing (??) operators.",
      severity: "high",
    });
  }

  // Generic prevention tips based on confidence
  if (job.confidence_score >= 0.8) {
    risks.push({
      icon: <Lightbulb size={14} />,
      title: "Automate This Fix Pattern",
      description:
        "High confidence suggests this is a well-understood pattern. Consider adding a custom lint rule or automated test to prevent recurrence.",
      severity: "low",
    });
  }

  // Retry-based risk
  if (job.retry_count > 0) {
    risks.push({
      icon: <ShieldAlert size={14} />,
      title: "Flaky Fix Detected",
      description:
        `This job required ${job.retry_count} retry(s). The original fix may have been incomplete. Review the patch carefully before merging.`,
      severity: "medium",
    });
  }

  return risks;
}

const SEVERITY_COLORS: Record<string, string> = {
  high: "var(--accent-red)",
  medium: "var(--accent-amber)",
  low: "var(--accent-cyan)",
};

const SEVERITY_BG: Record<string, string> = {
  high: "var(--glow-red)",
  medium: "rgba(245,158,11,0.1)",
  low: "rgba(6,182,212,0.08)",
};

export function PreventionPanel({ job }: Props) {
  const risks = generateRiskHints(job);

  if (risks.length === 0) return null;

  return (
    <div className="space-y-2">
      {risks.map((risk, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08 }}
          className="flex items-start gap-3 p-3 rounded-xl"
          style={{
            background: SEVERITY_BG[risk.severity],
            border: `1px solid ${SEVERITY_COLORS[risk.severity]}20`,
          }}
        >
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
            style={{ color: SEVERITY_COLORS[risk.severity] }}
          >
            {risk.icon}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>
                {risk.title}
              </span>
              <span
                className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase"
                style={{
                  color: SEVERITY_COLORS[risk.severity],
                  background: `${SEVERITY_COLORS[risk.severity]}15`,
                }}
              >
                {risk.severity}
              </span>
            </div>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {risk.description}
            </p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
