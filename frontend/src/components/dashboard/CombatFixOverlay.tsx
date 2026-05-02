"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { Zap, Shield, Star, CheckCircle2 } from "lucide-react";

interface Props {
  isActive: boolean;
  onComplete: () => void;
  diffText?: string;
}

export function CombatFixOverlay({ isActive, onComplete, diffText }: Props) {
  const [phase, setPhase] = useState<"charging" | "striking" | "exploding" | "success">("charging");

  useEffect(() => {
    if (!isActive) return;
    
    setPhase("charging");
    const t1 = setTimeout(() => setPhase("striking"), 1500);
    const t2 = setTimeout(() => setPhase("exploding"), 1800);
    const t3 = setTimeout(() => setPhase("success"), 2800);
    const t4 = setTimeout(() => onComplete(), 5000);

    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, [isActive, onComplete]);

  if (!isActive) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-lg overflow-hidden pointer-events-none"
    >
      <div className="relative w-full h-full flex flex-col items-center justify-center">

        {/* CHARGING PHASE */}
        <AnimatePresence>
          {phase === "charging" && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1.2, opacity: 1, filter: "brightness(2)" }}
              exit={{ scale: 0, opacity: 0, filter: "brightness(5)" }}
              transition={{ duration: 1.5, ease: "easeIn" }}
              className="flex flex-col items-center"
            >
              <div className="w-32 h-32 rounded-full border-4 border-cyan-400 border-t-transparent animate-spin" />
              <div className="absolute inset-0 bg-cyan-500/20 rounded-full blur-xl animate-pulse" />
              <h2 className="mt-8 text-2xl font-mono font-bold text-cyan-400 tracking-[0.5em] uppercase animate-pulse">
                Target Locked
              </h2>
              <p className="mt-2 font-mono text-cyan-200/50 text-sm">Charging Neural Fix...</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* STRIKING PHASE */}
        <AnimatePresence>
          {phase === "striking" && (
            <motion.div
              initial={{ x: "-100vw", y: "-100vh", rotate: 45, scale: 2 }}
              animate={{ x: "100vw", y: "100vh", rotate: 45, scale: 2 }}
              transition={{ duration: 0.3, ease: "linear" }}
              className="absolute w-[200vw] h-4 bg-white shadow-[0_0_50px_#fff,0_0_100px_#00f0ff] z-50"
            />
          )}
        </AnimatePresence>

        {/* EXPLODING PHASE (The Bug dying) */}
        <AnimatePresence>
          {phase === "exploding" && (
            <motion.div
              key="explode-flash"
              initial={{ scale: 1, opacity: 1 }}
              animate={{ scale: 4, opacity: 0 }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="absolute w-64 h-64 bg-red-500 rounded-full mix-blend-screen blur-2xl"
            />
          )}
          {phase === "exploding" && (
            <motion.div
              key="explode-text"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute font-mono text-4xl font-black text-red-500 tracking-widest drop-shadow-[0_0_20px_#ff0000]"
            >
              BUG NEUTRALIZED
            </motion.div>
          )}
        </AnimatePresence>

        {/* SUCCESS & DIFF REVEAL */}
        <AnimatePresence>
          {phase === "success" && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0, y: 50 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              className="flex flex-col items-center w-full max-w-4xl px-8"
            >
              <div className="flex items-center gap-4 mb-8">
                <div className="p-4 bg-green-500/20 rounded-full border border-green-500/50">
                  <CheckCircle2 size={48} className="text-green-400" />
                </div>
                <div>
                  <h2 className="text-4xl font-bold text-white tracking-wide drop-shadow-md">
                    Patch Successful
                  </h2>
                  <div className="flex items-center gap-4 mt-2">
                    <span className="flex items-center gap-1 text-yellow-400 font-mono text-lg bg-yellow-400/10 px-3 py-1 rounded border border-yellow-400/20">
                      <Star size={16} /> +500 XP
                    </span>
                    <span className="flex items-center gap-1 text-cyan-400 font-mono text-lg bg-cyan-400/10 px-3 py-1 rounded border border-cyan-400/20">
                      <Shield size={16} /> CONFIDENCE UP
                    </span>
                  </div>
                </div>
              </div>

              {diffText && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  transition={{ delay: 0.5, duration: 0.8 }}
                  className="w-full bg-black/80 border border-white/10 rounded-xl overflow-hidden backdrop-blur-md shadow-[0_0_30px_rgba(0,240,255,0.1)]"
                >
                  <div className="bg-white/5 px-4 py-2 border-b border-white/10 font-mono text-xs text-white/50 flex items-center gap-2">
                    <Zap size={14} className="text-cyan-400" /> DEPLOYED_CODE_DIFF
                  </div>
                  <pre className="p-6 font-mono text-sm overflow-x-auto text-green-400 leading-relaxed max-h-64 overflow-y-auto">
                    {diffText}
                  </pre>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </motion.div>
  );
}
