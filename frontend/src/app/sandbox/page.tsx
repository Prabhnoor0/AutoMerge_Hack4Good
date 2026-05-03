"use client";
import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Lock, Zap, ClipboardList, Play, FlaskConical, Settings, Trash2, CheckCircle2, XCircle, AlertTriangle, Clock, Loader2, MoreHorizontal } from "lucide-react";
import { api } from "@/lib/api";

/* ─── Helpers ─────────────────────────────────────── */
const STATUS_COLORS: Record<string, string> = {
  success: "#22c55e", failure: "#ef4444", error: "#f59e0b",
  timeout: "#f97316", running: "#3b82f6", pending: "#6b7280",
};
const STATUS_ICON: Record<string, React.ElementType> = {
  success: CheckCircle2, failure: XCircle, error: AlertTriangle, timeout: Clock, running: Loader2, pending: MoreHorizontal,
};

const TEMPLATES: Record<string, string> = {
  python: `# Python Sandbox\ndef greet(name):\n    return f"Hello, {name}!"\n\nprint(greet("AutoMerge"))`,
  javascript: `// JavaScript Sandbox\nfunction greet(name) {\n  return \`Hello, \${name}!\`;\n}\nconsole.log(greet("AutoMerge"));`,
};

const LANGUAGE_LABELS: Record<string, { label: string; color: string }> = {
  python: { label: "Python", color: "#3b82f6" },
  javascript: { label: "JavaScript", color: "#f59e0b" },
};

