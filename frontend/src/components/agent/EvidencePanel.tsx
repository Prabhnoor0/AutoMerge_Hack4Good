"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  Shield, ShieldCheck, ShieldAlert, ShieldX,
  AlertTriangle, CheckCircle2, XCircle, Info,
  GitCommit, Activity, Zap, Eye,
  FlaskConical, TrendingUp, Bug, FileCode,
} from "lucide-react";
import type { Summary } from "@/lib/types";

interface Props {
  summary: Summary;
}

// ─── Helper: parse JSON fields safely ────────────────────

function safeParseJSON<T>(json: string | undefined, fallback: T): T {
  if (!json) return fallback;
  try {
    return JSON.parse(json) as T;
  } catch {
    return fallback;
  }
}

// ─── Types for parsed evidence data ─────────────────────

interface CommitTrace {
  suspect_commit?: string | null;
  suspect_file?: string | null;
  trace_method?: string;
  trace_confidence?: number;
  trace_reasoning?: string;
  timeline?: Array<{ event: string; label: string; detail: string; timestamp?: string | null }>;
  available?: boolean;
}

interface EvidenceItem {
  type: string;
  weight: number;
  detail: string;
}

interface GroupedEvidence {
  [key: string]: Array<{ label: string; detail: string }>;
}

interface EvidenceReport {
  evidence_items?: EvidenceItem[];
  grouped_evidence?: GroupedEvidence;
  evidence_score?: number;
  signal_quality?: string;
}

// ─── Main Component ─────────────────────────────────────

