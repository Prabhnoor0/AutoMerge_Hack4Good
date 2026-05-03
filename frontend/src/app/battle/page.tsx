"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Swords, Hourglass, Lightbulb, PenLine, Send, Zap, ShieldAlert, Trophy, XCircle, Crown, Eye } from "lucide-react";
import { api } from "@/lib/api";
import type { BattleState, BattleParticipant } from "@/lib/types";

/* ─── Tiny helpers ──────────────────────────────────── */
const fmt = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

const Badge = ({ c, children }: { c: string; children: React.ReactNode }) => (
  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider" style={{ background: `${c}22`, color: c }}>{children}</span>
);

const diffColor: Record<string, string> = { easy: "#22c55e", medium: "#f59e0b", hard: "#ef4444" };

/* ─── Main Page ─────────────────────────────────────── */
export default function BattlePage() {
  const [view, setView] = useState<"lobby" | "battle" | "result">("lobby");
  const [name, setName] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [playerId, setPlayerId] = useState("");
  const [state, setState] = useState<BattleState | null>(null);
  const [code, setCode] = useState("");
  const [explanation, setExplanation] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultData, setResultData] = useState<any>(null);
  const [draftDirty, setDraftDirty] = useState(false);
  const pollRef = useRef<any>(null);
  const codeInitializedRef = useRef(false);
  const hasEditedRef = useRef(false);

  /* Safe code setter — tracks user edits */
  const handleCodeChange = useCallback((val: string) => {
    setCode(val);
    hasEditedRef.current = true;
    setDraftDirty(true);
  }, []);

  const resetDraft = useCallback(() => {
    if (state?.challenge?.broken_code) {
      setCode(state.challenge.broken_code);
      hasEditedRef.current = false;
      setDraftDirty(false);
    }
  }, [state]);

  /* polling — NEVER overwrites user draft */
  const poll = useCallback(async (sid: string) => {
    try {
      const r = await api.battleGetState(sid);
      const s = r.data as BattleState;
      setState(s);
      /* Initialize code ONCE when battle starts — never again */
      if (s.status === "running" && !codeInitializedRef.current && !hasEditedRef.current) {
        setCode(s.challenge?.broken_code || "");
        codeInitializedRef.current = true;
      }
      if (s.status === "finished") {
        clearInterval(pollRef.current);
        try { const res = await api.battleGetResult(sid); setResultData(res.data); } catch {}
        setView("result");
      }
    } catch {}
  }, []);  /* no code dependency — stable ref */

  const startPolling = useCallback((sid: string) => {
    clearInterval(pollRef.current);
    poll(sid);
    pollRef.current = setInterval(() => poll(sid), 2000);
  }, [poll]);

  useEffect(() => () => clearInterval(pollRef.current), []);

  /* actions */
  const create = async () => {
    if (!name.trim()) return; setLoading(true); setError("");
    try {
      const r = await api.battleCreate(name.trim());
      const s = r.data; setSessionId(s.id); setPlayerId(s.participants[0].id);
      setRoomCode(s.room_code); setState(s); setView("battle"); startPolling(s.id);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const join = async () => {
    if (!name.trim() || !roomCode.trim()) return; setLoading(true); setError("");
    try {
      const r = await api.battleJoin(roomCode.trim(), name.trim());
      const s = r.data; setSessionId(s.id);
      const me = s.participants.find((p: any) => p.name === name.trim());
      if (me) setPlayerId(me.id);
      setState(s); setView("battle"); startPolling(s.id);
    } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const start = async () => {
    if (!sessionId) return; setLoading(true);
    try { await api.battleStart(sessionId); } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const submit = async () => {
    if (!code.trim()) return; setLoading(true); setError("");
    try { await api.battleSubmit(sessionId, playerId, code, explanation); } catch (e: any) { setError(e.message); }
    setLoading(false);
  };

  const reset = () => {
    clearInterval(pollRef.current); setView("lobby"); setState(null); setResultData(null);
    setSessionId(""); setPlayerId(""); setCode(""); setExplanation(""); setError(""); setRoomCode("");
    codeInitializedRef.current = false; hasEditedRef.current = false; setDraftDirty(false);
  };

  const ch = state?.challenge;
  const me = state?.participants.find(p => p.id === playerId);
  const opponent = state?.participants.find(p => p.id !== playerId);

  return (
    <div className="flex h-[calc(100vh-64px)]" style={{ background: "var(--bg-primary)" }}>
      <AnimatePresence mode="wait">

        {/* ═══════ LOBBY ═══════ */}
        {view === "lobby" && (
          <motion.div key="lobby" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex items-center justify-center p-6">
            <div className="w-full max-w-lg space-y-6">
              {/* Hero */}
              <div className="text-center mb-8">
                <div className="w-20 h-20 mx-auto mb-4 rounded-2xl flex items-center justify-center text-white" style={{ background: "linear-gradient(135deg,#ef4444,#8b5cf6)", boxShadow: "0 8px 32px rgba(239,68,68,0.3)" }}>
                  <Swords className="w-10 h-10" />
                </div>
                <h1 className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>BugFix Arena</h1>
                <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>1v1 Debugging Competitions — Fix bugs faster than your opponent</p>
              </div>

              {/* Name */}
              <div>
                <label className="text-[10px] font-semibold uppercase tracking-wider block mb-1" style={{ color: "var(--text-muted)" }}>Your Name</label>
                <input value={name} onChange={e => setName(e.target.value)} placeholder="Enter your name..." className="w-full px-4 py-2.5 rounded-xl text-sm border" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
              </div>

              {/* Create */}
              <button onClick={create} disabled={loading || !name.trim()} className="w-full py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2" style={{ background: "linear-gradient(135deg,#ef4444,#8b5cf6)", color: "white", opacity: name.trim() ? 1 : 0.5 }}>
                <Swords className="w-4 h-4" /> Create New Battle
              </button>

              {/* Divider */}
              <div className="flex items-center gap-3">
                <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
                <span className="text-[10px] font-bold uppercase" style={{ color: "var(--text-muted)" }}>or join</span>
                <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
              </div>

              {/* Join */}
              <div className="flex gap-2">
                <input value={roomCode} onChange={e => setRoomCode(e.target.value.toUpperCase())} placeholder="ROOM CODE" maxLength={6} className="flex-1 px-4 py-2.5 rounded-xl text-sm border text-center font-mono tracking-[0.3em]" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
                <button onClick={join} disabled={loading || !name.trim() || !roomCode.trim()} className="px-6 py-2.5 rounded-xl text-sm font-semibold" style={{ background: "var(--bg-elevated)", color: "var(--accent-blue)", border: "1px solid var(--border)" }}>
                  Join
                </button>
              </div>

              {error && <p className="text-sm text-center" style={{ color: "var(--accent-red)" }}>{error}</p>}
            </div>
          </motion.div>
        )}

        {/* ═══════ BATTLE ═══════ */}
        {view === "battle" && state && (
          <motion.div key="battle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">

            {/* Top Bar */}
            <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
              <div className="flex items-center gap-3">
                <Swords className="w-6 h-6 text-gray-400" />
                <div>
                  <h2 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{state.title}</h2>
                  <div className="flex items-center gap-2 mt-0.5">
                    <Badge c={diffColor[ch?.difficulty || "medium"] || "#f59e0b"}>{ch?.difficulty}</Badge>
                    <Badge c="#8b5cf6">{ch?.language}</Badge>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded" style={{ background: "var(--bg-elevated)", color: "var(--accent-blue)" }}>Room: {state.room_code}</span>
                  </div>
                </div>
              </div>

              {/* Timer */}
              <div className="text-center">
                {state.status === "running" ? (
                  <div>
                    <p className="text-2xl font-mono font-bold" style={{ color: state.remaining < 60 ? "var(--accent-red)" : "var(--text-primary)" }}>{fmt(state.remaining)}</p>
                    <p className="text-[9px] uppercase" style={{ color: "var(--text-muted)" }}>Remaining</p>
                  </div>
                ) : (
                  <Badge c={state.status === "waiting" ? "#6b7280" : state.status === "ready" ? "#22c55e" : "#f59e0b"}>{state.status}</Badge>
                )}
              </div>

              {/* Players */}
              <div className="flex items-center gap-4">
                {state.participants.map(p => (
                  <div key={p.id} className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white" style={{ background: p.color }}>{p.name[0]}</div>
                    <div>
                      <p className="text-xs font-semibold" style={{ color: p.id === playerId ? "var(--accent-blue)" : "var(--text-primary)" }}>{p.name} {p.id === playerId ? "(You)" : ""}</p>
                      <p className="text-[9px]" style={{ color: p.submitted ? "var(--accent-green)" : "var(--text-muted)" }}>{p.submitted ? "✓ Submitted" : state.status === "running" ? "Coding..." : "Waiting"}</p>
                    </div>
                  </div>
                ))}
                {state.participants.length < 2 && <div className="w-8 h-8 rounded-full border-2 border-dashed flex items-center justify-center text-[10px]" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>?</div>}
              </div>
            </div>

            {/* Waiting / Ready state */}
            {(state.status === "waiting" || state.status === "ready") && (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center space-y-4">
                  <div className="w-16 h-16 mx-auto rounded-full border-4 border-dashed flex items-center justify-center animate-pulse text-purple-400" style={{ borderColor: "var(--accent-purple)" }}>
                    <Hourglass className="w-8 h-8" />
                  </div>
                  <h3 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                    {state.status === "waiting" ? "Waiting for opponent..." : "Ready to battle!"}
                  </h3>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>Share room code: <span className="font-mono font-bold text-sm" style={{ color: "var(--accent-blue)" }}>{state.room_code}</span></p>
                  {me?.is_host && state.status === "ready" && (
                    <button onClick={start} className="px-8 py-3 rounded-xl text-sm font-bold flex items-center justify-center gap-2 mx-auto" style={{ background: "linear-gradient(135deg,#ef4444,#8b5cf6)", color: "white" }}><Swords className="w-4 h-4" /> Start Battle</button>
                  )}
                  {me?.is_host && state.status === "waiting" && (
                    <button onClick={start} className="px-6 py-2 rounded-xl text-xs font-medium" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)", border: "1px solid var(--border)" }}>Start Solo (Practice)</button>
                  )}
                </div>
              </div>
            )}

            {/* Running: Code Editor + Challenge */}
            {state.status === "running" && (
              <div className="flex-1 flex overflow-hidden">
                {/* Left: Challenge Info */}
                <div className="w-80 flex-shrink-0 border-r overflow-auto p-4 space-y-4" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
                  <div>
                    <h3 className="text-sm font-bold mb-1" style={{ color: "var(--text-primary)" }}>Challenge</h3>
                    <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{ch?.description}</p>
                  </div>
                  <div>
                    <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--accent-red)" }}>Error Logs</h4>
                    <pre className="text-[10px] p-3 rounded-lg overflow-auto whitespace-pre-wrap font-mono" style={{ background: "var(--bg-primary)", color: "var(--accent-red)" }}>{ch?.error_logs}</pre>
                  </div>
                  {ch?.hints && ch.hints.length > 0 && (
                    <div>
                      <h4 className="text-[10px] font-semibold uppercase tracking-wider mb-1" style={{ color: "var(--accent-amber)" }}>Hints</h4>
                      {ch.hints.map((h, i) => <p key={i} className="text-[10px] flex items-start gap-1.5" style={{ color: "var(--text-muted)" }}><Lightbulb className="w-3 h-3 flex-shrink-0" /> {h}</p>)}
                    </div>
                  )}
                  {/* Opponent status */}
                  {opponent && (
                    <div className="p-3 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white" style={{ background: opponent.color }}>{opponent.name[0]}</div>
                        <span className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{opponent.name}</span>
                        <span className="ml-auto text-[10px]" style={{ color: opponent.submitted ? "var(--accent-green)" : "var(--accent-amber)" }}>{opponent.submitted ? "✓ Submitted" : "⏳ Coding..."}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right: Editor */}
                <div className="flex-1 flex flex-col overflow-hidden">
                  <div className="flex-1 flex flex-col p-4 gap-3 overflow-hidden">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--accent-blue)" }}>Your Fix</h4>
                        {draftDirty && !me?.submitted && <span className="text-[9px] px-2 py-0.5 rounded-full" style={{ background: "rgba(245,158,11,0.15)", color: "#f59e0b" }}>● unsaved draft</span>}
                      </div>
                      <div className="flex items-center gap-2">
                        {!me?.submitted && draftDirty && (
                          <button onClick={resetDraft} className="text-[10px] px-2 py-1 rounded-lg" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)", border: "1px solid var(--border)" }}>↺ Reset Code</button>
                        )}
                        {me?.submitted && <Badge c="#22c55e">Submitted ✓</Badge>}
                      </div>
                    </div>
                    <textarea value={code} onChange={e => handleCodeChange(e.target.value)} disabled={me?.submitted} className="flex-1 p-3 rounded-lg font-mono text-xs border resize-none" style={{ background: "var(--bg-elevated)", borderColor: draftDirty ? "var(--accent-amber)" : "var(--border)", color: "var(--text-primary)", minHeight: "200px" }} spellCheck={false} autoFocus />
                    <div>
                      <label className="text-[10px] font-semibold uppercase tracking-wider mb-1 block" style={{ color: "var(--accent-purple)" }}>Explanation (optional, +15 pts)</label>
                      <textarea value={explanation} onChange={e => setExplanation(e.target.value)} disabled={me?.submitted} placeholder="Explain the bugs you found and how you fixed them..." rows={3} className="w-full p-3 rounded-lg text-xs border resize-none" style={{ background: "var(--bg-elevated)", borderColor: "var(--border)", color: "var(--text-primary)" }} />
                    </div>
                    <button onClick={submit} disabled={me?.submitted || loading || !code.trim()} className="py-2.5 rounded-xl text-sm font-bold transition-all flex items-center justify-center gap-2" style={{ background: me?.submitted ? "var(--bg-elevated)" : "linear-gradient(135deg,#22c55e,#06b6d4)", color: "white", opacity: (me?.submitted || !code.trim()) ? 0.5 : 1 }}>
                      {me?.submitted ? "✓ Submitted — Waiting for opponent" : !code.trim() ? <><PenLine className="w-4 h-4" /> Write code to submit</> : <><Send className="w-4 h-4" /> Submit Solution</>}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {state.status === "judging" && (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full border-4 border-t-transparent animate-spin" style={{ borderColor: "var(--accent-purple)", borderTopColor: "transparent" }} />
                  <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>Judging submissions...</p>
                </div>
              </div>
            )}

            {error && <p className="px-4 py-2 text-sm" style={{ color: "var(--accent-red)" }}>{error}</p>}
          </motion.div>
        )}

        {/* ═══════ RESULT ═══════ */}
        {view === "result" && state && (
          <motion.div key="result" initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 overflow-auto p-6">
            <div className="max-w-3xl mx-auto space-y-6">
              {/* Winner Banner */}
              {(() => {
                const winner = state.participants.find(p => p.id === state.winner);
                const isMe = state.winner === playerId;
                const noWinner = !state.winner;
                const myScore = me?.score?.total ?? 0;
                const myCorrectness = me?.score?.correctness ?? 0;
                /* Outcome labels */
                let Icon = Zap, title = "Battle Complete", color = "var(--accent-purple)";
                let bgGrad = "linear-gradient(135deg,rgba(107,114,128,0.08),rgba(107,114,128,0.08))";
                if (noWinner) {
                  Icon = ShieldAlert; title = "No Winner — Both Failed"; color = "var(--text-muted)";
                } else if (isMe) {
                  Icon = Trophy; title = "You Won!"; color = "var(--accent-green)";
                  bgGrad = "linear-gradient(135deg,rgba(34,197,94,0.08),rgba(6,182,212,0.08))";
                } else {
                  Icon = XCircle; title = winner ? `${winner.name} Wins — You Lost` : "You Lost";
                  color = "var(--accent-red)";
                  bgGrad = "linear-gradient(135deg,rgba(239,68,68,0.08),rgba(139,92,246,0.08))";
                }
                /* Sub-message based on correctness */
                let sub = state.title;
                if (noWinner) sub = "Neither player met the minimum correctness threshold.";
                else if (isMe && myCorrectness >= 40) sub = "Excellent work — dominant victory!";
                else if (isMe) sub = "Close win — room for improvement.";
                else if (!isMe && myCorrectness < 15) sub = "Your fix was insufficient. Study the bugs and try again.";
                return (
                  <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.2 }} className="glass-card p-8 text-center relative overflow-hidden">
                    <div className="absolute inset-0" style={{ background: bgGrad }} />
                    <div className="relative">
                      <Icon className="w-12 h-12 mx-auto mb-3" style={{ color }} />
                      <h2 className="text-2xl font-bold mb-1" style={{ color }}>{title}</h2>
                      <p className="text-sm" style={{ color: "var(--text-muted)" }}>{sub}</p>
                      {myScore > 0 && <p className="text-xs mt-2 font-mono" style={{ color: "var(--text-muted)" }}>Your score: {myScore}/100</p>}
                    </div>
                  </motion.div>
                );
              })()}

              {/* Score Comparison */}
              <div className="grid grid-cols-2 gap-4">
                {state.participants.map((p, i) => {
                  const isWinner = p.id === state.winner;
                  const sc = p.score;
                  return (
                    <motion.div key={p.id} initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.3 + i * 0.15 }}
                      className="glass-card p-5 relative" style={{ borderColor: isWinner ? "var(--accent-green)" : "var(--border)", borderWidth: isWinner ? "2px" : "1px" }}>
                      {isWinner && <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full flex items-center justify-center text-sm text-white" style={{ background: "var(--accent-green)" }}><Crown className="w-4 h-4" /></div>}
                      <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white" style={{ background: p.color }}>{p.name[0]}</div>
                        <div>
                          <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{p.name} {p.id === playerId ? "(You)" : ""}</p>
                          <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{p.time_taken ? `${p.time_taken}s` : ""}</p>
                        </div>
                        <div className="ml-auto text-right">
                          <p className="text-2xl font-bold" style={{ color: isWinner ? "var(--accent-green)" : "var(--text-primary)" }}>{sc?.total || 0}</p>
                          <p className="text-[9px] uppercase" style={{ color: "var(--text-muted)" }}>points</p>
                        </div>
                      </div>
                      {/* Score bars */}
                      {sc && (
                        <div className="space-y-2">
                          {[{ l: "Correctness", v: sc.correctness, m: 50, c: "#22c55e" }, { l: "Hidden Tests", v: sc.hidden_tests, m: 25, c: "#8b5cf6" }, { l: "Explanation", v: sc.explanation_quality, m: 15, c: "#f59e0b" }, { l: "Speed", v: sc.speed, m: 10, c: "#06b6d4" }].map(b => (
                            <div key={b.l}>
                              <div className="flex justify-between text-[10px] mb-0.5"><span style={{ color: "var(--text-muted)" }}>{b.l}</span><span style={{ color: b.c }}>{b.v}/{b.m}</span></div>
                              <div className="h-1.5 rounded-full" style={{ background: "var(--bg-elevated)" }}><div className="h-full rounded-full transition-all duration-1000" style={{ width: `${(b.v / b.m) * 100}%`, background: b.c }} /></div>
                            </div>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>

              {/* Score Breakdown */}
              {resultData && resultData.participants?.map((p: any) => p.score?.breakdown?.length > 0 && (
                <div key={p.id} className="glass-card p-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: p.color }}>{p.name} — Score Breakdown</h4>
                  {p.score.breakdown.map((b: string, i: number) => <p key={i} className="text-xs py-0.5" style={{ color: "var(--text-secondary)" }}>• {b}</p>)}
                </div>
              ))}

              {/* Submissions Diff */}
              {resultData && resultData.participants?.map((p: any) => p.submission && (
                <div key={p.id} className="glass-card p-4">
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: p.color }}>{p.name}&apos;s Solution</h4>
                  <pre className="text-[10px] p-3 rounded-lg font-mono overflow-auto max-h-48" style={{ background: "var(--bg-primary)", color: "var(--text-secondary)" }}>{p.submission.code}</pre>
                  {p.submission.explanation && (
                    <div className="mt-2 p-2 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
                      <p className="text-[10px] font-semibold mb-1" style={{ color: "var(--accent-purple)" }}>Explanation:</p>
                      <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{p.submission.explanation}</p>
                    </div>
                  )}
                </div>
              ))}

              <div className="flex gap-3">
                <a href={`/ar?type=battle&id=${sessionId}`} className="flex-1 py-3 rounded-xl text-sm font-bold text-center transition-all flex items-center justify-center gap-2" style={{ background: "linear-gradient(135deg,rgba(79,142,247,0.15),rgba(168,85,247,0.15))", color: "#a855f7", border: "1px solid rgba(168,85,247,0.2)" }}><Eye className="w-4 h-4" /> View in AR</a>
                <button onClick={reset} className="flex-1 py-3 rounded-xl text-sm font-bold flex items-center justify-center gap-2" style={{ background: "linear-gradient(135deg,#ef4444,#8b5cf6)", color: "white" }}><Swords className="w-4 h-4" /> New Battle</button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
