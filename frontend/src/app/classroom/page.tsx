"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GraduationCap, RefreshCw, BookOpen, CheckCircle2, Clock,
  TrendingUp, AlertTriangle, ExternalLink, Trash2, PlayCircle,
  FileText, Lightbulb, ChevronDown, ChevronUp, BookMarked,
  Target, Layers, BarChart3,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ClassroomReport, ClassroomSummary, ClassroomResource } from "@/lib/types";

// ─── Resource type icon map ─────────────────────────────
const RESOURCE_ICON: Record<string, React.ReactNode> = {
  youtube: <PlayCircle size={14} />,
  docs: <FileText size={14} />,
  article: <BookOpen size={14} />,
  practice: <Lightbulb size={14} />,
};

const RESOURCE_COLOR: Record<string, string> = {
  youtube: "#ef4444",
  docs: "var(--accent-blue)",
  article: "var(--accent-cyan)",
  practice: "var(--accent-amber)",
};

const CATEGORY_LABELS: Record<string, string> = {
  concurrency: "Concurrency",
  type_system: "Type System",
  reliability: "Reliability",
  data_integrity: "Data Integrity",
  quality: "Quality",
  tooling: "Tooling",
  workflow: "Workflow",
  general: "General",
};

export default function ClassroomPage() {
  const [reports, setReports] = useState<ClassroomReport[]>([]);
  const [summary, setSummary] = useState<ClassroomSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [reportsData, summaryData] = await Promise.all([
        api.classroomReports(),
        api.classroomSummary(),
      ]);
      setReports(reportsData);
      setSummary(summaryData);
    } catch (e: any) {
      setError(e.message || "Failed to load classroom data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const data = await api.classroomRefresh();
      setReports(data);
      const summaryData = await api.classroomSummary();
      setSummary(summaryData);
    } catch (e: any) {
      setError(e.message || "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  };

  const handleUpdate = async (id: string, update: { status?: string; revision_done?: boolean }) => {
    try {
      const updated = await api.classroomUpdateReport(id, update);
      setReports((prev) => prev.map((r) => (r.id === id ? updated : r)));
      const summaryData = await api.classroomSummary();
      setSummary(summaryData);
    } catch {}
  };

  const handleDelete = async (id: string) => {
    try {
      await api.classroomDeleteReport(id);
      setReports((prev) => prev.filter((r) => r.id !== id));
      setDeleteConfirm(null);
      setExpandedId(null);
      const summaryData = await api.classroomSummary();
      setSummary(summaryData);
    } catch {}
  };

  const filtered = reports.filter((r) => {
    if (filter === "all") return true;
    if (filter === "open") return r.status === "open";
    if (filter === "in_progress") return r.status === "in_progress";
    if (filter === "completed") return r.status === "completed";
    if (filter === "revision_done") return r.revision_done;
    return true;
  });

  // ─── Loading state ─────────────────────────────
  if (loading) {
    return (
      <div className="h-full flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="text-center space-y-4">
          <div className="w-14 h-14 mx-auto rounded-2xl flex items-center justify-center" style={{ background: "var(--bg-elevated)" }}>
            <GraduationCap size={24} className="animate-pulse" style={{ color: "var(--accent-purple)" }} />
          </div>
          <div>
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Loading Classroom</p>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Analyzing your debugging history...</p>
          </div>
        </div>
      </div>
    );
  }

  // ─── Error state ───────────────────────────────
  if (error && reports.length === 0) {
    return (
      <div className="h-full flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="text-center space-y-4 max-w-sm">
          <div className="w-14 h-14 mx-auto rounded-2xl flex items-center justify-center" style={{ background: "var(--glow-red)" }}>
            <AlertTriangle size={24} style={{ color: "var(--accent-red)" }} />
          </div>
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Something went wrong</p>
          <p className="text-xs" style={{ color: "var(--text-muted)" }}>{error}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 rounded-lg text-xs font-semibold"
            style={{ background: "var(--bg-elevated)", color: "var(--text-primary)" }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-primary)" }}>
      {/* ─── Page Header ─── */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-shrink-0 px-8 pt-6 pb-4"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center"
              style={{
                background: "linear-gradient(135deg, rgba(139,92,246,0.15), rgba(79,142,247,0.15))",
                border: "1px solid rgba(139,92,246,0.2)",
              }}
            >
              <GraduationCap size={22} style={{ color: "var(--accent-purple)" }} />
            </div>
            <div>
              <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
                Classroom
              </h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                AI-generated learning reports from your debugging patterns
              </p>
            </div>
          </div>

          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: refreshing ? "var(--bg-elevated)" : "linear-gradient(135deg, #4f8ef7, #6366f1)",
              color: "white",
              opacity: refreshing ? 0.7 : 1,
            }}
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Analyzing..." : "Refresh Reports"}
          </button>
        </div>

        {/* ─── Summary Strip ─── */}
        {summary && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="flex gap-3 mt-5"
          >
            <StatCard icon={<Layers size={14} />} label="Total" value={summary.total_reports} color="var(--accent-blue)" />
            <StatCard icon={<Clock size={14} />} label="Open" value={summary.open_reports} color="var(--accent-amber)" />
            <StatCard icon={<BookMarked size={14} />} label="Revised" value={summary.revision_done_count} color="var(--accent-cyan)" />
            <StatCard icon={<CheckCircle2 size={14} />} label="Completed" value={summary.completed_count} color="var(--accent-green)" />
          </motion.div>
        )}

        {/* ─── Filters ─── */}
        <div className="flex gap-1.5 mt-4">
          {[
            { key: "all", label: "All" },
            { key: "open", label: "Open" },
            { key: "in_progress", label: "In Progress" },
            { key: "revision_done", label: "Revised" },
            { key: "completed", label: "Completed" },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className="px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
              style={{
                background: filter === f.key ? "var(--bg-elevated)" : "transparent",
                color: filter === f.key ? "var(--text-primary)" : "var(--text-muted)",
                border: filter === f.key ? "1px solid var(--border)" : "1px solid transparent",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* ─── Report List ─── */}
      <div className="flex-1 overflow-y-auto px-8 pb-8">
        {filtered.length === 0 ? (
          <EmptyState hasAnyReports={reports.length > 0} onRefresh={handleRefresh} refreshing={refreshing} />
        ) : (
          <div className="space-y-3 mt-2">
            <AnimatePresence mode="popLayout">
              {filtered.map((report, i) => (
                <ReportCard
                  key={report.id}
                  report={report}
                  index={i}
                  expanded={expandedId === report.id}
                  onToggle={() => setExpandedId(expandedId === report.id ? null : report.id)}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                  deleteConfirm={deleteConfirm}
                  setDeleteConfirm={setDeleteConfirm}
                />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Stat Card ───────────────────────────────────────────

function StatCard({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: number; color: string }) {
  return (
    <div
      className="flex items-center gap-3 px-4 py-3 rounded-xl flex-1"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
    >
      <div className="flex items-center justify-center w-8 h-8 rounded-lg" style={{ background: `${color}15`, color }}>
        {icon}
      </div>
      <div>
        <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{value}</p>
        <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</p>
      </div>
    </div>
  );
}

// ─── Empty State ─────────────────────────────────────────

function EmptyState({ hasAnyReports, onRefresh, refreshing }: { hasAnyReports: boolean; onRefresh: () => void; refreshing: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-20 text-center"
    >
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
        style={{ background: "linear-gradient(135deg, rgba(139,92,246,0.1), rgba(79,142,247,0.1))" }}
      >
        <GraduationCap size={28} style={{ color: "var(--accent-purple)" }} />
      </div>
      {hasAnyReports ? (
        <>
          <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
            No reports match this filter
          </p>
          <p className="text-xs mt-1 max-w-xs" style={{ color: "var(--text-muted)" }}>
            Try selecting a different filter above.
          </p>
        </>
      ) : (
        <>
          <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            No learning reports yet
          </p>
          <p className="text-xs mt-2 max-w-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
            Classroom generates reports by analyzing your debugging history.
            Run some debugging jobs first, then click <strong>Refresh Reports</strong> to
            let AutoMerge identify your recurring weakness areas.
          </p>
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="mt-5 flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold"
            style={{
              background: "linear-gradient(135deg, #4f8ef7, #6366f1)",
              color: "white",
            }}
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Analyzing..." : "Generate Reports"}
          </button>
        </>
      )}
    </motion.div>
  );
}

// ─── Report Card ─────────────────────────────────────────

function ReportCard({
  report,
  index,
  expanded,
  onToggle,
  onUpdate,
  onDelete,
  deleteConfirm,
  setDeleteConfirm,
}: {
  report: ClassroomReport;
  index: number;
  expanded: boolean;
  onToggle: () => void;
  onUpdate: (id: string, update: { status?: string; revision_done?: boolean }) => void;
  onDelete: (id: string) => void;
  deleteConfirm: string | null;
  setDeleteConfirm: (id: string | null) => void;
}) {
  const isCompleted = report.status === "completed";
  const severityColor =
    report.severity_score >= 0.7 ? "var(--accent-red)" :
    report.severity_score >= 0.4 ? "var(--accent-amber)" :
    "var(--accent-cyan)";

  const severityLabel =
    report.severity_score >= 0.7 ? "High" :
    report.severity_score >= 0.4 ? "Medium" : "Low";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-xl overflow-hidden"
      style={{
        background: "var(--bg-card)",
        border: `1px solid ${isCompleted ? "var(--border-subtle)" : "var(--border)"}`,
        opacity: isCompleted ? 0.7 : 1,
      }}
    >
      {/* Card header — always visible */}
      <button
        onClick={onToggle}
        className="w-full text-left px-5 py-4 flex items-start gap-4 transition-colors"
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        {/* Severity indicator */}
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{ background: `${severityColor}12` }}
        >
          <BarChart3 size={18} style={{ color: severityColor }} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              {report.title}
            </h3>
            {/* Status badge */}
            <span
              className="text-[9px] font-bold px-2 py-0.5 rounded-full uppercase"
              style={{
                background: isCompleted ? "rgba(34,197,94,0.1)" : report.status === "in_progress" ? "rgba(79,142,247,0.1)" : "rgba(245,158,11,0.1)",
                color: isCompleted ? "var(--accent-green)" : report.status === "in_progress" ? "var(--accent-blue)" : "var(--accent-amber)",
              }}
            >
              {report.status.replace("_", " ")}
            </span>
            {report.revision_done && (
              <span
                className="text-[9px] font-bold px-2 py-0.5 rounded-full uppercase"
                style={{ background: "rgba(6,182,212,0.1)", color: "var(--accent-cyan)" }}
              >
                Revised
              </span>
            )}
          </div>

          <p className="text-xs mt-1 line-clamp-2" style={{ color: "var(--text-muted)" }}>
            {report.weakness_summary}
          </p>

          <div className="flex items-center gap-4 mt-2 text-[10px]" style={{ color: "var(--text-muted)" }}>
            <span className="flex items-center gap-1">
              <Target size={10} style={{ color: severityColor }} />
              {severityLabel} severity
            </span>
            <span className="flex items-center gap-1">
              <TrendingUp size={10} />
              {report.occurrence_count}× seen
            </span>
            <span className="flex items-center gap-1">
              <Layers size={10} />
              {CATEGORY_LABELS[report.topic_category] || report.topic_category}
            </span>
            <span>
              {new Date(report.report_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </span>
          </div>
        </div>

        <div className="flex-shrink-0 mt-2">
          {expanded ? <ChevronUp size={16} style={{ color: "var(--text-muted)" }} /> : <ChevronDown size={16} style={{ color: "var(--text-muted)" }} />}
        </div>
      </button>

      {/* Expanded details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-4 border-t" style={{ borderColor: "var(--border-subtle)" }}>
              {/* Why it matters */}
              <div className="pt-4">
                <h4 className="text-xs font-semibold mb-2 flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
                  <AlertTriangle size={12} style={{ color: "var(--accent-amber)" }} />
                  Why This Matters
                </h4>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                  {report.why_it_matters}
                </p>
              </div>

              {/* Evidence */}
              {report.evidence.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold mb-2 flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
                    <Target size={12} style={{ color: "var(--accent-red)" }} />
                    Evidence from Your History
                  </h4>
                  <div className="space-y-1.5">
                    {report.evidence.map((e, i) => (
                      <div
                        key={i}
                        className="text-[11px] px-3 py-2 rounded-lg font-mono"
                        style={{ background: "var(--bg-elevated)", color: "var(--text-muted)", border: "1px solid var(--border-subtle)" }}
                      >
                        {e}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Level Up Resources */}
              {report.resources.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold mb-2 flex items-center gap-1.5" style={{ color: "var(--text-secondary)" }}>
                    <BookOpen size={12} style={{ color: "var(--accent-purple)" }} />
                    Level Up — Learning Resources
                  </h4>
                  <div className="space-y-2">
                    {report.resources.map((res, i) => (
                      <ResourceCard key={i} resource={res} />
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 pt-2 flex-wrap">
                {!report.revision_done && (
                  <button
                    onClick={() => onUpdate(report.id, { revision_done: true, status: "in_progress" })}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors"
                    style={{ background: "rgba(6,182,212,0.1)", color: "var(--accent-cyan)", border: "1px solid rgba(6,182,212,0.15)" }}
                  >
                    <BookMarked size={12} />
                    Mark Revision Done
                  </button>
                )}
                {report.status !== "completed" && (
                  <button
                    onClick={() => onUpdate(report.id, { status: "completed" })}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors"
                    style={{ background: "rgba(34,197,94,0.1)", color: "var(--accent-green)", border: "1px solid rgba(34,197,94,0.15)" }}
                  >
                    <CheckCircle2 size={12} />
                    Complete
                  </button>
                )}
                {report.status === "completed" && (
                  <button
                    onClick={() => onUpdate(report.id, { status: "open" })}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors"
                    style={{ background: "var(--bg-elevated)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
                  >
                    <RefreshCw size={12} />
                    Reopen
                  </button>
                )}

                {/* Delete */}
                {deleteConfirm === report.id ? (
                  <div className="flex items-center gap-1.5 ml-auto">
                    <span className="text-[10px]" style={{ color: "var(--accent-red)" }}>Delete?</span>
                    <button
                      onClick={() => onDelete(report.id)}
                      className="px-2.5 py-1.5 rounded text-[10px] font-bold"
                      style={{ background: "var(--glow-red)", color: "var(--accent-red)" }}
                    >
                      Yes
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="px-2.5 py-1.5 rounded text-[10px] font-bold"
                      style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setDeleteConfirm(report.id)}
                    className="flex items-center gap-1 px-2.5 py-2 rounded-lg text-xs transition-colors ml-auto"
                    style={{ color: "var(--text-muted)" }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent-red)")}
                    onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── Resource Card ───────────────────────────────────────

function ResourceCard({ resource }: { resource: ClassroomResource }) {
  const typeColor = RESOURCE_COLOR[resource.type] || "var(--accent-blue)";

  return (
    <a
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-3 p-3 rounded-lg transition-colors group"
      style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--border)")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--border-subtle)")}
    >
      <div
        className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5"
        style={{ background: `${typeColor}15`, color: typeColor }}
      >
        {RESOURCE_ICON[resource.type] || <BookOpen size={14} />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold group-hover:underline" style={{ color: "var(--text-primary)" }}>
            {resource.title}
          </span>
          <ExternalLink size={10} style={{ color: "var(--text-muted)" }} />
        </div>
        <p className="text-[10px] mt-0.5 leading-relaxed" style={{ color: "var(--text-muted)" }}>
          {resource.why_this_helps}
        </p>
        <span
          className="inline-block text-[9px] font-bold uppercase mt-1 px-1.5 py-0.5 rounded"
          style={{ background: `${typeColor}10`, color: typeColor }}
        >
          {resource.type}
        </span>
      </div>
    </a>
  );
}
