"use client";
import { Card, Badge, ScoreRing, StatCard, FileImportanceBar, CopyButton } from "./ReportCards";
import { MermaidDiagram } from "./MermaidDiagram";
import { useState } from "react";

/* ─── Overview Tab ──────────────────────────────────── */
export function OverviewTab({ r, report }: { r: any; report: any }) {
  return (
    <div className="space-y-4">
      {/* Hero */}
      <div className="glass-card p-5">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "linear-gradient(135deg,#4f8ef7,#8b5cf6)" }}>
            <span className="text-xl">📦</span>
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{report.repo_name}</h2>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{report.owner}/{report.repo_name}</p>
            <p className="text-sm mt-2 leading-relaxed" style={{ color: "var(--text-secondary)" }}>{r.what_it_does}</p>
          </div>
          <div className="flex gap-4 flex-shrink-0">
            <ScoreRing score={r.health_score} label="Health" />
            <ScoreRing score={r.architecture_confidence || 50} label="Arch. Confidence" />
          </div>
        </div>
      </div>

      {/* Problem Statement */}
      {r.problem_statement && (
        <Card title="Problem Statement" accent="var(--accent-purple)">
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{r.problem_statement}</p>
        </Card>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-5 gap-3">
        <StatCard label="Files" value={r.total_files} color="var(--accent-blue)" />
        <StatCard label="Modules" value={r.modules?.length || 0} color="var(--accent-purple)" />
        <StatCard label="Routes" value={r.routes?.length || 0} color="var(--accent-green)" />
        <StatCard label="Services" value={r.services?.length || 0} color="var(--accent-cyan)" />
        <StatCard label="Components" value={r.components?.length || 0} color="var(--accent-amber)" />
      </div>

      {/* Tech Stack + Entry Points */}
      <div className="grid grid-cols-2 gap-4">
        <Card title="Tech Stack">
          <div className="space-y-2">
            {[
              { label: "Languages", items: r.tech_stack?.languages, color: "var(--accent-blue)" },
              { label: "Frameworks", items: r.tech_stack?.frameworks, color: "var(--accent-purple)" },
              { label: "Infrastructure", items: r.tech_stack?.infrastructure, color: "var(--accent-green)" },
              { label: "Styling", items: r.tech_stack?.styling, color: "var(--accent-cyan)" },
              { label: "Databases", items: r.tech_stack?.databases, color: "var(--accent-amber)" },
            ].filter(g => g.items?.length).map(g => (
              <div key={g.label}>
                <span className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>{g.label}</span>
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {g.items.map((t: string) => <Badge key={t} text={t} color={g.color!} />)}
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card title="What to Read First" accent="var(--accent-green)">
          {(r.read_first || []).map((f: any, i: number) => (
            <div key={i} className="flex items-center gap-2 py-1">
              <span className="text-[10px] w-4 h-4 rounded flex items-center justify-center font-bold" style={{ background: "var(--glow-blue)", color: "var(--accent-blue)" }}>{i + 1}</span>
              <span className="text-[11px] font-mono truncate" style={{ color: "var(--text-secondary)" }}>{f.path}</span>
            </div>
          ))}
          {!r.read_first?.length && <p className="text-xs" style={{ color: "var(--text-muted)" }}>Start with README.md and entry points</p>}
        </Card>
      </div>

      {/* Execution + Data Flow */}
      <div className="grid grid-cols-2 gap-4">
        <Card title="Execution Flow" collapsible>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{r.execution_flow}</p>
        </Card>
        <Card title="Data Flow" collapsible>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{r.data_flow}</p>
        </Card>
      </div>

      {/* Frontend-Backend Interaction */}
      {r.frontend_backend_interaction && (
        <Card title="Frontend ↔ Backend Interaction" collapsible>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{r.frontend_backend_interaction}</p>
        </Card>
      )}

      {/* Strengths / Risks */}
      <div className="grid grid-cols-2 gap-4">
        <Card title="✅ Strengths" accent="var(--accent-green)">
          {(r.strengths || []).map((s: string, i: number) => <p key={i} className="text-xs py-0.5 leading-relaxed" style={{ color: "var(--text-secondary)" }}>• {s}</p>)}
        </Card>
        <Card title="⚠️ Risk Radar" accent="var(--accent-amber)">
          {(r.risks || []).map((s: string, i: number) => <p key={i} className="text-xs py-0.5 leading-relaxed" style={{ color: "var(--text-secondary)" }}>• {s}</p>)}
        </Card>
      </div>

      {/* Suggested Improvements */}
      <Card title="💡 Suggested Improvements" accent="var(--accent-cyan)" collapsible>
        {(r.suggested_improvements || []).map((s: string, i: number) => (
          <div key={i} className="flex items-start gap-2 py-1">
            <span className="text-[10px] mt-0.5 w-4 h-4 rounded flex items-center justify-center flex-shrink-0" style={{ background: "var(--glow-blue)", color: "var(--accent-cyan)" }}>{i + 1}</span>
            <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{s}</p>
          </div>
        ))}
      </Card>

      {/* Conclusion */}
      {r.conclusion && (
        <Card title="Conclusion" accent="var(--accent-purple)" collapsible>
          <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }} dangerouslySetInnerHTML={{ __html: r.conclusion.replace(/\*\*(.*?)\*\*/g, '<strong style="color:var(--text-primary)">$1</strong>') }} />
        </Card>
      )}

      {r.readme_summary && (
        <Card title="README Summary" collapsible defaultOpen={false}>
          <p className="text-xs whitespace-pre-wrap leading-relaxed" style={{ color: "var(--text-secondary)" }}>{r.readme_summary}</p>
        </Card>
      )}
    </div>
  );
}

/* ─── Architecture Tab ──────────────────────────────── */
export function ArchTab({ r, dg }: { r: any; dg: any }) {
  return (
    <div className="space-y-4">
      <MermaidDiagram code={dg?.architecture || ""} title="Architecture Diagram" />
      <MermaidDiagram code={dg?.request_flow || ""} title="Request Lifecycle" />
      <MermaidDiagram code={dg?.execution_flow || ""} title="Execution Flow" />
      <div className="grid grid-cols-2 gap-4">
        <Card title="Routes" accent="var(--accent-green)">
          {(r.routes || []).map((rt: string) => <p key={rt} className="text-xs font-mono py-0.5" style={{ color: "var(--text-secondary)" }}>{rt}</p>)}
          {!r.routes?.length && <p className="text-xs" style={{ color: "var(--text-muted)" }}>None detected</p>}
        </Card>
        <Card title="Services" accent="var(--accent-purple)">
          {(r.services || []).map((s: string) => <p key={s} className="text-xs font-mono py-0.5" style={{ color: "var(--text-secondary)" }}>{s}</p>)}
          {!r.services?.length && <p className="text-xs" style={{ color: "var(--text-muted)" }}>None detected</p>}
        </Card>
      </div>
    </div>
  );
}

/* ─── Insights Tab ──────────────────────────────────── */
export function InsightsTab({ r }: { r: any }) {
  return (
    <div className="space-y-4">
      {/* Scores */}
      <div className="glass-card p-5 flex items-center justify-center gap-12">
        <ScoreRing score={r.health_score} label="Repo Health" size={80} />
        <ScoreRing score={r.architecture_confidence || 50} label="Architecture Confidence" size={80} />
      </div>

      {/* File Importance Ranking */}
      <Card title="File Importance Ranking">
        {(r.important_files || []).slice(0, 12).map((f: any) => <FileImportanceBar key={f.path} file={f} />)}
      </Card>

      {/* Module Ranking */}
      <Card title="Module Ranking" accent="var(--accent-purple)">
        {(r.module_ranking || []).map((m: any) => (
          <div key={m.module} className="flex items-center gap-2 py-1">
            <span className="text-[11px] font-mono" style={{ color: "var(--accent-purple)" }}>{m.module}/</span>
            <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{m.file_count} files</span>
          </div>
        ))}
      </Card>

      {/* Folder Explanations */}
      <Card title="Folder Guide" accent="var(--accent-cyan)" collapsible>
        {(r.folder_explanations || []).map((f: any) => (
          <div key={f.folder} className="py-1.5 border-b last:border-0" style={{ borderColor: "var(--border-subtle)" }}>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-semibold" style={{ color: "var(--accent-blue)" }}>📁 {f.folder}/</span>
              <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>({f.file_count} files)</span>
            </div>
            <p className="text-[11px] mt-0.5" style={{ color: "var(--text-secondary)" }}>{f.explanation}</p>
          </div>
        ))}
      </Card>

      {/* Important Files Detail */}
      <Card title="Key File Analysis" collapsible defaultOpen={false}>
        {(r.important_files || []).slice(0, 10).map((f: any) => (
          <div key={f.path} className="py-2 border-b last:border-0" style={{ borderColor: "var(--border-subtle)" }}>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-medium" style={{ color: "var(--text-primary)" }}>{f.name}</span>
              <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{f.lines} lines</span>
              <Badge text={`${f.importance}/100`} color={f.importance >= 70 ? "var(--accent-blue)" : "var(--accent-cyan)"} />
            </div>
            <p className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>{f.purpose}</p>
            {f.functions?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {f.functions.slice(0, 5).map((fn: string) => <span key={fn} className="text-[9px] px-1.5 py-0.5 rounded font-mono" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}>{fn}()</span>)}
              </div>
            )}
          </div>
        ))}
      </Card>
    </div>
  );
}