export function EvidencePanel({ summary }: Props) {
  const {
    triage_verdict,
    confidence_calibrated,
    reproducibility,
    flake_score,
    severity,
    next_action,
  } = summary;

  const whyReal = useMemo(() => safeParseJSON<string[]>(summary.why_real, []), [summary.why_real]);
  const whyNoise = useMemo(() => safeParseJSON<string[]>(summary.why_noise, []), [summary.why_noise]);
  const commitTrace = useMemo(() => safeParseJSON<CommitTrace>(summary.commit_trace_json, {}), [summary.commit_trace_json]);
  const evidenceReport = useMemo(() => safeParseJSON<EvidenceReport>(summary.evidence_report_json, {}), [summary.evidence_report_json]);

  // Don't render if no precision data
  if (!triage_verdict && !confidence_calibrated) {
    return null;
  }

  const confidence = confidence_calibrated ?? 0;
  const flake = flake_score ?? 0;

  return (
    <div className="space-y-4">
      {/* ── Verdict Banner ── */}
      <VerdictBanner verdict={triage_verdict || ""} confidence={confidence} severity={severity || ""} />

      {/* ── Metrics Row ── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <MetricCard
          label="Confidence"
          value={`${Math.round(confidence * 100)}%`}
          icon={<Shield size={14} />}
          color={confidence >= 0.7 ? "var(--accent-green)" : confidence >= 0.4 ? "var(--accent-amber)" : "var(--accent-red)"}
        />
        <MetricCard
          label="Reproducibility"
          value={formatReproducibility(reproducibility || "")}
          icon={<FlaskConical size={14} />}
          color={reproducibility === "reproducible" ? "var(--accent-green)" : reproducibility === "likely_flaky" ? "var(--accent-amber)" : "var(--text-muted)"}
        />
        <MetricCard
          label="Flake Score"
          value={`${Math.round(flake * 100)}%`}
          icon={<Zap size={14} />}
          color={flake < 0.3 ? "var(--accent-green)" : flake < 0.6 ? "var(--accent-amber)" : "var(--accent-red)"}
        />
        <MetricCard
          label="Severity"
          value={severity ? severity.charAt(0).toUpperCase() + severity.slice(1) : "—"}
          icon={<Bug size={14} />}
          color={
            severity === "critical" ? "var(--accent-red)" :
            severity === "high" ? "var(--accent-amber)" :
            severity === "medium" ? "var(--accent-cyan)" :
            "var(--text-muted)"
          }
        />
      </div>

      {/* ── Evidence Items ── */}
      {evidenceReport.evidence_items && evidenceReport.evidence_items.length > 0 && (
        <div
          className="rounded-lg p-4"
          style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
        >
          <div className="flex items-center gap-2 mb-3">
            <Eye size={14} style={{ color: "var(--accent-cyan)" }} />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
              Evidence Sources
            </span>
            {evidenceReport.evidence_score !== undefined && (
              <span
                className="ml-auto text-[11px] px-2 py-0.5 rounded-md font-medium"
                style={{
                  color: evidenceReport.evidence_score >= 0.6 ? "var(--accent-green)" : "var(--accent-amber)",
                  background: evidenceReport.evidence_score >= 0.6 ? "var(--glow-green)" : "rgba(245, 158, 11, 0.15)",
                }}
              >
                {Math.round(evidenceReport.evidence_score * 100)}% coverage
              </span>
            )}
          </div>
          <div className="space-y-2">
            {evidenceReport.evidence_items.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-2.5 text-xs"
              >
                <div
                  className="mt-0.5 w-5 h-5 rounded flex items-center justify-center flex-shrink-0"
                  style={{ background: "var(--bg-hover)" }}
                >
                  {getEvidenceIcon(item.type)}
                </div>
                <div className="min-w-0">
                  <span className="font-medium" style={{ color: "var(--text-primary)" }}>
                    {formatEvidenceType(item.type)}
                  </span>
                  <p className="text-[11px] mt-0.5 line-clamp-2" style={{ color: "var(--text-muted)" }}>
                    {item.detail}
                  </p>
                </div>
                <span className="ml-auto flex-shrink-0 text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>
                  +{Math.round(item.weight * 100)}%
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* ── Why Real / Why Noise ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {whyReal.length > 0 && (
          <div className="rounded-lg p-3.5" style={{ background: "rgba(34, 197, 94, 0.06)", border: "1px solid rgba(34, 197, 94, 0.15)" }}>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 size={13} style={{ color: "var(--accent-green)" }} />
              <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--accent-green)" }}>
                Why This Is Real
              </span>
            </div>
            <ul className="space-y-1.5">
              {whyReal.map((reason, i) => (
                <li key={i} className="text-xs flex items-start gap-1.5" style={{ color: "var(--text-secondary)" }}>
                  <span className="mt-1 w-1 h-1 rounded-full flex-shrink-0" style={{ background: "var(--accent-green)" }} />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {whyNoise.length > 0 && whyNoise[0] !== "No significant noise indicators" && (
          <div className="rounded-lg p-3.5" style={{ background: "rgba(245, 158, 11, 0.06)", border: "1px solid rgba(245, 158, 11, 0.15)" }}>
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={13} style={{ color: "var(--accent-amber)" }} />
              <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--accent-amber)" }}>
                Noise Indicators
              </span>
            </div>
            <ul className="space-y-1.5">
              {whyNoise.map((reason, i) => (
                <li key={i} className="text-xs flex items-start gap-1.5" style={{ color: "var(--text-secondary)" }}>
                  <span className="mt-1 w-1 h-1 rounded-full flex-shrink-0" style={{ background: "var(--accent-amber)" }} />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* ── Commit Trace ── */}
      {commitTrace.available && (
        <div className="rounded-lg p-4" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2 mb-3">
            <GitCommit size={14} style={{ color: "var(--accent-purple)" }} />
            <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-secondary)" }}>
              Commit Trace
            </span>
            <span
              className="ml-auto text-[10px] px-1.5 py-0.5 rounded font-medium"
              style={{ color: "var(--accent-purple)", background: "rgba(139, 92, 246, 0.15)" }}
            >
              {commitTrace.trace_method?.replace(/_/g, " ")}
            </span>
          </div>

          {/* Timeline */}
          {commitTrace.timeline && commitTrace.timeline.length > 0 && (
            <div className="relative pl-4 space-y-3">
              <div
                className="absolute left-[7px] top-1 bottom-1 w-px"
                style={{ background: "var(--border)" }}
              />
              {commitTrace.timeline.map((event, i) => (
                <div key={i} className="relative flex items-start gap-3">
                  <div
                    className="absolute left-[-13px] top-[5px] w-2 h-2 rounded-full"
                    style={{
                      background: event.event === "failure" ? "var(--accent-red)" :
                                  event.event === "commit" ? "var(--accent-purple)" :
                                  "var(--accent-cyan)",
                    }}
                  />
                  <div className="min-w-0">
                    <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                      {event.label}
                    </span>
                    <p className="text-[11px] mt-0.5" style={{ color: "var(--text-muted)" }}>
                      {event.detail}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {commitTrace.suspect_commit && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>Suspect:</span>
              <code
                className="text-[11px] px-2 py-0.5 rounded font-mono"
                style={{ background: "var(--bg-primary)", color: "var(--accent-purple)", border: "1px solid var(--border-subtle)" }}
              >
                {commitTrace.suspect_commit.slice(0, 8)}
              </code>
              {commitTrace.suspect_file && (
                <>
                  <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>in</span>
                  <code
                    className="text-[11px] px-2 py-0.5 rounded font-mono"
                    style={{ background: "var(--bg-primary)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}
                  >
                    {commitTrace.suspect_file}
                  </code>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Next Action ── */}
      {next_action && (
        <div
          className="rounded-lg p-3.5 flex items-start gap-3"
          style={{
            background: "rgba(79, 142, 247, 0.06)",
            border: "1px solid rgba(79, 142, 247, 0.15)",
          }}
        >
          <TrendingUp size={14} className="mt-0.5 flex-shrink-0" style={{ color: "var(--accent-blue)" }} />
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--accent-blue)" }}>
              Recommended Action
            </span>
            <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
              {next_action}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────

function VerdictBanner({ verdict, confidence, severity }: { verdict: string; confidence: number; severity: string }) {
  const config = getVerdictConfig(verdict);

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl p-4 flex items-center gap-4"
      style={{
        background: config.bg,
        border: `1px solid ${config.borderColor}`,
      }}
    >
      <div className="flex-shrink-0">{config.icon}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold" style={{ color: config.color }}>
            {config.label}
          </span>
          {severity && (
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-md font-semibold uppercase tracking-wider"
              style={{
                color: severity === "critical" ? "var(--accent-red)" : severity === "high" ? "var(--accent-amber)" : "var(--text-muted)",
                background: severity === "critical" ? "var(--glow-red)" : severity === "high" ? "rgba(245, 158, 11, 0.15)" : "var(--bg-hover)",
              }}
            >
              {severity}
            </span>
          )}
        </div>
        <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
          {config.description}
        </p>
      </div>
      <div className="text-right flex-shrink-0">
        <div className="text-xl font-bold font-mono" style={{ color: config.color }}>
          {Math.round(confidence * 100)}%
        </div>
        <div className="text-[10px]" style={{ color: "var(--text-muted)" }}>
          confidence
        </div>
      </div>
    </motion.div>
  );
}

function MetricCard({ label, value, icon, color }: { label: string; value: string; icon: React.ReactNode; color: string }) {
  return (
    <div
      className="rounded-lg p-3 flex flex-col gap-1"
      style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}
    >
      <div className="flex items-center gap-1.5">
        <span style={{ color }}>{icon}</span>
        <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
          {label}
        </span>
      </div>
      <span className="text-sm font-bold" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

// ─── Helpers ────────────────────────────────────────────

function getVerdictConfig(verdict: string) {
  switch (verdict) {
    case "high_confidence":
      return {
        icon: <ShieldCheck size={20} style={{ color: "var(--accent-green)" }} />,
        color: "var(--accent-green)",
        bg: "rgba(34, 197, 94, 0.08)",
        borderColor: "rgba(34, 197, 94, 0.2)",
        label: "High Confidence Bug",
        description: "Strong evidence supports this is a genuine, reproducible issue.",
      };
    case "moderate_confidence":
      return {
        icon: <Shield size={20} style={{ color: "var(--accent-cyan)" }} />,
        color: "var(--accent-cyan)",
        bg: "rgba(6, 182, 212, 0.08)",
        borderColor: "rgba(6, 182, 212, 0.2)",
        label: "Moderate Confidence",
        description: "Evidence suggests a real issue but manual review is recommended.",
      };
    case "low_confidence":
      return {
        icon: <ShieldAlert size={20} style={{ color: "var(--accent-amber)" }} />,
        color: "var(--accent-amber)",
        bg: "rgba(245, 158, 11, 0.08)",
        borderColor: "rgba(245, 158, 11, 0.2)",
        label: "Low Confidence",
        description: "Limited evidence — may be a false positive. Monitor for recurrence.",
      };
    case "likely_flaky":
      return {
        icon: <Zap size={20} style={{ color: "var(--accent-amber)" }} />,
        color: "var(--accent-amber)",
        bg: "rgba(245, 158, 11, 0.08)",
        borderColor: "rgba(245, 158, 11, 0.2)",
        label: "Likely Flaky",
        description: "Failure shows signs of intermittent behavior — investigate test stability.",
      };
    case "noise":
      return {
        icon: <ShieldX size={20} style={{ color: "var(--text-muted)" }} />,
        color: "var(--text-muted)",
        bg: "var(--bg-elevated)",
        borderColor: "var(--border)",
        label: "Likely Noise",
        description: "Weak signal — probably not a real bug. No action needed.",
      };
    case "low_signal":
      return {
        icon: <Info size={20} style={{ color: "var(--text-muted)" }} />,
        color: "var(--text-muted)",
        bg: "var(--bg-elevated)",
        borderColor: "var(--border)",
        label: "Low Signal",
        description: "Insufficient evidence to determine if this is a real issue.",
      };
    default:
      return {
        icon: <Activity size={20} style={{ color: "var(--text-secondary)" }} />,
        color: "var(--text-secondary)",
        bg: "var(--bg-elevated)",
        borderColor: "var(--border)",
        label: "Analysis Complete",
        description: "Review the evidence below for details.",
      };
  }
}

function formatReproducibility(repro: string): string {
  const map: Record<string, string> = {
    reproducible: "Reproducible",
    partially_reproducible: "Partial",
    likely_flaky: "Flaky",
    non_reproducible: "Not Repro",
    unknown: "Unknown",
  };
  return map[repro] || repro || "—";
}

function formatEvidenceType(type: string): string {
  const map: Record<string, string> = {
    stack_trace: "Stack Trace",
    error_message: "Error Message",
    file_references: "File References",
    test_names: "Test Names",
    multiple_signals: "Corroborating Signals",
    line_numbers: "Line Numbers",
    classification_hit: "Classification Match",
    pattern_recurrence: "Pattern Recurrence",
  };
  return map[type] || type.replace(/_/g, " ");
}

function getEvidenceIcon(type: string): React.ReactNode {
  const size = 11;
  const style = { color: "var(--text-muted)" };
  switch (type) {
    case "stack_trace": return <Activity size={size} style={style} />;
    case "error_message": return <AlertTriangle size={size} style={style} />;
    case "file_references": return <FileCode size={size} style={style} />;
    case "test_names": return <FlaskConical size={size} style={style} />;
    case "multiple_signals": return <Zap size={size} style={style} />;
    case "line_numbers": return <Info size={size} style={style} />;
    case "classification_hit": return <CheckCircle2 size={size} style={style} />;
    case "pattern_recurrence": return <Bug size={size} style={style} />;
    default: return <Eye size={size} style={style} />;
  }
}
