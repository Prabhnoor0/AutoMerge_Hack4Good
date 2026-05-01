"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Zap, Play, Target, Shield, FileCode, CheckCircle2, Terminal, AlertTriangle, AlertCircle, Info, Bug, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { useDevmitra } from "@/store/DevmitraContext";

const LANGUAGES = [
  { value: "auto", label: "Auto-detect" },
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "java", label: "Java" },
];

const MODES = [
  { id: "debug", label: "Debug & Explain", desc: "Find issues and explain them" },
  { id: "fix", label: "Generate Fix", desc: "Create a patch for the issues" },
  { id: "validate", label: "Validate", desc: "Run checks on the fixed code" },
  { id: "refactor", label: "Refactor", desc: "Suggest cleaner ways to write this" },
  { id: "quality", label: "Quality Checks", desc: "Check performance & best practices" },
];

export default function StudioPage() {
  const [code, setCode] = useState("");
  const [logs, setLogs] = useState("");
  const [language, setLanguage] = useState("auto");
  const [filename, setFilename] = useState("");
  const [selectedModes, setSelectedModes] = useState<string[]>(["debug", "fix"]);
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const { setContext } = useDevmitra();

  useEffect(() => {
    setContext({ code, logs, language, filename });
  }, [code, logs, language, filename, setContext]);

  const toggleMode = (modeId: string) => {
    setSelectedModes(prev => 
      prev.includes(modeId) ? prev.filter(m => m !== modeId) : [...prev, modeId]
    );
  };

  const handleAnalyze = async () => {
    if (!code.trim()) {
      setError("Please provide some code to analyze");
      return;
    }
    
    setError(null);
    setLoading(true);
    setResult(null);

    try {
      const res = await api.studioSubmit({
        code,
        logs,
        language,
        filename,
        modes: selectedModes
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to analyze code");
    } finally {
      setLoading(false);
    }
  };

  const handleDemo = async (type: string) => {
    setError(null);
    setLoading(true);
    setResult(null);

    try {
      const res = await api.studioDemo(type, selectedModes);
      setCode(res.sample_code);
      setLogs(res.sample_logs || "");
      setFilename(res.sample_filename || "");
      // Fetch the full result using the job ID from demo
      const fullRes = await api.studioGetResult(res.job_id);
      setResult(fullRes);
    } catch (err: any) {
      setError(err.message || "Demo failed");
    } finally {
      setLoading(false);
    }
  };

  const filteredIssues = useMemo(() => {
    if (!result?.issues) return [];
    if (severityFilter === "all") return result.issues;
    return result.issues.filter((i: any) => i.severity === severityFilter);
  }, [result, severityFilter]);

  const severityCounts = useMemo(() => {
    if (!result?.issues) return { error: 0, warning: 0, bug: 0, security: 0, info: 0 };
    return result.issues.reduce((acc: any, curr: any) => {
      acc[curr.severity] = (acc[curr.severity] || 0) + 1;
      return acc;
    }, { error: 0, warning: 0, bug: 0, security: 0, info: 0 });
  }, [result]);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "error": return <AlertCircle size={14} />;
      case "warning": return <AlertTriangle size={14} />;
      case "bug": return <Bug size={14} />;
      case "security": return <ShieldAlert size={14} />;
      default: return <Info size={14} />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "error": return "var(--accent-red)";
      case "warning": return "var(--accent-amber)";
      case "bug": return "var(--accent-orange)";
      case "security": return "var(--accent-purple)";
      default: return "var(--accent-blue)";
    }
  };

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-primary)" }}>
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Input Panel */}
        <div className="w-1/2 flex flex-col border-r border-[var(--border)] overflow-y-auto p-6 space-y-6">
          <div>
            <h1 className="text-2xl font-bold mb-2 text-[var(--text-primary)]">Code Debug Studio</h1>
            <p className="text-sm text-[var(--text-muted)]">Paste code and logs to get AI-powered debugging, fixes, and refactoring suggestions.</p>
          </div>

          {error && (
            <div className="p-3 bg-[var(--glow-red)] text-[var(--accent-red)] rounded-xl border border-red-500/20 text-sm">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-[var(--text-secondary)] block mb-1.5">Language</label>
                <select 
                  value={language} onChange={e => setLanguage(e.target.value)}
                  className="w-full px-3 py-2 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg text-sm outline-none"
                >
                  {LANGUAGES.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--text-secondary)] block mb-1.5">Filename (optional)</label>
                <input 
                  type="text" value={filename} onChange={e => setFilename(e.target.value)} placeholder="e.g. main.py"
                  className="w-full px-3 py-2 bg-[var(--bg-card)] border border-[var(--border)] rounded-lg text-sm outline-none"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] block mb-1.5">Source Code</label>
              <textarea 
                value={code} onChange={e => setCode(e.target.value)}
                placeholder="Paste your broken code here..."
                className="w-full h-64 p-3 font-mono text-sm bg-[var(--bg-card)] border border-[var(--border)] rounded-xl outline-none resize-y"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] block mb-1.5">Error Logs (optional)</label>
              <textarea 
                value={logs} onChange={e => setLogs(e.target.value)}
                placeholder="Paste stack traces or error logs..."
                className="w-full h-32 p-3 font-mono text-sm bg-[var(--bg-card)] border border-[var(--border)] rounded-xl outline-none resize-y"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] block mb-2">Analysis Modes</label>
              <div className="grid grid-cols-2 gap-2">
                {MODES.map(m => (
                  <label key={m.id} className="flex items-start gap-2 p-3 border border-[var(--border)] rounded-xl cursor-pointer hover:bg-[var(--bg-hover)] transition-colors">
                    <input 
                      type="checkbox" checked={selectedModes.includes(m.id)}
                      onChange={() => toggleMode(m.id)}
                      className="mt-0.5"
                    />
                    <div>
                      <div className="text-sm font-medium text-[var(--text-primary)]">{m.label}</div>
                      <div className="text-[10px] text-[var(--text-muted)]">{m.desc}</div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button 
                onClick={handleAnalyze} disabled={loading}
                className="flex-1 flex items-center justify-center gap-2 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl font-semibold opacity-90 hover:opacity-100 disabled:opacity-50"
              >
                {loading ? <Loader2 className="animate-spin" size={16} /> : <Zap size={16} />}
                {loading ? "Analyzing..." : "Analyze Code"}
              </button>
              <button 
                onClick={() => handleDemo("python_buggy")} disabled={loading}
                className="px-4 py-3 bg-[var(--bg-card)] border border-[var(--border)] rounded-xl font-semibold text-[var(--text-secondary)] hover:text-white transition-colors"
              >
                Try Demo
              </button>
            </div>
          </div>
        </div>

        {/* Right: Results Panel */}
        <div className="w-1/2 bg-[var(--bg-secondary)] overflow-y-auto p-6">
          {!result && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-[var(--text-muted)] space-y-4">
              <Terminal size={48} className="opacity-20" />
              <p>Submit code to see analysis results</p>
            </div>
          )}

          {loading && (
            <div className="h-full flex flex-col items-center justify-center text-[var(--accent-blue)] space-y-4">
              <Loader2 size={48} className="animate-spin opacity-50" />
              <p className="text-sm font-medium animate-pulse">AI is debugging your code...</p>
            </div>
          )}

          {result && !loading && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="p-5 bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-lg">
                <div className="flex items-center gap-3 mb-4">
                  <Target className="text-[var(--accent-blue)]" size={20} />
                  <h2 className="text-lg font-bold text-[var(--text-primary)]">Analysis Summary</h2>
                  <div className="ml-auto flex items-center gap-2 text-xs">
                    <span className="px-2 py-1 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-md font-medium text-[var(--text-muted)]">
                      {result.validation?.re_parse_backend || result.issues?.[0]?.backend_name || result.issues?.[0]?.parser_name || "Analyzer"}
                    </span>
                    <span className="px-2 py-1 bg-[var(--bg-elevated)] rounded-md font-medium text-[var(--text-muted)] uppercase">
                      {result.language}
                    </span>
                    <span className="px-2 py-1 bg-[var(--glow-blue)] text-[var(--accent-blue)] rounded-md font-bold flex items-center gap-1">
                      {(result.confidence * 100).toFixed(0)}% Confidence
                    </span>
                  </div>
                </div>
                <div className="p-4 bg-[var(--bg-elevated)] rounded-xl text-sm text-[var(--text-primary)] border border-[var(--border-subtle)]">
                  {result.root_cause}
                </div>
              </div>

              {/* Issues List */}
              {result.issues && result.issues.length > 0 && (
                <div className="p-5 bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <AlertTriangle className="text-[var(--accent-amber)]" size={20} />
                      <h2 className="text-lg font-bold text-[var(--text-primary)]">Issues Detected</h2>
                    </div>
                    
                    {/* Severity Filters */}
                    <div className="flex gap-2">
                      <button 
                        onClick={() => setSeverityFilter("all")}
                        className={`px-3 py-1 text-xs font-medium rounded-lg border transition-colors ${severityFilter === "all" ? 'bg-[var(--bg-hover)] border-[var(--border)] text-[var(--text-primary)]' : 'bg-transparent border-transparent text-[var(--text-muted)] hover:bg-[var(--bg-elevated)]'}`}
                      >
                        All ({result.issues.length})
                      </button>
                      {['error', 'security', 'bug', 'warning'].map(sev => severityCounts[sev] > 0 && (
                        <button
                          key={sev}
                          onClick={() => setSeverityFilter(sev)}
                          className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-lg border transition-colors`}
                          style={{
                            borderColor: severityFilter === sev ? getSeverityColor(sev) : 'transparent',
                            backgroundColor: severityFilter === sev ? `${getSeverityColor(sev)}15` : 'transparent',
                            color: severityFilter === sev ? getSeverityColor(sev) : 'var(--text-muted)'
                          }}
                        >
                          {getSeverityIcon(sev)}
                          <span className="capitalize">{sev} ({severityCounts[sev]})</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-4">
                    {filteredIssues.map((issue: any, idx: number) => (
                      <div key={idx} className="p-4 bg-[var(--bg-elevated)] rounded-xl border border-[var(--border-subtle)]">
                        <div className="flex items-start gap-3 mb-2">
                          <div className="mt-0.5" style={{ color: getSeverityColor(issue.severity) }}>
                            {getSeverityIcon(issue.severity)}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-semibold text-sm text-[var(--text-primary)]">{issue.message}</span>
                              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded" style={{ backgroundColor: `${getSeverityColor(issue.severity)}15`, color: getSeverityColor(issue.severity) }}>
                                {issue.severity}
                              </span>
                              {issue.origin && (
                                <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-[var(--bg-primary)] border border-[var(--border-subtle)] text-[var(--text-muted)]">
                                  {issue.origin}
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-[var(--text-secondary)]">Line {issue.line}</div>
                          </div>
                        </div>
                        
                        {issue.explanation && (
                          <div className="text-sm text-[var(--text-secondary)] mb-3 pl-7">
                            {issue.explanation}
                          </div>
                        )}

                        {issue.code_frame && (
                          <div className="ml-7 mb-3">
                            <pre className="p-3 bg-[#0a0b0f] rounded-lg text-xs overflow-x-auto text-gray-300 border border-[var(--border-subtle)] font-mono leading-relaxed">
                              {issue.code_frame}
                            </pre>
                          </div>
                        )}

                        {issue.fix_hint && (
                          <div className="ml-7 text-xs flex items-center gap-2 text-[var(--accent-green)] bg-[var(--glow-green)] p-2 rounded-lg border border-green-500/10">
                            <CheckCircle2 size={14} />
                            <span><strong>Hint:</strong> {issue.fix_hint}</span>
                          </div>
                        )}
                      </div>
                    ))}
                    {filteredIssues.length === 0 && (
                      <div className="text-center p-6 text-[var(--text-muted)] text-sm">
                        No issues matching the selected filter.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Explanation */}
              {result.explanation && (
                <div className="p-5 bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-lg">
                  <div className="flex items-center gap-3 mb-4">
                    <Zap className="text-[var(--accent-amber)]" size={20} />
                    <h2 className="text-lg font-bold text-[var(--text-primary)]">Explanation</h2>
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-[var(--text-secondary)]" dangerouslySetInnerHTML={{__html: result.explanation.replace(/\\n/g, '<br/>')}} />
                </div>
              )}

              {/* Fix */}
              {result.diff_text && (
                <div className="p-5 bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-lg">
                  <div className="flex items-center gap-3 mb-4">
                    <FileCode className="text-[var(--accent-green)]" size={20} />
                    <h2 className="text-lg font-bold text-[var(--text-primary)]">Suggested Fix</h2>
                  </div>
                  {result.fix_explanation && (
                    <p className="text-sm mb-4 text-[var(--text-secondary)]">{result.fix_explanation}</p>
                  )}
                  <pre className="p-4 bg-[#0a0b0f] rounded-xl text-xs overflow-x-auto text-gray-300 border border-[var(--border-subtle)] font-mono leading-relaxed">
                    {result.diff_text}
                  </pre>
                </div>
              )}

              {/* Refactor */}
              {result.refactor_suggestions && result.refactor_suggestions.length > 0 && (
                <div className="p-5 bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-lg">
                  <div className="flex items-center gap-3 mb-4">
                    <Zap className="text-[var(--accent-purple)]" size={20} />
                    <h2 className="text-lg font-bold text-[var(--text-primary)]">Refactor Suggestions</h2>
                  </div>
                  <div className="space-y-3">
                    {result.refactor_suggestions.map((s: any, i: number) => (
                      <div key={i} className="p-3 bg-[var(--bg-elevated)] rounded-xl border border-[var(--border-subtle)]">
                        <p className="text-sm text-[var(--text-primary)] font-medium mb-1">{s.suggestion}</p>
                        <p className="text-xs text-[var(--text-muted)] mb-2">Line {s.line}: <code className="bg-black/30 px-1 rounded">{s.source_line}</code></p>
                        <p className="text-xs text-[var(--accent-purple)] font-mono">Example: {s.example}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Validation */}
              {result.validation && (
                <div className="p-5 bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl shadow-lg">
                  <div className="flex items-center gap-3 mb-4">
                    <Shield className={result.validation.status === "passed" ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"} size={20} />
                    <h2 className="text-lg font-bold text-[var(--text-primary)]">Validation Engine</h2>
                    <div className="ml-auto flex items-center gap-3">
                      {result.validation.re_parse_backend && (
                        <span className="px-2 py-1 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-md font-medium text-[var(--text-muted)] text-xs">
                          {result.validation.re_parse_backend}
                        </span>
                      )}
                      <span className="text-xs text-[var(--text-muted)] font-medium">
                        {result.validation.duration_seconds.toFixed(2)}s
                      </span>
                    </div>
                  </div>
                  <pre className="p-4 bg-[#0a0b0f] rounded-xl text-xs overflow-x-auto text-[var(--text-secondary)] border border-[var(--border-subtle)] font-mono leading-relaxed mb-4">
                    {result.validation.stdout}
                  </pre>
                  
                  {result.validation.status !== "passed" && result.validation.remaining_issues?.length > 0 && (
                    <div className="space-y-3 mt-4">
                      <h3 className="text-sm font-semibold text-[var(--text-primary)]">Remaining Issues ({result.validation.remaining_issues.length})</h3>
                      {result.validation.remaining_issues.map((iss: any, idx: number) => (
                        <div key={idx} className="p-3 bg-[var(--bg-elevated)] rounded-xl border border-[var(--border-subtle)] flex items-start gap-3">
                          <AlertCircle size={14} className="mt-0.5" style={{ color: getSeverityColor(iss.severity) }} />
                          <div>
                            <p className="text-sm text-[var(--text-primary)] font-medium">{iss.message}</p>
                            <p className="text-xs text-[var(--text-muted)]">Line {iss.line}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

            </div>
          )}
        </div>
      </div>
    </div>
  );
}
