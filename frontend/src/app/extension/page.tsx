"use client";
import { useState, useEffect, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useSearchParams } from "next/navigation";
import { MousePointer2, GitBranch, Package, Zap, FileEdit, HelpCircle, PlugZap, MessageCircle } from "lucide-react";
import { api } from "@/lib/api";
import type { ExtensionHistoryEntry, ExtensionFullReport } from "@/lib/types";

/* ── Helpers ───────────────────────────────────────── */
const SOURCE_LABELS: Record<string, { label: string; color: string; Icon: React.ElementType }> = {
  selection: { label: "Selection", color: "#4f8ef7", Icon: MousePointer2 },
  github: { label: "GitHub", color: "#22c55e", Icon: GitBranch },
  codeblock: { label: "Code Block", color: "#f59e0b", Icon: Package },
  web_editor: { label: "Web Editor", color: "#8b5cf6", Icon: Zap },
  textarea: { label: "Textarea", color: "#06b6d4", Icon: FileEdit },
  none: { label: "Unknown", color: "#6b7280", Icon: HelpCircle },
};

const LANG_COLORS: Record<string, string> = {
  python: "#3b82f6", javascript: "#f59e0b", typescript: "#06b6d4",
  java: "#ef4444", go: "#22c55e", rust: "#f97316", cpp: "#8b5cf6",
};

function confidenceStyle(c: number) {
  if (c >= 0.8) return { color: "#22c55e", bg: "rgba(34,197,94,0.12)" };
  if (c >= 0.5) return { color: "#f59e0b", bg: "rgba(245,158,11,0.12)" };
  return { color: "#ef4444", bg: "rgba(239,68,68,0.12)" };
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/* ── Report Panel ──────────────────────────────────── */
function ReportPanel({ report, onClose }: { report: ExtensionFullReport; onClose: () => void }) {
  const src = SOURCE_LABELS[report.source_type] || SOURCE_LABELS.none;
  const conf = confidenceStyle(report.confidence || 0);
  const langColor = LANG_COLORS[report.language] || "#6b7280";

  return (
    <motion.div
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      className="flex flex-col gap-4 overflow-auto"
      style={{ flex: 1, minWidth: 0 }}
    >
      {/* Header */}
      <div className="glass-card p-5 relative overflow-hidden">
        <div className="absolute inset-0 opacity-5" style={{ background: `radial-gradient(circle at 10% 50%, ${langColor}, transparent 60%)` }} />
        <div className="relative flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <src.Icon className="w-4 h-4" style={{ color: src.color }} />
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded" style={{ background: `${src.color}18`, color: src.color }}>{src.label}</span>
              <span className="text-[10px] px-2 py-0.5 rounded font-mono" style={{ background: `${langColor}18`, color: langColor }}>{report.language}</span>
              <span className="text-[10px] px-2 py-0.5 rounded font-bold" style={{ background: conf.bg, color: conf.color }}>{Math.round((report.confidence || 0) * 100)}% confidence</span>
            </div>
            <h2 className="text-base font-bold mb-1 truncate" style={{ color: "var(--text-primary)" }}>{report.filename || report.source_summary || "Browser Analysis"}</h2>
            {report.page_url && <p className="text-[10px] truncate" style={{ color: "var(--text-muted)" }}>{report.page_url}</p>}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-lg font-bold" style={{ color: report.issue_count > 0 ? "#ef4444" : "#22c55e" }}>{report.issue_count > 0 ? `⚠ ${report.issue_count}` : "✓ Clean"}</span>
            <button onClick={onClose} className="text-xs px-2 py-1 rounded-lg" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}>✕</button>
          </div>
        </div>
      </div>

      {/* Issue Summary */}
      {report.issue_summary && (
        <div className="glass-card p-4">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "#ef4444" }}>Issues</h3>
          <pre className="text-[10px] font-mono leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text-secondary)" }}>{report.issue_summary}</pre>
        </div>
      )}

      {/* Root Cause */}
      {report.root_cause && (
        <div className="glass-card p-4">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-amber)" }}>Root Cause</h3>
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{report.root_cause}</p>
        </div>
      )}

      {/* Explanation */}
      {report.explanation && (
        <div className="glass-card p-4">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-blue)" }}>Explanation</h3>
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{report.explanation}</p>
        </div>
      )}

      {/* Fix Suggestion */}
      {report.fix_suggestion && (
        <div className="glass-card p-4">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-green)" }}>Fix Suggestion</h3>
          <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{report.fix_suggestion}</p>
        </div>
      )}

      {/* Fixed Code diff */}
      {report.diff_text && (
        <div className="glass-card p-4">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-green)" }}>Patch / Diff</h3>
          <pre className="text-[10px] font-mono p-3 rounded-lg overflow-auto max-h-64 whitespace-pre-wrap"
            style={{ background: "var(--bg-primary)", color: "var(--text-secondary)" }}>{report.diff_text}</pre>
        </div>
      )}

      {/* Code snippet */}
      {report.code_snippet && (
        <div className="glass-card p-4">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>Analyzed Code</h3>
          <pre className="text-[10px] font-mono p-3 rounded-lg overflow-auto max-h-48 whitespace-pre-wrap"
            style={{ background: "var(--bg-primary)", color: "var(--text-muted)" }}>{report.code_snippet}</pre>
        </div>
      )}

      {/* Ask Devमित्र */}
      <div className="glass-card p-4">
        <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 flex items-center gap-1.5" style={{ color: "#a78bfa" }}><MessageCircle className="w-3.5 h-3.5" /> Ask Devमित्र</h3>
        <p className="text-[10px] mb-3" style={{ color: "var(--text-muted)" }}>
          This analysis has been pushed to Devमित्र context. Open the chat to ask follow-up questions about this code.
        </p>
        <a href={`/?devmitra=open&context=extension&id=${report.analysis_id}`}
          className="inline-block py-2 px-4 rounded-lg text-xs font-semibold"
          style={{ background: "rgba(139,92,246,0.15)", color: "#a78bfa", border: "1px solid rgba(139,92,246,0.25)" }}>
          Open Devमित्र Chat →
        </a>
      </div>
    </motion.div>
  );
}

