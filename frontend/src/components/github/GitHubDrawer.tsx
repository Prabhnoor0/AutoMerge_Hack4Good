"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X, GitFork, Check, AlertCircle, Loader2,
  GitBranch, ExternalLink, Unplug,
} from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function GitHubDrawer({ open, onClose }: Props) {
  const [status, setStatus] = useState<{
    connected: boolean; mode: string; owner: string; repo: string;
  } | null>(null);
  const [token, setToken] = useState("");
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    if (open) {
      api.githubStatus().then(setStatus).catch(() => {});
    }
  }, [open]);

  const handleConnect = async () => {
    if (!token || !owner || !repo) return;
    setLoading(true);
    setMessage(null);
    try {
      const res = await api.githubConnect({ token, owner, repo });
      setMessage({ type: "success", text: res.message });
      setStatus({ connected: true, mode: "live", owner, repo });
      setToken("");
    } catch (e: any) {
      setMessage({ type: "error", text: e.message || "Connection failed" });
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      await api.githubDisconnect();
      setStatus({ connected: false, mode: "mock", owner: "(not configured)", repo: "(not configured)" });
      setMessage({ type: "success", text: "Disconnected — using mock mode" });
    } catch (e: any) {
      setMessage({ type: "error", text: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40"
            style={{ background: "rgba(0,0,0,0.5)" }}
            onClick={onClose}
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-[420px] flex flex-col"
            style={{ background: "var(--bg-secondary)", borderLeft: "1px solid var(--border)" }}
          >
            {/* Header */}
            <div className="h-14 flex items-center justify-between px-5 border-b flex-shrink-0" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2.5">
                <GitFork size={16} style={{ color: "var(--text-primary)" }} />
                <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                  GitHub Integration
                </span>
              </div>
              <button onClick={onClose} className="p-1.5 rounded-md transition-colors" style={{ color: "var(--text-muted)" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}>
                <X size={16} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {/* Status card */}
              <div className="p-4 rounded-xl" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                    Connection Status
                  </span>
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase"
                    style={{
                      background: status?.connected ? "var(--glow-green)" : "var(--bg-elevated)",
                      color: status?.connected ? "var(--accent-green)" : "var(--text-muted)",
                    }}
                  >
                    {status?.connected ? "Live" : "Mock Mode"}
                  </span>
                </div>

                {status && (
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs">
                      <span style={{ color: "var(--text-muted)" }}>Owner:</span>
                      <span className="font-mono font-medium" style={{ color: "var(--text-primary)" }}>
                        {status.owner}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs">
                      <span style={{ color: "var(--text-muted)" }}>Repo:</span>
                      <span className="font-mono font-medium" style={{ color: "var(--text-primary)" }}>
                        {status.repo}
                      </span>
                    </div>
                  </div>
                )}

                {status?.connected && (
                  <button
                    onClick={handleDisconnect}
                    disabled={loading}
                    className="mt-3 flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-colors"
                    style={{ color: "var(--accent-red)", background: "var(--glow-red)" }}
                  >
                    <Unplug size={12} />
                    Disconnect
                  </button>
                )}
              </div>

              {/* Connect form */}
              {!status?.connected && (
                <div className="space-y-3">
                  <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                    Connect Repository
                  </h3>

                  <div>
                    <label className="text-[11px] font-medium block mb-1" style={{ color: "var(--text-secondary)" }}>
                      Personal Access Token
                    </label>
                    <input
                      type="password"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="ghp_xxxxxxxxxxxx"
                      className="w-full px-3 py-2 rounded-lg text-xs font-mono outline-none"
                      style={{
                        background: "var(--bg-primary)",
                        border: "1px solid var(--border)",
                        color: "var(--text-primary)",
                      }}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-medium block mb-1" style={{ color: "var(--text-secondary)" }}>
                        Owner
                      </label>
                      <input
                        value={owner}
                        onChange={(e) => setOwner(e.target.value)}
                        placeholder="username"
                        className="w-full px-3 py-2 rounded-lg text-xs font-mono outline-none"
                        style={{
                          background: "var(--bg-primary)",
                          border: "1px solid var(--border)",
                          color: "var(--text-primary)",
                        }}
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-medium block mb-1" style={{ color: "var(--text-secondary)" }}>
                        Repository
                      </label>
                      <input
                        value={repo}
                        onChange={(e) => setRepo(e.target.value)}
                        placeholder="my-project"
                        className="w-full px-3 py-2 rounded-lg text-xs font-mono outline-none"
                        style={{
                          background: "var(--bg-primary)",
                          border: "1px solid var(--border)",
                          color: "var(--text-primary)",
                        }}
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleConnect}
                    disabled={loading || !token || !owner || !repo}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-semibold transition-all"
                    style={{
                      background: loading || !token ? "var(--bg-elevated)" : "linear-gradient(135deg, #4f8ef7, #6366f1)",
                      color: "white",
                      opacity: loading || !token ? 0.5 : 1,
                    }}
                  >
                    {loading ? (
                      <><Loader2 size={13} className="animate-spin" /> Connecting...</>
                    ) : (
                      <><GitFork size={13} /> Connect</>
                    )}
                  </button>
                </div>
              )}

              {/* Message */}
              {message && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 p-3 rounded-lg text-xs font-medium"
                  style={{
                    background: message.type === "success" ? "var(--glow-green)" : "var(--glow-red)",
                    color: message.type === "success" ? "var(--accent-green)" : "var(--accent-red)",
                  }}
                >
                  {message.type === "success" ? <Check size={14} /> : <AlertCircle size={14} />}
                  {message.text}
                </motion.div>
              )}

              {/* How it works */}
              <div className="p-4 rounded-xl" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <h3 className="text-xs font-semibold mb-3" style={{ color: "var(--text-primary)" }}>
                  How GitHub Integration Works
                </h3>
                <div className="space-y-2.5">
                  {[
                    { step: "1", text: "AutoMerge creates a fix branch from main" },
                    { step: "2", text: "The generated patch is committed to the branch" },
                    { step: "3", text: "A pull request is opened with full context" },
                    { step: "4", text: "You review and merge when ready" },
                  ].map((item) => (
                    <div key={item.step} className="flex items-start gap-2.5">
                      <div
                        className="w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-bold"
                        style={{ background: "var(--bg-elevated)", color: "var(--accent-blue)" }}
                      >
                        {item.step}
                      </div>
                      <span className="text-xs" style={{ color: "var(--text-secondary)" }}>
                        {item.text}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