/* ─── Contributor Tab ───────────────────────────────── */
export function ContributorTab({ r, dg }: { r: any; dg: any }) {
  const cg = r.contributor_guide || {};
  return (
    <div className="space-y-4">
      <MermaidDiagram code={dg?.contributor_map || ""} title="Contributor Navigation Map" />

      <Card title="Typical Request Flow" accent="var(--accent-blue)">
        <p className="text-sm font-mono" style={{ color: "var(--text-secondary)" }}>{cg.typical_request_flow || "N/A"}</p>
      </Card>

      <div className="grid grid-cols-2 gap-4">
        <Card title="📖 Start Reading" accent="var(--accent-green)">
          {(cg.start_reading || []).map((f: string) => <p key={f} className="text-xs font-mono py-0.5" style={{ color: "var(--text-secondary)" }}>→ {f}</p>)}
        </Card>
        <Card title="🚪 Entry Points" accent="var(--accent-blue)">
          {(cg.entry_points || []).map((f: string) => <p key={f} className="text-xs font-mono py-0.5" style={{ color: "var(--text-secondary)" }}>📄 {f}</p>)}
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card title="✅ Safe to Edit First" accent="var(--accent-green)">
          {(cg.safe_to_edit_first || []).map((f: string) => <p key={f} className="text-xs font-mono py-0.5" style={{ color: "var(--text-secondary)" }}>{f}</p>)}
          {!cg.safe_to_edit_first?.length && <p className="text-xs" style={{ color: "var(--text-muted)" }}>Analyze a repo to see suggestions</p>}
        </Card>
        <Card title="⛔ Avoid Unless Necessary" accent="var(--accent-red)">
          {(cg.avoid_unless_necessary || []).map((f: string) => <p key={f} className="text-xs font-mono py-0.5" style={{ color: "var(--text-secondary)" }}>{f}</p>)}
        </Card>
      </div>

      <Card title="🎯 Suggested First Contributions" accent="var(--accent-cyan)">
        {(cg.first_contribution_tasks || []).map((t: string, i: number) => (
          <div key={i} className="flex items-start gap-2 py-1">
            <span className="text-[10px] mt-0.5 w-4 h-4 rounded flex items-center justify-center flex-shrink-0 font-bold" style={{ background: "var(--glow-blue)", color: "var(--accent-cyan)" }}>{i + 1}</span>
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{t}</p>
          </div>
        ))}
      </Card>
    </div>
  );
}