/* ─── Main Page ──────────────────────────────────── */
export default function SandboxPage() {
  const [language, setLanguage] = useState("python");
  const [code, setCode] = useState(TEMPLATES.python);
  const [testCode, setTestCode] = useState("");
  const [mode, setMode] = useState<"run" | "test">("run");
  const [timeout, setTimeoutVal] = useState(30);
  const [memoryLimit, setMemoryLimit] = useState("128m");

  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"editor" | "history">("editor");
  const [showConfig, setShowConfig] = useState(false);
  const editorRef = useRef<HTMLTextAreaElement>(null);

  // Load history on mount
  useEffect(() => { loadHistory(); }, []);

  const loadHistory = async () => {
    try {
      const r = await api.sandboxRuns(30);
      setHistory(r.data || []);
    } catch {}
  };

  const handleRun = async () => {
    if (!code.trim() || running) return;
    setRunning(true); setResult(null);
    try {
      const fn = mode === "test" ? api.sandboxTest : api.sandboxRun;
      const r = await fn({
        code,
        language,
        test_code: testCode,
        mode,
        timeout,
        memory_limit: memoryLimit,
        source_feature: "sandbox",
      });
      setResult(r.data);
      loadHistory();
    } catch (e: any) {
      setResult({ status: "error", error_summary: e.message, stdout: "", stderr: "" });
    }
    setRunning(false);
  };

  const handleLangSwitch = (lang: string) => {
    setLanguage(lang);
    if (!code.trim() || code === TEMPLATES[language]) {
      setCode(TEMPLATES[lang] || "");
    }
  };

  const viewHistoryRun = async (runId: string) => {
    try {
      const r = await api.sandboxGetRun(runId);
      setResult(r.data);
      setActiveTab("editor");
    } catch {}
  };

  const deleteRun = async (runId: string) => {
    try {
      await api.sandboxDeleteRun(runId);
      setHistory(h => h.filter(r => r.run_id !== runId));
    } catch {}
  };

  return (
    <div className="flex h-[calc(100vh-64px)]" style={{ background: "var(--bg-primary)" }}>
      {/* ── Sidebar ── */}
      <div className="w-72 flex-shrink-0 border-r flex flex-col" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
        {/* Header */}
        <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center text-white" style={{ background: "linear-gradient(135deg,#06b6d4,#8b5cf6)", boxShadow: "0 4px 16px rgba(6,182,212,0.3)" }}>
              <Lock className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>Sandbox</h1>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Isolated Code Execution</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b" style={{ borderColor: "var(--border)" }}>
          {(["editor", "history"] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} className="flex-1 py-2.5 text-[11px] font-semibold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5" style={{ color: activeTab === tab ? "var(--accent-blue)" : "var(--text-muted)", borderBottom: activeTab === tab ? "2px solid var(--accent-blue)" : "2px solid transparent" }}>
              {tab === "editor" ? <><Zap className="w-3.5 h-3.5" /> Editor</> : <><ClipboardList className="w-3.5 h-3.5" /> History ({history.length})</>}
            </button>
          ))}
        </div>

        {activeTab === "editor" && (
          <div className="flex-1 overflow-auto p-4 space-y-4">
            {/* Language Selector */}
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider block mb-1.5" style={{ color: "var(--text-muted)" }}>Language</label>
              <div className="flex gap-2">
                {Object.entries(LANGUAGE_LABELS).map(([key, { label, color }]) => (
                  <button key={key} onClick={() => handleLangSwitch(key)} className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all" style={{ background: language === key ? `${color}20` : "var(--bg-elevated)", color: language === key ? color : "var(--text-muted)", border: `1px solid ${language === key ? color : "var(--border)"}` }}>
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Mode */}
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider block mb-1.5" style={{ color: "var(--text-muted)" }}>Mode</label>
              <div className="flex gap-2">
                {(["run", "test"] as const).map(m => (
                  <button key={m} onClick={() => setMode(m)} className="flex-1 py-2 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-1.5" style={{ background: mode === m ? "var(--accent-blue)15" : "var(--bg-elevated)", color: mode === m ? "var(--accent-blue)" : "var(--text-muted)", border: `1px solid ${mode === m ? "var(--accent-blue)" : "var(--border)"}` }}>
                    {m === "run" ? <><Play className="w-3.5 h-3.5" /> Run</> : <><FlaskConical className="w-3.5 h-3.5" /> Test</>}
                  </button>
                ))}
              </div>
            </div>

            {/* Config Toggle */}
            <button onClick={() => setShowConfig(!showConfig)} className="w-full flex items-center gap-1.5 text-left text-[10px] font-semibold uppercase tracking-wider py-1" style={{ color: "var(--text-muted)" }}>
              <Settings className="w-3 h-3" /> {showConfig ? "Hide" : "Show"} Config
            </button>

            <AnimatePresence>
              {showConfig && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="space-y-3 overflow-hidden">
                  <div>
                    <label className="text-[10px] block mb-1" style={{ color: "var(--text-muted)" }}>Timeout (s)</label>
                    <input type="number" value={timeout} onChange={e => setTimeoutVal(Number(e.target.value))} min={5} max={120} className="w-full px-3 py-1.5 rounded-lg text-xs border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
                  </div>
                  <div>
                    <label className="text-[10px] block mb-1" style={{ color: "var(--text-muted)" }}>Memory</label>
                    <select value={memoryLimit} onChange={e => setMemoryLimit(e.target.value)} className="w-full px-3 py-1.5 rounded-lg text-xs border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }}>
                      <option value="64m">64 MB</option>
                      <option value="128m">128 MB</option>
                      <option value="256m">256 MB</option>
                      <option value="512m">512 MB</option>
                    </select>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Safety Info */}
            <div className="p-3 rounded-lg" style={{ background: "rgba(6,182,212,0.08)", border: "1px solid rgba(6,182,212,0.15)" }}>
              <p className="text-[10px] font-semibold mb-1 flex items-center gap-1.5" style={{ color: "#06b6d4" }}><Lock className="w-3 h-3" /> Container Isolated</p>
              <p className="text-[10px] leading-relaxed" style={{ color: "var(--text-muted)" }}>
                Code runs in Docker with CPU/memory limits, no network, and read-only filesystem. Containers are destroyed after each run.
              </p>
            </div>
          </div>
        )}

        {activeTab === "history" && (
          <div className="flex-1 overflow-auto p-2 space-y-1">
            {history.length === 0 && (
              <p className="text-center text-xs py-8" style={{ color: "var(--text-muted)" }}>No runs yet</p>
            )}
            {history.map(h => {
              const Icon = STATUS_ICON[h.status] || MoreHorizontal;
              return (
                <button key={h.run_id} onClick={() => viewHistoryRun(h.run_id)} className="w-full text-left p-3 rounded-lg transition-all hover:opacity-80" style={{ background: "var(--bg-elevated)" }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-semibold flex items-center gap-1.5" style={{ color: STATUS_COLORS[h.status] || "#6b7280" }}>
                      <Icon className={`w-3 h-3 ${h.status === "running" ? "animate-spin" : ""}`} /> {h.status}
                    </span>
                    <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>{h.duration_ms}ms</span>
                  </div>
                  <p className="text-[10px] font-mono truncate" style={{ color: "var(--text-muted)" }}>{h.run_id}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: `${LANGUAGE_LABELS[h.language]?.color || "#6b7280"}20`, color: LANGUAGE_LABELS[h.language]?.color || "#6b7280" }}>{h.language}</span>
                    <button onClick={e => { e.stopPropagation(); deleteRun(h.run_id); }} className="ml-auto text-[9px] hover:text-red-400" style={{ color: "var(--text-muted)" }}><Trash2 className="w-3 h-3" /></button>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Main Content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Editor Area */}
        <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
          {/* Code Editor */}
          <div className="flex-1 flex flex-col overflow-hidden border-r" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
              <h3 className="text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5" style={{ color: "var(--accent-blue)" }}>
                {mode === "test" ? <><FlaskConical className="w-3.5 h-3.5" /> Code + Tests</> : <><Play className="w-3.5 h-3.5" /> Code</>}
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-mono px-2 py-0.5 rounded" style={{ background: `${LANGUAGE_LABELS[language]?.color}20`, color: LANGUAGE_LABELS[language]?.color }}>{language}</span>
              </div>
            </div>
            <textarea
              ref={editorRef}
              value={code}
              onChange={e => setCode(e.target.value)}
              className="flex-1 p-4 font-mono text-xs resize-none"
              style={{ background: "var(--bg-primary)", color: "var(--text-primary)", border: "none", outline: "none" }}
              spellCheck={false}
              placeholder="Write your code here..."
              autoFocus
            />
            {mode === "test" && (
              <>
                <div className="px-4 py-1.5 border-t border-b" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
                  <h4 className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--accent-purple)" }}>Test Code</h4>
                </div>
                <textarea
                  value={testCode}
                  onChange={e => setTestCode(e.target.value)}
                  className="p-4 font-mono text-xs resize-none"
                  style={{ background: "var(--bg-primary)", color: "var(--text-primary)", border: "none", outline: "none", minHeight: "120px", maxHeight: "200px" }}
                  spellCheck={false}
                  placeholder="Write test code here..."
                />
              </>
            )}
            {/* Run Button */}
            <div className="p-3 border-t" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
              <button onClick={handleRun} disabled={running || !code.trim()} className="w-full py-2.5 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2" style={{ background: running ? "var(--bg-elevated)" : "linear-gradient(135deg,#06b6d4,#8b5cf6)", color: "white", opacity: (!code.trim() || running) ? 0.5 : 1 }}>
                {running ? <><Loader2 className="w-4 h-4 animate-spin" /> Executing in Container...</> : mode === "test" ? <><FlaskConical className="w-4 h-4" /> Run Tests</> : <><Play className="w-4 h-4" /> Execute Code</>}
              </button>
            </div>
          </div>

          {/* Results Panel */}
          <div className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
            <div className="px-4 py-2 border-b" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
              <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--accent-green)" }}>Output</h3>
            </div>
            <div className="flex-1 overflow-auto p-4 space-y-4">
              {!result && !running && (
                <div className="flex-1 flex items-center justify-center h-full">
                  <div className="text-center space-y-3">
                    <div className="w-16 h-16 mx-auto rounded-2xl flex items-center justify-center text-gray-400" style={{ background: "var(--bg-elevated)" }}>
                      <Lock className="w-8 h-8" />
                    </div>
                    <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Ready to Execute</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>Code will run in an isolated Docker container</p>
                  </div>
                </div>
              )}

              {running && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-center h-32">
                  <div className="text-center space-y-3">
                    <div className="w-12 h-12 mx-auto rounded-full border-4 border-t-transparent animate-spin" style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }} />
                    <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>Running in container...</p>
                  </div>
                </motion.div>
              )}

              {result && !running && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                  {/* Status Banner */}
                  <div className="flex items-center justify-between p-3 rounded-xl" style={{ background: `${STATUS_COLORS[result.status] || "#6b7280"}10`, border: `1px solid ${STATUS_COLORS[result.status] || "#6b7280"}30` }}>
                    <div className="flex items-center gap-3">
                      {(() => { const ResIcon = STATUS_ICON[result.status] || MoreHorizontal; return <ResIcon className={`w-6 h-6 ${result.status === "running" ? "animate-spin" : ""}`} style={{ color: STATUS_COLORS[result.status] }} />; })()}
                      <div>
                        <p className="text-sm font-bold uppercase" style={{ color: STATUS_COLORS[result.status] }}>{result.status}</p>
                        <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>Exit code: {result.exit_code} · {result.duration_ms}ms</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {result.timed_out && <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: "rgba(249,115,22,0.15)", color: "#f97316" }}>TIMEOUT</span>}
                      {result.cleanup_ok && <span className="text-[10px] px-2 py-0.5 rounded-full" style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e" }}>🧹 Cleaned</span>}
                      <span className="text-[9px] font-mono" style={{ color: "var(--text-muted)" }}>{result.run_id}</span>
                    </div>
                  </div>

                  {/* Error Summary */}
                  {result.error_summary && (
                    <div className="p-3 rounded-lg" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.15)" }}>
                      <p className="text-[10px] font-semibold mb-1" style={{ color: "#ef4444" }}>Error</p>
                      <p className="text-xs font-mono" style={{ color: "#ef4444" }}>{result.error_summary}</p>
                    </div>
                  )}

                  {/* Stdout */}
                  {result.stdout && (
                    <div>
                      <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--accent-green)" }}>stdout</h4>
                      <pre className="text-[11px] p-3 rounded-lg font-mono overflow-auto max-h-64 whitespace-pre-wrap" style={{ background: "var(--bg-elevated)", color: "var(--text-primary)" }}>{result.stdout}</pre>
                    </div>
                  )}

                  {/* Stderr */}
                  {result.stderr && (
                    <div>
                      <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--accent-red)" }}>stderr</h4>
                      <pre className="text-[11px] p-3 rounded-lg font-mono overflow-auto max-h-48 whitespace-pre-wrap" style={{ background: "rgba(239,68,68,0.05)", color: "#ef4444" }}>{result.stderr}</pre>
                    </div>
                  )}

                  {/* Test Summary */}
                  {result.test_summary && result.test_summary.total > 0 && (
                    <div className="p-3 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
                      <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-purple)" }}>Test Results</h4>
                      <div className="flex items-center gap-4">
                        <span className="text-xs font-bold" style={{ color: "#22c55e" }}>✓ {result.test_summary.passed} passed</span>
                        <span className="text-xs font-bold" style={{ color: "#ef4444" }}>✗ {result.test_summary.failed} failed</span>
                        {result.test_summary.errors > 0 && <span className="text-xs font-bold" style={{ color: "#f59e0b" }}>⚠ {result.test_summary.errors} errors</span>}
                      </div>
                    </div>
                  )}

                  {/* Resource Summary */}
                  {result.resource_summary && (
                    <div className="p-3 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
                      <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>Container Config</h4>
                      <div className="flex flex-wrap gap-3">
                        {Object.entries(result.resource_summary).map(([k, v]) => (
                          <span key={k} className="text-[10px] font-mono px-2 py-0.5 rounded" style={{ background: "var(--bg-primary)", color: "var(--text-muted)" }}>{k}: {String(v)}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
