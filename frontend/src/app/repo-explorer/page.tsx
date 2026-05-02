"use client";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import {
  OverviewTab, ArchTab, InsightsTab, ContributorTab,
  FilesTab, DiagramsTab, QATab, HistoryTab,
} from "@/components/repo-explorer/ExplorerTabs";

const TABS = ["Overview", "Architecture", "Insights", "Contributor", "Files", "Q&A", "Diagrams", "History"] as const;
type Tab = (typeof TABS)[number];

const TAB_ICONS: Record<Tab, string> = {
  Overview: "📊", Architecture: "🏗️", Insights: "🔍", Contributor: "🤝",
  Files: "📁", "Q&A": "💬", Diagrams: "📐", History: "🕐",
};

export default function RepoExplorerPage() {
  const [repoUrl, setRepoUrl] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("");
  const [error, setError] = useState("");
  const [report, setReport] = useState<any>(null);
  const [tab, setTab] = useState<Tab>("Overview");
  const [history, setHistory] = useState<any[]>([]);
  const [question, setQuestion] = useState("");
  const [qaLoading, setQaLoading] = useState(false);
  const [qaHistory, setQaHistory] = useState<any[]>([]);
  const qaEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { loadHistory(); }, []);
  useEffect(() => { qaEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [qaHistory]);

  const loadHistory = async () => {
    try { const res = await api.repoExplorerHistory(); setHistory(res.data || []); } catch {}
  };

  const analyze = async () => {
    if (!repoUrl.trim()) return;
    setLoading(true); setError(""); setProgress(5);
    setProgressLabel("Connecting to GitHub...");
    const labels = [
      "Fetching repository tree...", "Downloading key files...",
      "Detecting tech stack...", "Analyzing structure...",
      "Generating report...", "Building diagrams...", "Finalizing..."
    ];
    let step = 0;
    const interval = setInterval(() => {
      step++;
      setProgress(p => Math.min(p + 12, 92));
      setProgressLabel(labels[Math.min(step, labels.length - 1)]);
    }, 600);
    try {
      const res = await api.repoExplorerAnalyze(repoUrl.trim(), token.trim());
      setReport(res.data); setQaHistory(res.data?.qa_history || []);
      setTab("Overview"); setProgress(100); setProgressLabel("Complete!");
      loadHistory();
    } catch (e: any) {
      setError(e.message || "Analysis failed");
    } finally {
      clearInterval(interval);
      setTimeout(() => { setLoading(false); setProgress(0); setProgressLabel(""); }, 600);
    }
  };

  const loadReport = async (id: string) => {
    try { const res = await api.repoExplorerReport(id); setReport(res.data); setQaHistory(res.data?.qa_history || []); setTab("Overview"); } catch {}
  };

  const askQuestion = async () => {
    if (!question.trim() || !report?.id) return;
    setQaLoading(true);
    const q = question; setQuestion("");
    setQaHistory(h => [...h, { question: q, answer: "..." }]);
    try {
      const res = await api.repoExplorerAsk(report.id, q);
      setQaHistory(h => { const c = [...h]; c[c.length - 1] = { question: q, answer: res.data?.answer || "No answer" }; return c; });
    } catch {
      setQaHistory(h => { const c = [...h]; c[c.length - 1] = { question: q, answer: "Error getting answer." }; return c; });
    }
    setQaLoading(false);
  };

  const deleteItem = async (id: string) => {
    await api.repoExplorerDeleteHistory(id);
    loadHistory();
    if (report?.id === id) setReport(null);
  };

  const r = report?.report;
  const st = report?.structure;
  const dg = report?.diagrams;

  return (
    <div className="flex h-[calc(100vh-64px)]" style={{ background: "var(--bg-primary)" }}>
      {/* ─── Sidebar ─── */}
      <aside className="w-72 flex-shrink-0 border-r flex flex-col" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
        <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
            <span className="w-7 h-7 rounded-lg flex items-center justify-center text-xs" style={{ background: "linear-gradient(135deg,#4f8ef7,#8b5cf6)", color: "white" }}>D</span>
            Devमित्र Explorer
          </h2>
          <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>Deep Repository Intelligence</p>
        </div>
        <div className="flex-1 overflow-auto p-3 space-y-1">
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>History</p>
          {history.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No repos analyzed yet</p>}
          {history.map(h => (
            <div key={h.id} onClick={() => loadReport(h.id)}
              className="p-2.5 rounded-lg cursor-pointer transition-all group"
              style={{ background: report?.id === h.id ? "var(--bg-elevated)" : "transparent" }}
              onMouseEnter={e => e.currentTarget.style.background = "var(--bg-hover)"}
              onMouseLeave={e => e.currentTarget.style.background = report?.id === h.id ? "var(--bg-elevated)" : "transparent"}>
              <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>{h.repo_name}</p>
              <p className="text-[10px] truncate" style={{ color: "var(--text-muted)" }}>{h.owner}/{h.repo_name}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--glow-blue)", color: "var(--accent-blue)" }}>{h.languages?.split(",")[0]}</span>
                <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{h.total_files} files</span>
                <span className="text-[10px]" style={{ color: h.health_score >= 70 ? "var(--accent-green)" : "var(--accent-amber)" }}>{h.health_score}%</span>
                <button onClick={e => { e.stopPropagation(); deleteItem(h.id); }} className="ml-auto text-[10px] opacity-0 group-hover:opacity-100" style={{ color: "var(--accent-red)" }}>✕</button>
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* ─── Main ─── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Input Bar */}
        <div className="p-4 border-b flex gap-3 items-end" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
          <div className="flex-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--text-muted)" }}>GitHub Repository URL</label>
            <input value={repoUrl} onChange={e => setRepoUrl(e.target.value)} placeholder="https://github.com/owner/repo"
              onKeyDown={e => e.key === "Enter" && analyze()}
              className="w-full px-3 py-2 rounded-lg text-sm border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
          </div>
          <div className="w-48">
            <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--text-muted)" }}>Token (optional)</label>
            <input value={token} onChange={e => setToken(e.target.value)} placeholder="ghp_..." type="password"
              className="w-full px-3 py-2 rounded-lg text-sm border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
          </div>
          <button onClick={analyze} disabled={loading || !repoUrl.trim()}
            className="px-5 py-2 rounded-lg text-sm font-semibold transition-all"
            style={{ background: loading ? "var(--bg-elevated)" : "linear-gradient(135deg,#4f8ef7,#6366f1)", color: "white", opacity: loading ? 0.7 : 1 }}>
            {loading ? "Analyzing..." : "🔍 Analyze"}
          </button>
        </div>

        {/* Progress */}
        {loading && (
          <div>
            <div className="h-1 w-full" style={{ background: "var(--bg-elevated)" }}>
              <motion.div className="h-full progress-bar-animated" initial={{ width: 0 }} animate={{ width: `${progress}%` }} transition={{ duration: 0.3 }} />
            </div>
            <div className="px-4 py-1.5 flex items-center gap-2" style={{ background: "var(--bg-secondary)" }}>
              <div className="w-3 h-3 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }} />
              <span className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>{progressLabel}</span>
            </div>
          </div>
        )}

        {error && <div className="mx-4 mt-3 p-3 rounded-lg text-sm" style={{ background: "var(--glow-red)", color: "var(--accent-red)" }}>{error}</div>}

        {/* Empty State */}
        {!report && !loading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-lg">
              <div className="w-20 h-20 mx-auto mb-5 rounded-2xl flex items-center justify-center" style={{ background: "linear-gradient(135deg,#4f8ef7,#8b5cf6)", boxShadow: "0 8px 32px rgba(79,142,247,0.3)" }}>
                <span className="text-3xl">🧠</span>
              </div>
              <h3 className="text-xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>Devमित्र Repo Explorer</h3>
              <p className="text-sm leading-relaxed mb-6" style={{ color: "var(--text-muted)" }}>
                Paste a GitHub URL to get a complete technical analysis: architecture report, tech stack detection, Mermaid diagrams, contributor guide, and interactive Q&A — all from your repository.
              </p>
              <div className="grid grid-cols-4 gap-3 text-center">
                {[
                  { icon: "📊", label: "Deep Report" },
                  { icon: "📐", label: "Diagrams" },
                  { icon: "🤝", label: "Contributor Guide" },
                  { icon: "💬", label: "Repo Q&A" },
                ].map(f => (
                  <div key={f.label} className="glass-card p-3">
                    <span className="text-lg">{f.icon}</span>
                    <p className="text-[10px] mt-1 font-medium" style={{ color: "var(--text-muted)" }}>{f.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Report Content */}
        {report && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Tabs */}
            <div className="flex gap-0.5 px-4 pt-2 overflow-x-auto" style={{ borderBottom: "1px solid var(--border)" }}>
              {TABS.map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className="px-3 py-2 text-[11px] font-medium rounded-t-lg transition-all flex items-center gap-1.5 whitespace-nowrap"
                  style={{
                    color: tab === t ? "var(--accent-blue)" : "var(--text-muted)",
                    background: tab === t ? "var(--bg-elevated)" : "transparent",
                    borderBottom: tab === t ? "2px solid var(--accent-blue)" : "2px solid transparent",
                  }}>
                  <span className="text-[10px]">{TAB_ICONS[t]}</span>{t}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-4">
              <AnimatePresence mode="wait">
                <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
                  {tab === "Overview" && r && <OverviewTab r={r} report={report} />}
                  {tab === "Architecture" && r && <ArchTab r={r} dg={dg} />}
                  {tab === "Insights" && r && <InsightsTab r={r} />}
                  {tab === "Contributor" && r && <ContributorTab r={r} dg={dg} />}
                  {tab === "Files" && st && <FilesTab st={st} contents={report.file_contents} />}
                  {tab === "Q&A" && <QATab qaHistory={qaHistory} question={question} setQuestion={setQuestion} askQuestion={askQuestion} qaLoading={qaLoading} qaEndRef={qaEndRef} />}
                  {tab === "Diagrams" && dg && <DiagramsTab dg={dg} />}
                  {tab === "History" && <HistoryTab history={history} loadReport={loadReport} deleteItem={deleteItem} currentId={report?.id} />}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