/* ─── Files Tab ─────────────────────────────────────── */
export function FilesTab({ st, contents }: { st: any; contents: any }) {
  const [sel, setSel] = useState<string | null>(null);
  const tree = st?.folder_tree || [];
  const dirs = [...new Set(tree.map((f: any) => f.path.split("/")[0]))].sort() as string[];
  return (
    <div className="flex gap-4 h-[calc(100vh-220px)]">
      <div className="w-64 overflow-auto rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}>
        <div className="p-2 border-b" style={{ borderColor: "var(--border)" }}>
          <p className="text-[10px] font-semibold uppercase" style={{ color: "var(--text-muted)" }}>File Tree ({tree.length})</p>
        </div>
        <div className="p-1">
          {dirs.map(d => (
            <div key={d}>
              <p className="text-[10px] font-semibold px-2 py-1" style={{ color: "var(--accent-blue)" }}>📁 {d}/</p>
              {tree.filter((f: any) => f.path.startsWith(d + "/") && f.type === "blob").slice(0, 15).map((f: any) => (
                <button key={f.path} onClick={() => setSel(f.path)}
                  className="w-full text-left px-3 py-1 text-[11px] font-mono truncate rounded transition-colors"
                  style={{ color: sel === f.path ? "var(--accent-blue)" : "var(--text-secondary)", background: sel === f.path ? "var(--bg-hover)" : "transparent" }}>
                  {f.path.split("/").slice(1).join("/")}
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-auto rounded-lg border" style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}>
        {sel && contents?.[sel] ? (
          <div>
            <div className="p-3 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
              <span className="text-xs font-mono font-medium" style={{ color: "var(--text-primary)" }}>{sel}</span>
              <CopyButton text={contents[sel]} />
            </div>
            <pre className="p-3 text-xs font-mono overflow-auto leading-relaxed" style={{ color: "var(--text-secondary)" }}>{contents[sel]}</pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>Select a file to view its contents</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Diagrams Tab ──────────────────────────────────── */
export function DiagramsTab({ dg }: { dg: any }) {
  return (
    <div className="space-y-4">
      {Object.entries(dg || {}).map(([name, code]) => (
        <MermaidDiagram key={name} code={code as string} title={name.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())} />
      ))}
    </div>
  );
}

/* ─── Q&A Tab ───────────────────────────────────────── */
export function QATab({ qaHistory, question, setQuestion, askQuestion, qaLoading, qaEndRef }: any) {
  return (
    <div className="flex flex-col h-[calc(100vh-220px)]">
      <div className="flex-1 overflow-auto space-y-3 mb-3">
        {qaHistory.length === 0 && (
          <div className="text-center py-12">
            <span className="text-3xl">💬</span>
            <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>Ask anything about this repository</p>
            <div className="flex flex-wrap gap-2 justify-center mt-4">
              {["What does this repo do?", "What tech stack is used?", "Where are the routes?", "Explain the architecture"].map(s => (
                <button key={s} onClick={() => { setQuestion(s); }} className="px-3 py-1.5 text-[11px] rounded-full border transition-colors"
                  style={{ borderColor: "var(--border)", color: "var(--text-secondary)", background: "var(--bg-elevated)" }}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {qaHistory.map((qa: any, i: number) => (
          <div key={i} className="space-y-2">
            <div className="flex justify-end"><div className="max-w-[70%] px-3 py-2 rounded-xl text-sm" style={{ background: "var(--accent-blue)", color: "white" }}>{qa.question}</div></div>
            <div className="flex justify-start"><div className="max-w-[80%] px-3 py-2 rounded-xl text-sm glass-card whitespace-pre-wrap leading-relaxed" style={{ color: "var(--text-secondary)" }}>{qa.answer}</div></div>
          </div>
        ))}
        <div ref={qaEndRef} />
      </div>
      <div className="flex gap-2">
        <input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask about this repo..."
          onKeyDown={e => e.key === "Enter" && askQuestion()} disabled={qaLoading}
          className="flex-1 px-3 py-2 rounded-lg text-sm border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
        <button onClick={askQuestion} disabled={qaLoading || !question.trim()}
          className="px-4 py-2 rounded-lg text-sm font-semibold" style={{ background: "linear-gradient(135deg,#4f8ef7,#6366f1)", color: "white", opacity: qaLoading ? 0.6 : 1 }}>
          {qaLoading ? "..." : "Ask"}
        </button>
      </div>
    </div>
  );
}

/* ─── History Tab ───────────────────────────────────── */
export function HistoryTab({ history, loadReport, deleteItem, currentId }: any) {
  return (
    <div className="space-y-2">
      {history.length === 0 && <p className="text-sm" style={{ color: "var(--text-muted)" }}>No history yet</p>}
      {history.map((h: any) => (
        <div key={h.id} onClick={() => loadReport(h.id)}
          className="glass-card p-3 flex items-center gap-3 cursor-pointer card-hover"
          style={{ borderColor: currentId === h.id ? "var(--accent-blue)" : "var(--border)" }}>
          <div className="flex-1">
            <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>{h.owner}/{h.repo_name}</p>
            <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{h.languages} • {h.total_files} files • Score: {h.health_score}</p>
          </div>
          <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{new Date(h.analyzed_at).toLocaleDateString()}</p>
          <button onClick={e => { e.stopPropagation(); deleteItem(h.id); }} className="text-xs px-2 py-1 rounded" style={{ color: "var(--accent-red)" }}>Delete</button>
        </div>
      ))}
    </div>
  );
}
