"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Fingerprint, TrendingUp, RefreshCw, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import type { BugPattern } from "@/lib/types";

export function BugMemoryPanel({ currentFailureType }: { currentFailureType?: string }) {
  const [patterns, setPatterns] = useState<BugPattern[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .bugPatterns()
      .then((data) => setPatterns(data))
      .catch(() => setPatterns([]))
      .finally(() => setLoading(false));
  }, []);

  const relevant = currentFailureType
    ? patterns.filter((p) => p.failure_type === currentFailureType)
    : patterns;

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-3">
        <RefreshCw size={14} className="animate-spin" style={{ color: "var(--accent-blue)" }} />
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>Loading bug memory...</span>
      </div>
    );
  }

  if (relevant.length === 0) {
    return (
      <div className="flex items-center gap-2 py-3 px-3 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
        <Fingerprint size={14} style={{ color: "var(--text-muted)" }} />
        <span className="text-xs" style={{ color: "var(--text-muted)" }}>
          No matching bug patterns in memory yet. Patterns will accumulate as more jobs run.
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {relevant.slice(0, 5).map((p, i) => (
        <motion.div
          key={p.id}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
          className="flex items-center gap-3 p-3 rounded-xl"
          style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)" }}
        >
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{
              background:
                p.occurrence_count >= 3
                  ? "rgba(239,68,68,0.12)"
                  : "rgba(245,158,11,0.12)",
            }}
          >
            {p.occurrence_count >= 3 ? (
              <AlertTriangle size={14} style={{ color: "var(--accent-red)" }} />
            ) : (
              <Fingerprint size={14} style={{ color: "var(--accent-amber)" }} />
            )}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold truncate" style={{ color: "var(--text-primary)" }}>
                {p.root_cause_category || p.pattern_signature}
              </span>
              {p.occurrence_count >= 3 && (
                <span
                  className="text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase"
                  style={{ background: "var(--glow-red)", color: "var(--accent-red)" }}
                >
                  Recurring
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 mt-1 text-[10px]" style={{ color: "var(--text-muted)" }}>
              <span className="flex items-center gap-1">
                <TrendingUp size={9} />
                {p.occurrence_count}× seen
              </span>
              <span>{Math.round(p.resolution_rate * 100)}% resolved</span>
              <span className="font-mono">{p.failure_type}</span>
            </div>
          </div>

          {/* Resolution rate ring */}
          <div className="flex-shrink-0 text-right">
            <div
              className="text-sm font-bold"
              style={{
                color: p.resolution_rate >= 0.8 ? "var(--accent-green)" : "var(--accent-amber)",
              }}
            >
              {Math.round(p.resolution_rate * 100)}%
            </div>
            <div className="text-[9px]" style={{ color: "var(--text-muted)" }}>
              fix rate
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