/* ── Main Page ─────────────────────────────────────── */
function ExtensionPageContent() {
  const searchParams = useSearchParams();
  const reportId = searchParams.get("report");

  const [history, setHistory] = useState<ExtensionHistoryEntry[]>([]);
  const [selectedReport, setSelectedReport] = useState<ExtensionFullReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingReport, setLoadingReport] = useState(false);
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    if (reportId) openReport(reportId);
  }, [reportId]);

  const loadHistory = async () => {
    setLoading(true);
    try {
      const r = await api.extensionHistory(50);
      setHistory(r.data || []);
    } catch {}
    setLoading(false);
  };

  const openReport = async (id: string) => {
    setLoadingReport(true);
    try {
      const r = await api.extensionReport(id);
      setSelectedReport(r.data);
    } catch {}
    setLoadingReport(false);
  };

  const deleteReport = async (id: string) => {
    setDeleting(id);
    try {
      await api.extensionDeleteReport(id);
      setHistory(h => h.filter(e => e.analysis_id !== id));
      if (selectedReport?.analysis_id === id) setSelectedReport(null);
    } catch {}
    setDeleting(null);
  };

  const filtered = history.filter(h =>
    !search || h.filename?.toLowerCase().includes(search.toLowerCase()) ||
    h.page_url?.toLowerCase().includes(search.toLowerCase()) ||
    h.language?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-[calc(100vh-64px)]" style={{ background: "var(--bg-primary)" }}>
      {/* ── Sidebar ── */}
      <div className="w-80 flex-shrink-0 border-r flex flex-col" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
        {/* Header */}
        <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white" style={{ background: "linear-gradient(135deg,#4f8ef7,#8b5cf6)", boxShadow: "0 4px 16px rgba(79,142,247,0.3)" }}>
              <PlugZap className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Extension Reports</h1>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Chrome Extension Analysis History</p>
            </div>
          </div>
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by file, URL, language…"
            className="w-full px-3 py-2 rounded-lg text-xs border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
        </div>

        {/* Setup Guide */}
        <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border)", background: "rgba(79,142,247,0.05)" }}>
          <p className="text-[9px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--accent-blue)" }}>🔧 Install Extension</p>
          <p className="text-[9px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
            Open <code>chrome://extensions</code> → Load unpacked → Select the <code>chrome-extension/</code> folder.
          </p>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-auto p-2 space-y-1">
          {loading && <div className="text-center py-8 text-xs" style={{ color: "var(--text-muted)" }}>Loading…</div>}
          {!loading && filtered.length === 0 && (
            <div className="text-center py-10 space-y-2">
              <div className="flex justify-center opacity-30 text-gray-400"><PlugZap className="w-8 h-8" /></div>
              <p className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>No analyses yet</p>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Use the extension on a code page to analyze code.</p>
            </div>
          )}
          {filtered.map((h, i) => {
            const src = SOURCE_LABELS[h.source_type] || SOURCE_LABELS.none;
            const conf = confidenceStyle(h.confidence || 0);
            const langColor = LANG_COLORS[h.language] || "#6b7280";
            const isSelected = selectedReport?.analysis_id === h.analysis_id;
            return (
              <motion.div
                key={h.analysis_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                onClick={() => openReport(h.analysis_id)}
                className="w-full text-left p-3 rounded-xl transition-all cursor-pointer group"
                style={{ background: isSelected ? "var(--bg-elevated)" : "transparent", border: isSelected ? "1px solid var(--border)" : "1px solid transparent" }}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <src.Icon className="w-3.5 h-3.5 flex-shrink-0" style={{ color: src.color }} />
                  <span className="text-[10px] font-semibold flex-1 truncate" style={{ color: "var(--text-primary)" }}>
                    {h.filename || h.page_url?.split("/").slice(-1)[0] || "Browser code"}
                  </span>
                  <button onClick={e => { e.stopPropagation(); deleteReport(h.analysis_id); }}
                    className="text-[9px] opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ color: "var(--text-muted)" }}>
                    {deleting === h.analysis_id ? "…" : "🗑"}
                  </button>
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: `${src.color}15`, color: src.color }}>{src.label}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded font-mono" style={{ background: `${langColor}15`, color: langColor }}>{h.language}</span>
                  <span className="text-[9px] px-1.5 py-0.5 rounded font-bold" style={{ background: conf.bg, color: conf.color }}>{Math.round((h.confidence || 0) * 100)}%</span>
                  {h.issue_count > 0 && <span className="text-[9px]" style={{ color: "#ef4444" }}>⚠ {h.issue_count}</span>}
                  <span className="ml-auto text-[9px]" style={{ color: "var(--text-muted)" }}>{timeAgo(h.created_at)}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* ── Main Panel ── */}
      <div className="flex-1 overflow-auto p-6 space-y-4">
        <AnimatePresence mode="wait">
          {loadingReport && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center justify-center h-48">
              <div className="text-center space-y-3">
                <div className="w-10 h-10 mx-auto rounded-full border-4 border-t-transparent animate-spin"
                  style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }} />
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>Loading report…</p>
              </div>
            </motion.div>
          )}
          {!loadingReport && selectedReport && (
            <ReportPanel key={selectedReport.analysis_id} report={selectedReport as ExtensionFullReport} onClose={() => setSelectedReport(null)} />
          )}
          {!loadingReport && !selectedReport && (
            <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex items-center justify-center h-full min-h-64">
              <div className="text-center space-y-4 max-w-sm">
                <div className="w-20 h-20 mx-auto rounded-3xl flex items-center justify-center text-gray-400" style={{ background: "var(--bg-elevated)" }}>
                  <PlugZap className="w-10 h-10" />
                </div>
                <div>
                  <h2 className="text-lg font-bold mb-2" style={{ color: "var(--text-primary)" }}>AutoMerge Chrome Extension</h2>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
                    Install the extension, open a code page, click the icon, and analyze any code instantly.
                    Reports will appear here automatically.
                  </p>
                </div>
                <div className="p-4 rounded-xl text-left space-y-2" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}>
                  <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-blue)" }}>Quick Setup</p>
                  {["1. Open chrome://extensions", "2. Enable Developer Mode", "3. Click 'Load unpacked'", "4. Select chrome-extension/ folder", "5. Visit any code page and click the extension icon"].map((s, i) => (
                    <p key={i} className="text-[10px]" style={{ color: "var(--text-secondary)" }}>{s}</p>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function ExtensionPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-sm" style={{ color: "var(--text-muted)" }}>Loading…</div>}>
      <ExtensionPageContent />
    </Suspense>
  );
}
