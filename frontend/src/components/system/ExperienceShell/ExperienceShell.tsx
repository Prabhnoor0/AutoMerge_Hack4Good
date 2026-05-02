"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Settings2, Globe, Clock, Zap } from "lucide-react";
import { ChaosMode } from "@/components/visual/ChaosMode/ChaosMode";
import { CommentaryOverlay, pushCommentary } from "@/components/ai/CommentaryOverlay/CommentaryOverlay";

interface Props {
  children: React.ReactNode;
}

export function ExperienceShell({ children }: Props) {
  const [isChaos, setIsChaos] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  const toggleChaos = () => {
    setIsChaos(!isChaos);
    if (!isChaos) {
      pushCommentary("Chaos Simulation Initiated", "warning");
    } else {
      pushCommentary("Stability Restored", "success");
    }
  };

  return (
    <>
      {/* Global Commentary */}
      <CommentaryOverlay />

      <ChaosMode isActive={isChaos}>
        {children}
      </ChaosMode>

      {/* Control Panel Toggle */}
      <div className="fixed bottom-6 left-6 z-[200]">
        <button 
          onClick={() => setPanelOpen(!panelOpen)}
          className="p-3 bg-black/50 backdrop-blur-md border border-white/10 rounded-full text-white/50 hover:text-white transition shadow-xl"
        >
          <Settings2 size={20} />
        </button>

        {/* Panel Options */}
        <AnimatePresence>
          {panelOpen && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.9 }}
              className="absolute bottom-16 left-0 flex flex-col gap-2"
            >
              <button 
                onClick={toggleChaos}
                className={`flex items-center gap-3 px-4 py-3 rounded-2xl border transition-all ${isChaos ? 'bg-red-500/20 border-red-500 text-red-400 shadow-[0_0_15px_rgba(255,0,0,0.5)]' : 'bg-black/80 border-white/10 text-white/70 hover:bg-white/10 hover:text-white'}`}
              >
                <Zap size={16} />
                <span className="text-xs font-mono font-bold">Chaos Sim</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  );
}
