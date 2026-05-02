"use client";
import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "@/lib/api";
import type { DeployAnalysis, DeployRun, DeployPlatform, DeploySimCheck } from "@/lib/types";

// ─── Helpers ─────────────────────────────────────────────
const CK = ({ s }: { s: string }) => {
  const c = s === "pass" ? "var(--accent-green)" : s === "fail" ? "var(--accent-red)" : s === "warn" ? "var(--accent-amber)" : "var(--accent-blue)";
  const i = s === "pass" ? "✓" : s === "fail" ? "✗" : s === "warn" ? "!" : "i";
  return <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0" style={{ background: `${c}22`, color: c }}>{i}</span>;
};

const Score = ({ v, label, size = 72 }: { v: number; label: string; size?: number }) => {
  const c = v >= 70 ? "var(--accent-green)" : v >= 40 ? "var(--accent-amber)" : "var(--accent-red)";
  const r = (size - 8) / 2, circ = 2 * Math.PI * r, off = circ * (1 - v / 100);
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size}><circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--bg-elevated)" strokeWidth={4} />
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={c} strokeWidth={4} strokeDasharray={circ} strokeDashoffset={off} strokeLinecap="round" style={{ transform: "rotate(-90deg)", transformOrigin: "center", transition: "stroke-dashoffset 1s ease" }} />
      <text x="50%" y="50%" textAnchor="middle" dy="0.35em" fill={c} fontSize={size/4} fontWeight="bold">{v}</text></svg>
      <span className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>{label}</span>
    </div>
  );
};

