"use client";
import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Focus, Zap, FolderOpen, Rocket, Swords, AlertTriangle, Lightbulb } from "lucide-react";
import { api } from "@/lib/api";
import type { ARScene, ARNode, AREdge, ARSourceType, ARHistoryEntry } from "@/lib/types";
import { useSearchParams } from "next/navigation";

// ─── Constants ───────────────────────────────────────────
const SOURCE_LABELS: Record<ARSourceType, string> = { studio: "Studio", repo: "Repo Explorer", deploy: "Deploy", battle: "Battle" };
const SOURCE_ICONS: Record<ARSourceType, React.ElementType> = { studio: Zap, repo: FolderOpen, deploy: Rocket, battle: Swords };
const STATUS_GLOW: Record<string, string> = { error: "#ef4444", warning: "#f59e0b", success: "#22c55e", active: "#3b82f6", default: "#6b7280", highlight: "#a855f7", winner: "#fbbf24", finished: "#22c55e", submitted: "#3b82f6", info: "#3b82f6" };

// ─── Sub-components ──────────────────────────────────────
function MetricBadge({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex flex-col items-center px-3 py-2 rounded-xl border" style={{ borderColor: `${color}33`, background: `${color}0a` }}>
      <span className="text-lg font-bold" style={{ color }}>{value}</span>
      <span className="text-[10px] font-medium uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</span>
    </div>
  );
}

function NodeCard({ node, selected, onClick }: { node: ARNode; selected: boolean; onClick: () => void }) {
  const glow = STATUS_GLOW[node.status] || node.color;
  return (
    <motion.div
      layout layoutId={node.id}
      onClick={onClick}
      whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
      className="cursor-pointer rounded-xl border p-3 transition-all"
      style={{
        borderColor: selected ? glow : `${glow}33`,
        background: selected ? `${glow}15` : "var(--bg-card)",
        boxShadow: selected ? `0 0 20px ${glow}30` : "none",
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: glow, boxShadow: `0 0 8px ${glow}60` }} />
        <span className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{node.label}</span>
        {node.severity && (
          <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ml-auto" style={{ background: `${glow}20`, color: glow }}>{node.severity}</span>
        )}
      </div>
      {node.description && <p className="text-[11px] line-clamp-2 mt-1" style={{ color: "var(--text-muted)" }}>{node.description}</p>}
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}>{node.type}</span>
        {node.source_line != null && <span className="text-[9px]" style={{ color: "var(--text-muted)" }}>L{node.source_line}</span>}
      </div>
    </motion.div>
  );
}

