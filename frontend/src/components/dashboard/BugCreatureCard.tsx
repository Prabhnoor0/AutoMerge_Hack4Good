"use client";

import { motion } from "framer-motion";
import type { JobDetail } from "@/lib/types";
import { BugCore } from "../bugs/BugCore";
import { BugAura } from "../bugs/BugAura";
import { BugBehavior } from "../bugs/BugBehavior";

interface Props {
  job: JobDetail;
}

export function BugCreatureCard({ job }: Props) {
  const typeStr = (job.failure_type || "").toLowerCase();
  let creatureType = "blob";
  if (typeStr.includes("syntax")) creatureType = "glitch";
  else if (typeStr.includes("runtime")) creatureType = "blob";
  else if (typeStr.includes("logic")) creatureType = "shadow";
  else if (typeStr.includes("async") || typeStr.includes("promise") || typeStr.includes("timeout")) creatureType = "teleporting";
  else if (typeStr.includes("security") || typeStr.includes("auth")) creatureType = "virus";

  return (
    <div className="relative w-full h-80 flex items-center justify-center overflow-hidden rounded-2xl bg-black/40 border border-white/5 shadow-2xl">
      <div className="absolute inset-0 opacity-20 pointer-events-none cyber-panel-grid" />
      
      <div className="relative w-full h-full flex flex-col items-center justify-center gap-6">
        <div className="w-48 h-48 flex items-center justify-center">
          <BugBehavior type={creatureType} isExpanded={true}>
            <BugAura type={creatureType} isExpanded={true} />
            <BugCore type={creatureType} isExpanded={true} />
          </BugBehavior>
        </div>

        <div className="text-center z-10">
          <h3 className="font-mono text-xl font-bold text-white tracking-widest drop-shadow-[0_0_10px_rgba(255,255,255,0.3)]">
            {creatureType.toUpperCase()} ANOMALY DETECTED
          </h3>
          <p className="mt-2 text-[10px] text-cyan-400/60 uppercase tracking-[0.5em]">
            Isolation Protocol Active
          </p>
        </div>
      </div>
    </div>
  );
}
