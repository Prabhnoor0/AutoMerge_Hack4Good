import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { STATUS_COLORS } from '@/lib/types';
import type { Job, JobDetail } from '@/lib/types';
import { Clock, Loader2, RotateCcw, CheckCircle2, AlertCircle, Bug, ShieldAlert, Target } from 'lucide-react';
import { useJobDetail } from '@/hooks/useJobs';
import { BugAura } from '../bugs/BugAura';
import { BugCore } from '../bugs/BugCore';
import { BugBehavior } from '../bugs/BugBehavior';

const STATUS_ICONS: Record<string, React.ReactNode> = {
  queued: <Clock size={14} />,
  analyzing: <Loader2 size={14} className="animate-spin" />,
  diagnosing: <Loader2 size={14} className="animate-spin" />,
  patching: <Loader2 size={14} className="animate-spin" />,
  validating: <Loader2 size={14} className="animate-spin" />,
  summarizing: <Loader2 size={14} className="animate-spin" />,
  retrying: <RotateCcw size={14} className="animate-spin" />,
  completed: <CheckCircle2 size={14} />,
  failed: <AlertCircle size={14} />,
};

interface MissionCardProps {
  job: Job;
  isSelected: boolean;
  onClick: () => void;
  index: number;
}

export function MissionCard({ job, isSelected, onClick, index }: MissionCardProps) {
  const { job: jobDetail, loading } = useJobDetail(isSelected ? job.id : null);
  const displayJob = jobDetail || job;
  const detail = 'summary' in displayJob ? (displayJob as JobDetail) : null;

  // Derive game-like stats
  const stabilityPercent = Math.max(10, Math.round(displayJob.confidence_score * 100));
  const difficulty = stabilityPercent < 40 ? 'EXTREME' : stabilityPercent < 80 ? 'HARD' : 'NORMAL';

  let hash = 0;
  for (let i = 0; i < job.id.length; i++) {
    hash = job.id.charCodeAt(i) + ((hash << 5) - hash);
  }
  const bugCount = (Math.abs(hash) % 5) + 1;

  let badgeClass = "cyber-badge-info";
  if (displayJob.status === "completed") badgeClass = "cyber-badge-success";
  if (displayJob.status === "failed") badgeClass = "cyber-badge-error";
  if (displayJob.status.includes("ing") || displayJob.status === "queued") badgeClass = "cyber-badge-warning cyber-badge-live";

  // Visual Entity Mapping
  const typeStr = (displayJob.failure_type || "").toLowerCase();
  let creatureType = "blob";
  if (typeStr.includes("syntax")) creatureType = "glitch";
  else if (typeStr.includes("runtime")) creatureType = "blob";
  else if (typeStr.includes("logic")) creatureType = "shadow";
  else if (typeStr.includes("async") || typeStr.includes("promise") || typeStr.includes("timeout")) creatureType = "teleporting";
  else if (typeStr.includes("security") || typeStr.includes("auth")) creatureType = "virus";

  const pulseClass = difficulty === 'EXTREME' ? 'cyber-pulse-fast' : difficulty === 'HARD' ? 'cyber-pulse-slow' : '';
  const rootCause = detail?.root_cause || displayJob.root_cause || "Analyzing underlying structures...";
  const whyBreaking = detail?.reasoning_trace?.split('\n')[0] || "Analysis pending...";
  const fixHint = detail?.summary?.fix_description || "Auto-patch generation pending...";

  return (
    <motion.button
      layout
      onClick={onClick}
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      whileHover={{ scale: isSelected ? 1 : 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`w-full text-left relative overflow-hidden mb-4 group ${isSelected ? `cyber-panel-accent ${pulseClass} border-cyan-400` : 'cyber-panel hover:border-cyan-400/50'}`}
      style={{
        boxShadow: isSelected ? `var(--cyber-shadow-md), 0 0 ${difficulty === 'EXTREME' ? 30 : 15}px ${difficulty === 'EXTREME' ? 'rgba(255,0,0,0.3)' : 'rgba(0,240,255,0.15)'}` : '',
        transition: 'all 0.3s ease-out'
      }}
    >
      {/* Visual Energy Entity Layer (Background) */}
      <div className="absolute right-0 top-1/2 -translate-y-1/2 opacity-60 pointer-events-none scale-125 group-hover:opacity-100 transition-opacity blur-[2px] group-hover:blur-0">
        <BugBehavior type={creatureType} isExpanded={false}>
          <BugAura type={creatureType} isExpanded={false} />
          <BugCore type={creatureType} isExpanded={false} />
        </BugBehavior>
      </div>

      <div className="cyber-panel-grid opacity-30 pointer-events-none"></div>
      <div className="cyber-panel-inner-glow opacity-50 pointer-events-none"></div>

      {displayJob.status.includes('ing') && (
        <div className="absolute top-0 left-0 w-full h-[2px] bg-cyan-400 opacity-50 shadow-[0_0_8px_#00f0ff] cyber-animate-scanline pointer-events-none z-0" />
      )}

      <motion.div layout="position" className="relative z-10 p-4">
        <div className="flex justify-between items-start mb-3">
          <div className="flex items-center gap-2">
            <div className={`cyber-badge ${badgeClass}`}>
              {STATUS_ICONS[displayJob.status] || <Bug size={14} />}
              <span>{displayJob.status}</span>
            </div>
            {displayJob.mode === "demo" && (
              <span className="cyber-badge cyber-badge-ai">SIMULATION</span>
            )}
          </div>

          <div
            className="flex items-center gap-1 text-[10px] uppercase font-bold tracking-widest px-2 py-1 rounded backdrop-blur-sm"
            style={{
              color: difficulty === 'EXTREME' ? 'var(--cyber-neon-red)' : difficulty === 'HARD' ? 'var(--cyber-accent-amber)' : 'var(--cyber-neon-cyan)',
              background: 'rgba(0,0,0,0.4)',
              border: `1px solid ${difficulty === 'EXTREME' ? 'rgba(255,0,0,0.3)' : 'rgba(0,240,255,0.2)'}`
            }}
          >
            <ShieldAlert size={12} />
            <span>{difficulty}</span>
          </div>
        </div>

        <h3 className="font-mono text-sm md:text-base font-bold text-white mb-4 leading-tight pr-8">
          {displayJob.failure_title || "UNKNOWN MISSION OBJECTIVE"}
        </h3>

        {/* Expanded Panel Details */}
        <AnimatePresence>
          {isSelected && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="py-4 mt-2 mb-4 border-t border-b border-white/10 space-y-4">
                <div>
                  <h4 className="text-[10px] uppercase tracking-widest text-white/40 mb-1 flex items-center gap-2">
                    <ShieldAlert size={12} /> Root Cause
                  </h4>
                  <p className="text-xs text-white/80 border-l-2 border-white/20 pl-2">
                    {rootCause}
                  </p>
                </div>
                <div>
                  <h4 className="text-[10px] uppercase tracking-widest text-white/40 mb-1 flex items-center gap-2">
                    <Bug size={12} /> Why it's breaking
                  </h4>
                  <p className="text-xs text-white/70 bg-white/5 p-2 rounded">
                    {whyBreaking}
                  </p>
                </div>
                <div>
                  <h4 className="text-[10px] uppercase tracking-widest text-cyan-400 mb-1 flex items-center gap-2">
                    <Target size={12} /> Fix Hint
                  </h4>
                  <p className="text-xs text-cyan-100 font-mono bg-cyan-900/30 p-2 rounded border border-cyan-500/20">
                    {fixHint}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex items-center justify-between mt-auto pt-3 border-t border-white/5">
          <div className="flex flex-col flex-1 mr-4">
            <span className="text-[9px] uppercase tracking-widest text-white/40 mb-1.5 font-mono">System Stability</span>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1 bg-black/60 rounded-full overflow-hidden border border-white/10">
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{
                    width: `${stabilityPercent}%`,
                    background: stabilityPercent >= 80 ? 'var(--cyber-success)' : stabilityPercent >= 40 ? 'var(--cyber-accent-amber)' : 'var(--cyber-neon-red)',
                    boxShadow: `0 0 5px ${stabilityPercent >= 80 ? 'var(--cyber-success)' : stabilityPercent >= 40 ? 'var(--cyber-accent-amber)' : 'var(--cyber-neon-red)'}`
                  }}
               />
              </div>
              <span
                className="text-[10px] font-mono font-bold w-8 text-right"
                style={{ color: stabilityPercent >= 80 ? 'var(--cyber-success)' : stabilityPercent >= 40 ? 'var(--cyber-accent-amber)' : 'var(--cyber-neon-red)' }}
              >
                {stabilityPercent}%
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono font-bold text-white/70 bg-black/30 px-2 py-1 rounded border border-white/5 backdrop-blur-sm">
            <Target size={12} className="text-[var(--cyber-neon-cyan)]" />
            <span>{bugCount} TARGET{bugCount > 1 ? 'S' : ''}</span>
          </div>
        </div>
      </motion.div>
    </motion.button>
  );
}
