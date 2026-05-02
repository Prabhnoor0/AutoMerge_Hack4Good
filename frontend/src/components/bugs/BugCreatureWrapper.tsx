"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BugCore } from "./BugCore";
import { BugAura } from "./BugAura";
import { BugBehavior } from "./BugBehavior";
import type { Job, JobDetail } from "@/lib/types";
import { CreatePRButton } from "@/components/github/CreatePRButton";
import { useJobDetail } from "@/hooks/useJobs";

interface Props {
  job: Job | JobDetail;
  onClick: () => void;
  isSelected: boolean;
}

export function BugCreatureWrapper({ job, onClick, isSelected }: Props) {
  const [isFixing, setIsFixing] = useState(false);
  const [combatPhase, setCombatPhase] = useState<"idle" | "compress" | "flash" | "done">("idle");

  const handleFix = () => {
    setIsFixing(true);
    setCombatPhase("compress");
    setTimeout(() => setCombatPhase("flash"), 600);
    setTimeout(() => setCombatPhase("done"), 1200);
  };

  const { job: fetchedDetail } = useJobDetail(isSelected ? job.id : null);
  const displayJob = fetchedDetail || job;
  const jobDetail = 'summary' in displayJob ? (displayJob as JobDetail) : null;

  const typeStr = (displayJob.failure_type || "").toLowerCase();
  let creatureType = "blob";
  if (typeStr.includes("syntax")) creatureType = "glitch";
  else if (typeStr.includes("runtime")) creatureType = "blob";
  else if (typeStr.includes("logic")) creatureType = "shadow";
  else if (typeStr.includes("async") || typeStr.includes("promise") || typeStr.includes("timeout")) creatureType = "teleporting";
  else if (typeStr.includes("security") || typeStr.includes("auth")) creatureType = "virus";

  const whyBreaking = jobDetail?.reasoning_trace?.split('\n')[0] || "Analyzing underlying patterns...";
  const fixHint = jobDetail?.summary?.fix_description || "Pending auto-patch generation...";
  const rootCause = jobDetail?.root_cause || displayJob.root_cause || "Detecting root anomaly...";

  return (
    <>
      {/* LIST ITEM VIEW - NO CARD BOUNDARIES */}
      <motion.div
        layoutId={`creature-container-${job.id}`}
        className="relative flex items-center p-6 mb-2 group cursor-pointer"
        onClick={onClick}
      >
        <div className="absolute inset-0 rounded-full group-hover:bg-white/5 transition-colors duration-500 blur-xl" />
        
        <div className="flex-shrink-0 w-16 h-16 relative">
          <BugBehavior type={creatureType} isExpanded={false}>
            <BugAura type={creatureType} isExpanded={false} />
            <motion.div layoutId={`creature-core-${job.id}`}>
              <BugCore type={creatureType} isExpanded={false} />
            </motion.div>
          </BugBehavior>
        </div>

        {/* Text only appears on interaction/hover */}
        <div className="ml-6 flex-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <motion.h3 layoutId={`creature-title-${displayJob.id}`} className="font-mono text-xs text-white/90 truncate drop-shadow-md">
            {displayJob.failure_title}
          </motion.h3>
          <div className="text-[9px] text-white/40 uppercase tracking-widest mt-1">
            {creatureType} ANOMALY
          </div>
        </div>
      </motion.div>

      {/* EXPANDED OVERLAY VIEW */}
      <AnimatePresence>
        {isSelected && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md"
          >
            <div className="absolute inset-0" onClick={onClick} />

            <div className="relative w-full max-w-5xl p-8 flex flex-col md:flex-row items-center gap-16 pointer-events-none">
              
              {/* CENTER CREATURE */}
              <motion.div layoutId={`creature-container-${job.id}`} className="relative flex-shrink-0 w-80 h-80 flex items-center justify-center">
                
                {/* Elegant Fix Animation */}
                <AnimatePresence>
                  {combatPhase === "compress" && (
                    <motion.div
                      initial={{ scale: 1, opacity: 0.5 }}
                      animate={{ scale: 0.1, opacity: 1, filter: "brightness(3)" }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.6, ease: "anticipate" }}
                      className="absolute inset-0 bg-white rounded-full mix-blend-overlay z-50"
                    />
                  )}
                  {combatPhase === "flash" && (
                    <motion.div
                      initial={{ scale: 0.1, opacity: 1 }}
                      animate={{ scale: 4, opacity: 0 }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className="absolute inset-0 bg-cyan-200 rounded-full mix-blend-screen z-50 blur-xl"
                    />
                  )}
                </AnimatePresence>

                {combatPhase === "idle" && (
                  <div className="w-full h-full flex items-center justify-center">
                    <BugBehavior type={creatureType} isExpanded={true}>
                      <BugAura type={creatureType} isExpanded={true} />
                      <motion.div layoutId={`creature-core-${job.id}`}>
                        <BugCore type={creatureType} isExpanded={true} />
                      </motion.div>
                    </BugBehavior>
                  </div>
                )}
              </motion.div>

              {/* DETAILS PANEL (RIGHT) */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ delay: 0.2 }}
                className="flex-1 pointer-events-auto"
              >
                <motion.h2 layoutId={`creature-title-${displayJob.id}`} className="text-2xl font-light text-white mb-8 tracking-wide">
                  {displayJob.failure_title}
                </motion.h2>

                <div className="space-y-8">
                  <div>
                    <h4 className="text-[10px] uppercase tracking-widest text-cyan-400/60 mb-2 font-mono">
                      // ROOT CAUSE
                    </h4>
                    <p className="text-sm text-white/70 leading-relaxed font-light">
                      {rootCause}
                    </p>
                  </div>

                  <div>
                    <h4 className="text-[10px] uppercase tracking-widest text-cyan-400/60 mb-2 font-mono">
                      // BEHAVIORAL EXPLANATION
                    </h4>
                    <p className="text-sm text-white/70 leading-relaxed font-light">
                      {whyBreaking}
                    </p>
                  </div>

                  <div>
                    <h4 className="text-[10px] uppercase tracking-widest text-cyan-400/60 mb-2 font-mono">
                      // RESOLUTION STRATEGY
                    </h4>
                    <p className="text-sm text-white/90 font-mono bg-white/5 px-4 py-3 rounded-sm border-l-2 border-cyan-500/30">
                      {fixHint}
                    </p>
                  </div>

                  {displayJob.status === "completed" && (
                    <div className="pt-6 mt-6 pointer-events-auto">
                      {!isFixing ? (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleFix();
                          }}
                          className="px-6 py-2.5 rounded-sm font-mono text-sm tracking-wider transition-all border border-cyan-500/30 text-cyan-400 hover:bg-cyan-500/10 hover:shadow-[0_0_20px_rgba(0,240,255,0.2)]"
                        >
                          [ INITIATE RESOLUTION ]
                        </button>
                      ) : (
                        <div className={combatPhase === "done" ? "opacity-100 transition-opacity" : "opacity-0 pointer-events-none h-0"}>
                          <CreatePRButton jobId={displayJob.id} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