// ─── Main Page ───────────────────────────────────────────
export default function DeployPage() {
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [platformToken, setPlatformToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"input" | "analysis" | "preview" | "deploying" | "result">("input");
  const [progress, setProgress] = useState("");
  const [analysis, setAnalysis] = useState<DeployAnalysis | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState("");
  const [envVars, setEnvVars] = useState<Record<string, string>>({});
  const [deployResult, setDeployResult] = useState<DeployRun | null>(null);
  const [runs, setRuns] = useState<DeployRun[]>([]);
  const [error, setError] = useState("");

  useEffect(() => { loadRuns(); }, []);

  const loadRuns = async () => { try { const r = await api.deployRuns(); setRuns(r.data || []); } catch {} };

  const analyze = async () => {
    if (!url.trim()) return;
    setLoading(true); setError(""); setProgress("Analyzing repository...");
    try {
      const r = await api.deployPreview(url.trim(), "", token.trim());
      const d = r.data as DeployAnalysis;
      setAnalysis(d);
      if (d.classification?.recommended_platforms?.[0]) setSelectedPlatform(d.classification.recommended_platforms[0].id);
      // Pre-fill env vars
      const vars: Record<string, string> = {};
      (d.env_scan?.required_vars || []).filter((v: any) => v.is_secret).forEach((v: any) => { vars[v.name] = ""; });
      setEnvVars(vars);
      setStep("analysis");
    } catch (e: any) { setError(e.message || "Analysis failed"); }
    setLoading(false); setProgress("");
  };

  const deploy = async () => {
    if (!selectedPlatform || !analysis) return;
    setStep("deploying"); setLoading(true); setProgress("Deploying...");
    try {
      const r = await api.deployStart({ repo_url: url.trim(), platform_id: selectedPlatform, token: token.trim(), platform_token: platformToken.trim(), env_vars: envVars });
      setDeployResult(r.data); setStep("result"); loadRuns();
    } catch (e: any) { setError(e.message || "Deploy failed"); setStep("analysis"); }
    setLoading(false); setProgress("");
  };

  const loadRun = async (id: string) => {
    try { const r = await api.deployGetRun(id); setDeployResult(r.data); setStep("result"); } catch {}
  };

  const reset = () => { setStep("input"); setAnalysis(null); setDeployResult(null); setError(""); setSelectedPlatform(""); };

  const cl = analysis?.classification;
  const sim = analysis?.simulation;
  const env = analysis?.env_scan;

  return (
    <div className="flex h-[calc(100vh-64px)]" style={{ background: "var(--bg-primary)" }}>
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r flex flex-col" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
        <div className="p-4 border-b" style={{ borderColor: "var(--border)" }}>
          <h2 className="text-sm font-bold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
            <span className="w-7 h-7 rounded-lg flex items-center justify-center text-xs" style={{ background: "linear-gradient(135deg,#f97316,#ef4444)", color: "white" }}>🚀</span>
            AutoDeploy
          </h2>
          <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>One-Click Deployment</p>
        </div>
        <div className="flex-1 overflow-auto p-3 space-y-1">
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>Recent Deploys</p>
          {runs.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No deployments yet</p>}
          {runs.map(r => (
            <div key={r.id} onClick={() => loadRun(r.id)} className="p-2.5 rounded-lg cursor-pointer transition-all group hover:opacity-90" style={{ background: deployResult?.id === r.id ? "var(--bg-elevated)" : "transparent" }}>
              <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>{r.repo_name}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: r.status === "deployed" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)", color: r.status === "deployed" ? "var(--accent-green)" : "var(--accent-red)" }}>{r.status}</span>
                <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{r.platform}</span>
              </div>
            </div>
          ))}
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Input Bar */}
        <div className="p-4 border-b flex gap-3 items-end" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
          <div className="flex-1">
            <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--text-muted)" }}>GitHub Repository URL</label>
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/owner/repo" onKeyDown={e => e.key === "Enter" && analyze()}
              className="w-full px-3 py-2 rounded-lg text-sm border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
          </div>
          <div className="w-36">
            <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--text-muted)" }}>GitHub Token</label>
            <input value={token} onChange={e => setToken(e.target.value)} placeholder="ghp_..." type="password"
              className="w-full px-3 py-2 rounded-lg text-sm border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
          </div>
          <button onClick={step === "input" ? analyze : reset} disabled={loading}
            className="px-5 py-2 rounded-lg text-sm font-semibold transition-all" style={{ background: step === "input" ? "linear-gradient(135deg,#f97316,#ef4444)" : "var(--bg-elevated)", color: "white", opacity: loading ? 0.7 : 1 }}>
            {loading ? "..." : step === "input" ? "🚀 Analyze" : "← New"}
          </button>
        </div>

        {loading && <div className="px-4 py-2 flex items-center gap-2" style={{ background: "var(--bg-secondary)" }}>
          <div className="w-3 h-3 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }} />
          <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>{progress}</span>
        </div>}

        {error && <div className="mx-4 mt-3 p-3 rounded-lg text-sm" style={{ background: "rgba(239,68,68,0.1)", color: "var(--accent-red)" }}>{error}</div>}

        <div className="flex-1 overflow-auto p-4">
          <AnimatePresence mode="wait">
            {/* ─── Empty State ─── */}
            {step === "input" && !loading && (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-center h-full">
                <div className="text-center max-w-lg">
                  <div className="w-20 h-20 mx-auto mb-5 rounded-2xl flex items-center justify-center" style={{ background: "linear-gradient(135deg,#f97316,#ef4444)", boxShadow: "0 8px 32px rgba(249,115,22,0.3)" }}>
                    <span className="text-3xl">🚀</span>
                  </div>
                  <h3 className="text-xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>AutoDeploy</h3>
                  <p className="text-sm leading-relaxed mb-6" style={{ color: "var(--text-muted)" }}>Paste a GitHub URL to analyze, simulate, and deploy your project to the best free hosting platform — Vercel, Render, Hugging Face, Supabase, and more.</p>
                  <div className="grid grid-cols-4 gap-3">
                    {[{ i: "▲", l: "Vercel" }, { i: "◉", l: "Render" }, { i: "🤗", l: "HuggingFace" }, { i: "⚡", l: "Supabase" }].map(p => (
                      <div key={p.l} className="glass-card p-3 text-center"><span className="text-lg">{p.i}</span><p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>{p.l}</p></div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* ─── Analysis + Preview ─── */}
            {(step === "analysis" || step === "preview") && analysis && cl && (
              <motion.div key="analysis" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4 max-w-4xl mx-auto">
                {/* Classification Hero */}
                <div className="glass-card p-5">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "linear-gradient(135deg,#f97316,#ef4444)" }}>
                      <span className="text-xl">{cl.project_type === "frontend" ? "🖥️" : cl.project_type === "backend" ? "⚙️" : cl.project_type === "ml" ? "🧠" : cl.project_type === "fullstack" ? "📦" : "📄"}</span>
                    </div>
                    <div className="flex-1">
                      <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{analysis.repo_name}</h2>
                      <p className="text-xs" style={{ color: "var(--text-muted)" }}>{analysis.owner}/{analysis.repo_name}</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold" style={{ background: "rgba(79,142,247,0.15)", color: "var(--accent-blue)" }}>{cl.project_type.toUpperCase()}</span>
                        {cl.frontend_type && <span className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(139,92,246,0.15)", color: "var(--accent-purple)" }}>{cl.frontend_type}</span>}
                        {cl.backend_type && <span className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(34,197,94,0.15)", color: "var(--accent-green)" }}>{cl.backend_type}</span>}
                        {cl.ml_type && <span className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(245,158,11,0.15)", color: "var(--accent-amber)" }}>{cl.ml_type}</span>}
                        {cl.database_type && <span className="px-2 py-0.5 rounded-full text-[10px]" style={{ background: "rgba(6,182,212,0.15)", color: "var(--accent-cyan)" }}>{cl.database_type}</span>}
                      </div>
                    </div>
                    {sim && <Score v={sim.readiness_score} label="Readiness" size={80} />}
                  </div>
                </div>

                {/* Reasoning */}
                <div className="glass-card p-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-blue)" }}>Detection Reasoning</h4>
                  {cl.reasoning.map((r, i) => <p key={i} className="text-xs py-0.5" style={{ color: "var(--text-secondary)" }}>• {r}</p>)}
                  {cl.warnings.map((w, i) => <p key={i} className="text-xs py-0.5" style={{ color: "var(--accent-amber)" }}>⚠️ {w}</p>)}
                  {(analysis.failure_warnings || []).map((w, i) => <p key={i} className="text-xs py-0.5" style={{ color: "var(--accent-red)" }}>{w}</p>)}
                </div>

                {/* Simulation Checks */}
                {sim && (
                  <div className="glass-card p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--accent-cyan)" }}>Deployment Readiness Checks</h4>
                    <div className="space-y-2">
                      {sim.checks.map((c: DeploySimCheck, i: number) => (
                        <div key={i} className="flex items-center gap-2"><CK s={c.status} /><span className="text-xs font-medium w-36" style={{ color: "var(--text-primary)" }}>{c.name}</span><span className="text-xs flex-1" style={{ color: "var(--text-muted)" }}>{c.detail}</span></div>
                      ))}
                    </div>
                    {sim.issues.length > 0 && <div className="mt-3 p-2 rounded-lg" style={{ background: "rgba(239,68,68,0.08)" }}>{sim.issues.map((s, i) => <p key={i} className="text-xs" style={{ color: "var(--accent-red)" }}>✗ {s}</p>)}</div>}
                  </div>
                )}

                {/* Platform Selector */}
                <div className="glass-card p-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--accent-purple)" }}>Select Platform</h4>
                  <div className="grid grid-cols-3 gap-3">
                    {(cl.recommended_platforms || []).map((p: DeployPlatform) => (
                      <button key={p.id} onClick={() => setSelectedPlatform(p.id)}
                        className="p-3 rounded-xl border-2 text-left transition-all" style={{ borderColor: selectedPlatform === p.id ? "var(--accent-blue)" : "var(--border)", background: selectedPlatform === p.id ? "rgba(79,142,247,0.08)" : "var(--bg-elevated)" }}>
                        <div className="flex items-center gap-2"><span className="text-lg">{p.icon}</span><span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{p.name}</span></div>
                        {p.match && <div className="w-full h-1 rounded-full mt-2" style={{ background: "var(--bg-card)" }}><div className="h-full rounded-full" style={{ width: `${p.match}%`, background: "var(--accent-blue)" }} /></div>}
                        <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>{p.reason}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Env Vars + Platform Token */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="glass-card p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--accent-amber)" }}>Environment Variables</h4>
                    {env && env.required_vars.filter((v: any) => v.is_secret).length > 0 ? (
                      <div className="space-y-2">
                        {env.required_vars.filter((v: any) => v.is_secret).map((v: any) => (
                          <div key={v.name}>
                            <label className="text-[10px] font-mono" style={{ color: "var(--text-muted)" }}>{v.name}</label>
                            <input value={envVars[v.name] || ""} onChange={e => setEnvVars(p => ({ ...p, [v.name]: e.target.value }))} type="password" placeholder={v.purpose}
                              className="w-full px-2 py-1.5 rounded text-xs border mt-0.5" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
                          </div>
                        ))}
                      </div>
                    ) : <p className="text-xs" style={{ color: "var(--text-muted)" }}>No secrets required</p>}
                  </div>
                  <div className="glass-card p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--accent-green)" }}>Platform Token</h4>
                    <p className="text-[10px] mb-2" style={{ color: "var(--text-muted)" }}>API token for {selectedPlatform || "selected platform"}</p>
                    <input value={platformToken} onChange={e => setPlatformToken(e.target.value)} type="password" placeholder="Platform API token..."
                      className="w-full px-2 py-1.5 rounded text-xs border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
                    {env && env.recommendations.length > 0 && (
                      <div className="mt-3 space-y-1">{env.recommendations.slice(0, 3).map((r, i) => <p key={i} className="text-[10px]" style={{ color: "var(--accent-amber)" }}>{r}</p>)}</div>
                    )}
                  </div>
                </div>

                {/* Deploy Button */}
                <button onClick={deploy} disabled={!selectedPlatform} className="w-full py-3 rounded-xl text-sm font-bold transition-all"
                  style={{ background: selectedPlatform ? "linear-gradient(135deg,#f97316,#ef4444)" : "var(--bg-elevated)", color: "white", opacity: selectedPlatform ? 1 : 0.5 }}>
                  🚀 Deploy to {selectedPlatform ? cl.recommended_platforms.find((p: any) => p.id === selectedPlatform)?.name || selectedPlatform : "..."}
                </button>
              </motion.div>
            )}

            {/* ─── Deploying ─── */}
            {step === "deploying" && (
              <motion.div key="deploying" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full border-4 border-t-transparent animate-spin" style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }} />
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Deploying to {selectedPlatform}...</p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>This may take a moment</p>
                </div>
              </motion.div>
            )}

            {/* ─── Result ─── */}
            {step === "result" && deployResult && (
              <motion.div key="result" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4 max-w-3xl mx-auto">
                <div className="glass-card p-6 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center" style={{ background: deployResult.status === "deployed" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)" }}>
                    <span className="text-3xl">{deployResult.status === "deployed" ? "✓" : "✗"}</span>
                  </div>
                  <h3 className="text-xl font-bold mb-1" style={{ color: deployResult.status === "deployed" ? "var(--accent-green)" : "var(--accent-red)" }}>
                    {deployResult.status === "deployed" ? "Deployed Successfully!" : "Deployment Failed"}
                  </h3>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{deployResult.repo_name} → {deployResult.platform}</p>
                  {deployResult.deploy_url && (
                    <a href={deployResult.deploy_url} target="_blank" rel="noopener noreferrer"
                      className="inline-block mt-3 px-4 py-2 rounded-lg text-sm font-semibold" style={{ background: "var(--accent-blue)", color: "white" }}>
                      🌐 {deployResult.deploy_url}
                    </a>
                  )}
                  {deployResult.error && <p className="mt-3 text-sm" style={{ color: "var(--accent-red)" }}>{deployResult.error}</p>}
                </div>

                {/* Logs */}
                <div className="glass-card p-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--accent-blue)" }}>Deployment Logs</h4>
                  <div className="p-3 rounded-lg font-mono text-xs space-y-1" style={{ background: "var(--bg-primary)" }}>
                    {(deployResult.logs || []).map((l, i) => (
                      <p key={i} style={{ color: l.startsWith("✓") ? "var(--accent-green)" : l.startsWith("✗") ? "var(--accent-red)" : "var(--text-secondary)" }}>{l}</p>
                    ))}
                  </div>
                </div>

                <div className="flex gap-3">
                  <button onClick={reset} className="flex-1 py-2 rounded-lg text-sm font-medium border" style={{ borderColor: "var(--border)", color: "var(--text-secondary)" }}>Deploy Another</button>
                  {deployResult.status === "failed" && (
                    <button onClick={() => { setStep("analysis"); setError(""); }} className="flex-1 py-2 rounded-lg text-sm font-medium" style={{ background: "var(--accent-amber)", color: "white" }}>Retry</button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