function TimelineRail({ steps }: { steps: ARScene["timeline"] }) {
  if (!steps.length) return null;
  return (
    <div className="space-y-1">
      {steps.map((s, i) => {
        const c = STATUS_GLOW[s.status] || "#6b7280";
        return (
          <div key={i} className="flex items-start gap-2">
            <div className="flex flex-col items-center mt-1">
              <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: c }} />
              {i < steps.length - 1 && <div className="w-px flex-1 min-h-[16px]" style={{ background: `${c}40` }} />}
            </div>
            <div className="flex-1 pb-2">
              <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{s.label}</p>
              {s.detail && <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{s.detail}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── 3D Canvas (CSS 3D + SVG hybrid) ────────────────────
function SceneCanvas({ scene, selectedNode, onSelectNode }: { scene: ARScene; selectedNode: string | null; onSelectNode: (id: string | null) => void }) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [rotation, setRotation] = useState({ x: 15, y: 0 });
  const [dragging, setDragging] = useState(false);
  const lastMouse = useRef({ x: 0, y: 0 });

  const handleMouseDown = (e: React.MouseEvent) => { setDragging(true); lastMouse.current = { x: e.clientX, y: e.clientY }; };
  const handleMouseUp = () => setDragging(false);
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;
    const dx = e.clientX - lastMouse.current.x;
    const dy = e.clientY - lastMouse.current.y;
    setRotation(r => ({ x: Math.max(-30, Math.min(60, r.x - dy * 0.3)), y: r.y + dx * 0.3 }));
    lastMouse.current = { x: e.clientX, y: e.clientY };
  };

  // Layout nodes in layers
  const layers: Record<string, ARNode[]> = {};
  scene.nodes.forEach(n => {
    const layer = n.position_hint?.layer || "default";
    if (!layers[layer]) layers[layer] = [];
    layers[layer].push(n);
  });

  const layerOrder = ["center", "issues", "fix", "validation", "modules", "entry_points", "routes", "components", "platform", "checks", "players", "default"];
  const nodePositions: Record<string, { x: number; y: number; z: number }> = {};

  let layerIdx = 0;
  layerOrder.forEach(layerName => {
    const layerNodes = layers[layerName];
    if (!layerNodes) return;
    const radius = layerName === "center" ? 0 : 140 + layerIdx * 60;
    layerNodes.forEach((n, i) => {
      if (layerName === "center") {
        nodePositions[n.id] = { x: 0, y: 0, z: 0 };
      } else {
        const angle = (i / layerNodes.length) * Math.PI * 2 - Math.PI / 2;
        nodePositions[n.id] = { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, z: -layerIdx * 30 };
      }
    });
    if (layerNodes.length) layerIdx++;
  });

  const cx = 400, cy = 300;

  return (
    <div ref={canvasRef} className="relative w-full h-full overflow-hidden rounded-2xl" style={{ background: "radial-gradient(ellipse at center, #0f1729 0%, #060a14 100%)", cursor: dragging ? "grabbing" : "grab" }}
      onMouseDown={handleMouseDown} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp} onMouseMove={handleMouseMove}
    >
      {/* Grid effect */}
      <div className="absolute inset-0 opacity-10" style={{ backgroundImage: "linear-gradient(rgba(79,142,247,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(79,142,247,0.15) 1px, transparent 1px)", backgroundSize: "40px 40px" }} />

      <svg width="100%" height="100%" viewBox="0 0 800 600" className="absolute inset-0" style={{ transform: `perspective(1200px) rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`, transformOrigin: "center center", transition: dragging ? "none" : "transform 0.3s ease" }}>
        {/* Edges */}
        {scene.edges.map((e, i) => {
          const from = nodePositions[e.from];
          const to = nodePositions[e.to];
          if (!from || !to) return null;
          return (
            <g key={`e${i}`}>
              <line x1={cx + from.x} y1={cy + from.y} x2={cx + to.x} y2={cy + to.y}
                stroke="rgba(79,142,247,0.2)" strokeWidth={1.5}
                strokeDasharray={e.style === "dashed" ? "6 4" : "none"} />
              {e.label && (
                <text x={cx + (from.x + to.x) / 2} y={cy + (from.y + to.y) / 2 - 6}
                  fill="rgba(148,163,184,0.5)" fontSize={8} textAnchor="middle">{e.label}</text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {scene.nodes.map(n => {
          const pos = nodePositions[n.id];
          if (!pos) return null;
          const isSel = selectedNode === n.id;
          const glow = STATUS_GLOW[n.status] || n.color;
          const r = n.position_hint?.layer === "center" ? 32 : 20;
          return (
            <g key={n.id} onClick={(e) => { e.stopPropagation(); onSelectNode(isSel ? null : n.id); }} className="cursor-pointer">
              {/* Glow */}
              <circle cx={cx + pos.x} cy={cy + pos.y} r={r + 8} fill="none" stroke={glow} strokeWidth={isSel ? 2 : 0} opacity={0.4}>
                <animate attributeName="r" values={`${r + 6};${r + 12};${r + 6}`} dur="3s" repeatCount="indefinite" />
              </circle>
              {/* Node circle */}
              <circle cx={cx + pos.x} cy={cy + pos.y} r={r} fill={`${glow}25`} stroke={glow} strokeWidth={isSel ? 2.5 : 1.5} />
              {/* Inner dot */}
              <circle cx={cx + pos.x} cy={cy + pos.y} r={4} fill={glow}>
                <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />
              </circle>
              {/* Label */}
              <text x={cx + pos.x} y={cy + pos.y + r + 14} fill="var(--text-secondary)" fontSize={9} textAnchor="middle" fontWeight={500}>
                {n.label.length > 25 ? n.label.slice(0, 24) + "…" : n.label}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Floating title */}
      <div className="absolute top-4 left-4 flex items-center gap-2">
        <div className="px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider flex items-center gap-2" style={{ background: "rgba(79,142,247,0.15)", color: "#4f8ef7", border: "1px solid rgba(79,142,247,0.2)" }}>
          {(() => { const Icon = SOURCE_ICONS[scene.source_type] || Focus; return <Icon className="w-3.5 h-3.5" />; })()} {scene.source_type}
        </div>
      </div>

      {/* Controls */}
      <div className="absolute bottom-4 right-4 flex items-center gap-2">
        <button onClick={() => setRotation({ x: 15, y: 0 })} className="px-3 py-1.5 rounded-lg text-[10px] font-semibold" style={{ background: "rgba(255,255,255,0.05)", color: "var(--text-muted)", border: "1px solid rgba(255,255,255,0.08)" }}>
          Reset View
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────
function ARPageInner() {
  const params = useSearchParams();
  const [scene, setScene] = useState<ARScene | null>(null);
  const [history, setHistory] = useState<ARHistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [tab, setTab] = useState<"graph" | "timeline" | "annotations">("graph");
  const [sourceInput, setSourceInput] = useState("");
  const [sourceType, setSourceType] = useState<ARSourceType>("studio");

  // Load from URL params or sessionStorage live data
  useEffect(() => {
    const type = params.get("type") as ARSourceType;
    const id = params.get("id");
    const mode = params.get("mode");

    // Check if live data was passed via sessionStorage
    if (mode === "live" && type === "studio") {
      try {
        const raw = sessionStorage.getItem("ar_live_data");
        if (raw) {
          sessionStorage.removeItem("ar_live_data");
          const liveData = JSON.parse(raw);
          setSourceType("studio"); setSourceInput(id || "live");
          loadLiveStudioScene(liveData);
          loadHistory();
          return;
        }
      } catch {}
    }

    if (type && id) { setSourceType(type); setSourceInput(id); loadScene(type, id); }
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try { const r = await api.arHistory(); setHistory(r.data || []); } catch {}
  };

  const loadScene = useCallback(async (type: ARSourceType, id: string) => {
    setLoading(true); setError(null); setScene(null); setSelectedNode(null);
    try {
      let res: any;
      if (type === "studio") res = await api.arStudioScene(id);
      else if (type === "repo") res = await api.arRepoScene(id);
      else if (type === "deploy") res = await api.arDeployScene(id);
      else if (type === "battle") res = await api.arBattleScene(id);
      if (res?.data) setScene(res.data);
      else setError("No scene data returned");
      loadHistory();
    } catch (e: any) { setError(e.message || "Failed to load scene"); }
    finally { setLoading(false); }
  }, []);

  const loadLiveStudioScene = useCallback(async (data: any) => {
    setLoading(true); setError(null); setScene(null); setSelectedNode(null);
    try {
      const res = await api.arStudioSceneLive(data);
      if (res?.data) setScene(res.data);
      else setError("No scene data returned");
    } catch (e: any) { setError(e.message || "Failed to load live scene"); }
    finally { setLoading(false); }
  }, []);

  const handleLoad = () => { if (sourceInput.trim()) loadScene(sourceType, sourceInput.trim()); };

  const selNode = scene?.nodes.find(n => n.id === selectedNode);

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-primary)" }}>
      {/* Top Bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center text-white" style={{ background: "linear-gradient(135deg, #4f8ef7, #a855f7)", boxShadow: "0 0 20px rgba(79,142,247,0.3)" }}>
            <Focus className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>AR Debug Explorer</h1>
            <p className="text-[10px] uppercase tracking-wider font-medium" style={{ color: "var(--text-muted)" }}>
              {scene ? scene.title : "Immersive Debugging Visualizer"}
            </p>
          </div>
        </div>
        {scene && (
          <div className="flex items-center gap-3">
            {scene.metrics.map((m, i) => <MetricBadge key={i} {...m} />)}
          </div>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel: Source Selector + History */}
        <div className="w-64 flex-shrink-0 border-r overflow-y-auto p-4 space-y-4" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
          {/* Source Input */}
          <div className="space-y-2">
            <label className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Source</label>
            <div className="relative">
              <select value={sourceType} onChange={e => setSourceType(e.target.value as ARSourceType)}
                className="w-full pl-8 pr-3 py-2 rounded-lg text-sm border outline-none appearance-none" style={{ background: "var(--bg-card)", borderColor: "var(--border)", color: "var(--text-primary)" }}>
                {(Object.keys(SOURCE_LABELS) as ARSourceType[]).map(k => <option key={k} value={k}>{SOURCE_LABELS[k]}</option>)}
              </select>
              <div className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
                {(() => { const Icon = SOURCE_ICONS[sourceType] || Focus; return <Icon className="w-3.5 h-3.5 text-gray-400" />; })()}
              </div>
            </div>
            <input value={sourceInput} onChange={e => setSourceInput(e.target.value)} placeholder="Enter ID..."
              className="w-full px-3 py-2 rounded-lg text-sm border outline-none font-mono" style={{ background: "var(--bg-card)", borderColor: "var(--border)", color: "var(--text-primary)" }}
              onKeyDown={e => e.key === "Enter" && handleLoad()} />
            <button onClick={handleLoad} disabled={loading || !sourceInput.trim()}
              className="w-full py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-40"
              style={{ background: "linear-gradient(135deg, #4f8ef7, #6366f1)", color: "white" }}>
              {loading ? "Loading..." : "Generate Scene"}
            </button>
          </div>

          {/* History */}
          <div>
            <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-muted)" }}>Recent Scenes</h3>
            <div className="space-y-1.5">
              {history.slice(0, 15).map(h => {
                const Icon = SOURCE_ICONS[h.source_type] || Focus;
                return (
                  <button key={h.scene_id} onClick={() => { setSourceType(h.source_type); setSourceInput(h.source_id); loadScene(h.source_type, h.source_id); }}
                    className="w-full text-left p-2.5 rounded-lg border transition-all hover:border-[var(--accent-blue)]"
                    style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-1.5">
                      <Icon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                      <span className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>{h.title}</span>
                    </div>
                    <span className="text-[9px] mt-0.5 block" style={{ color: "var(--text-muted)" }}>Views: {h.view_count}</span>
                  </button>
                );
              })}
              {!history.length && <p className="text-xs text-center py-4" style={{ color: "var(--text-muted)" }}>No scenes yet</p>}
            </div>
          </div>
        </div>

        {/* Center: Scene Canvas */}
        <div className="flex-1 flex flex-col">
          {error && <div className="m-4 p-3 rounded-xl text-sm border" style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.2)", color: "#ef4444" }}>{error}</div>}

          {!scene && !loading && !error && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4" style={{ color: "var(--text-muted)" }}>
              <div className="opacity-20"><Focus className="w-16 h-16" /></div>
              <p className="text-sm font-medium">Select a source or enter an ID to visualize</p>
              <p className="text-xs">Studio job IDs, Repo report IDs, Deploy run IDs, or Battle session IDs</p>
            </div>
          )}

          {loading && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4">
              <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2, ease: "linear" }} className="text-blue-500"><Focus className="w-12 h-12" /></motion.div>
              <p className="text-sm font-medium animate-pulse" style={{ color: "var(--accent-blue)" }}>Generating AR scene...</p>
            </div>
          )}

          {scene && !loading && (
            <div className="flex-1 p-4">
              <SceneCanvas scene={scene} selectedNode={selectedNode} onSelectNode={setSelectedNode} />
            </div>
          )}
        </div>

        {/* Right Panel: Inspector */}
        {scene && (
          <div className="w-80 flex-shrink-0 border-l overflow-y-auto" style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}>
            {/* Tabs */}
            <div className="flex border-b" style={{ borderColor: "var(--border)" }}>
              {(["graph", "timeline", "annotations"] as const).map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className="flex-1 py-2.5 text-xs font-semibold uppercase tracking-wider transition-all"
                  style={{ color: tab === t ? "var(--accent-blue)" : "var(--text-muted)", borderBottom: tab === t ? "2px solid var(--accent-blue)" : "2px solid transparent" }}>
                  {t === "graph" ? "Nodes" : t === "timeline" ? "Timeline" : "Insights"}
                </button>
              ))}
            </div>

            <div className="p-4 space-y-3">
              {/* Summary */}
              <div className="p-3 rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
                <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>{scene.summary}</p>
                {scene.warnings.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {scene.warnings.map((w, i) => (
                      <div key={i} className="flex items-start gap-1.5 text-[11px]" style={{ color: "#f59e0b" }}>
                        <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" /><span>{w}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {tab === "graph" && (
                <>
                  {/* Selected Node Detail */}
                  {selNode && (
                    <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
                      className="p-4 rounded-xl border" style={{ background: `${selNode.color}08`, borderColor: `${selNode.color}30` }}>
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-3 h-3 rounded-full" style={{ background: selNode.color }} />
                        <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{selNode.label}</h3>
                      </div>
                      {selNode.description && <p className="text-xs mb-2" style={{ color: "var(--text-secondary)" }}>{selNode.description}</p>}
                      <div className="flex flex-wrap gap-1.5">
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}>{selNode.type}</span>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}>{selNode.status}</span>
                        {selNode.source_line != null && <span className="text-[9px] font-mono px-1.5 py-0.5 rounded" style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}>Line {selNode.source_line}</span>}
                      </div>
                      {selNode.metadata?.fix_hint && (
                        <div className="mt-2 p-2 rounded-lg text-[11px] flex items-start gap-1.5" style={{ background: "rgba(34,197,94,0.08)", color: "#22c55e" }}>
                          <Lightbulb className="w-3 h-3 flex-shrink-0 mt-0.5" /> {selNode.metadata.fix_hint}
                        </div>
                      )}
                    </motion.div>
                  )}

                  {/* All Nodes */}
                  <div className="space-y-2">
                    {scene.nodes.map(n => <NodeCard key={n.id} node={n} selected={selectedNode === n.id} onClick={() => setSelectedNode(selectedNode === n.id ? null : n.id)} />)}
                  </div>
                </>
              )}

              {tab === "timeline" && <TimelineRail steps={scene.timeline} />}

              {tab === "annotations" && (
                <div className="space-y-2">
                  {scene.annotations.map((a, i) => (
                    <div key={i} className="p-3 rounded-xl border" style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded" style={{ background: a.type === "ai" ? "rgba(168,85,247,0.15)" : "rgba(79,142,247,0.15)", color: a.type === "ai" ? "#a855f7" : "#4f8ef7" }}>{a.type}</span>
                        <span className="text-xs font-semibold" style={{ color: "var(--text-primary)" }}>{a.label}</span>
                      </div>
                      {a.content && <p className="text-[11px] whitespace-pre-line" style={{ color: "var(--text-secondary)" }}>{a.content}</p>}
                    </div>
                  ))}
                  {!scene.annotations.length && <p className="text-xs text-center py-6" style={{ color: "var(--text-muted)" }}>No annotations</p>}
                </div>
              )}

              {/* Fallback Text */}
              {scene.fallback_text && (
                <details className="mt-4">
                  <summary className="text-[10px] font-semibold uppercase tracking-wider cursor-pointer" style={{ color: "var(--text-muted)" }}>Fallback View</summary>
                  <pre className="mt-2 p-3 rounded-lg text-[11px] overflow-x-auto font-mono" style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}>{scene.fallback_text}</pre>
                </details>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ARPage() {
  return (
    <Suspense fallback={<div className="flex-1 flex items-center justify-center" style={{ color: "var(--text-muted)" }}>Loading AR Explorer...</div>}>
      <ARPageInner />
    </Suspense>
  );
}
