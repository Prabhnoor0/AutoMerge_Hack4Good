"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Target, Zap, Trophy, Shield, Activity, Award } from "lucide-react";
import type { ClassroomReport } from "@/lib/types";

interface Props {
  report: ClassroomReport;
  onClose: () => void;
}

export function BugChallengeOverlay({ report, onClose }: Props) {
  const [phase, setPhase] = useState<"intro" | "challenge" | "success" | "fail">("intro");
  const [score, setScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(30);
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null);

  // Generate fake questions based on the report to make it a game without backend changes
  const options = [
    report.why_it_matters,
    "It causes a memory leak that crashes the entire server.",
    "It introduces a severe cross-site scripting vulnerability.",
    "It blocks the main thread, causing UI freezes."
  ].sort(() => Math.random() - 0.5);

  const correctAnswer = options.indexOf(report.why_it_matters);

  useEffect(() => {
    if (phase === "challenge" && timeLeft > 0) {
      const t = setTimeout(() => setTimeLeft(prev => prev - 1), 1000);
      return () => clearTimeout(t);
    } else if (phase === "challenge" && timeLeft === 0) {
      setPhase("fail");
    }
  }, [phase, timeLeft]);

  const handleSelect = (idx: number) => {
    setSelectedAnswer(idx);
    if (idx === correctAnswer) {
      setScore(timeLeft * 10 + 500); // XP calculation
      setTimeout(() => setPhase("success"), 1000);
    } else {
      setTimeout(() => setPhase("fail"), 1000);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md overflow-hidden p-4"
    >
      <div className="absolute top-6 right-6">
        <button onClick={onClose} className="p-2 bg-white/10 rounded-full hover:bg-white/20 transition">
          <X className="text-white" />
        </button>
      </div>

      <div className="relative w-full max-w-3xl flex flex-col items-center">
        
        {/* Top HUD */}
        {phase === "challenge" && (
          <motion.div initial={{ y: -50, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="absolute -top-16 left-0 right-0 flex justify-between items-center px-4">
            <div className="flex items-center gap-2 bg-cyan-900/40 border border-cyan-500/30 px-4 py-2 rounded-xl text-cyan-400 font-mono text-lg font-bold">
              <Zap size={20} /> XP: {score}
            </div>
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl font-mono text-lg font-bold border ${timeLeft < 10 ? 'bg-red-900/40 border-red-500/50 text-red-400 animate-pulse' : 'bg-white/5 border-white/10 text-white'}`}>
              <Activity size={20} /> 00:{timeLeft.toString().padStart(2, '0')}
            </div>
          </motion.div>
        )}

        <AnimatePresence mode="wait">
          {/* INTRO PHASE */}
          {phase === "intro" && (
            <motion.div key="intro" exit={{ scale: 0.8, opacity: 0 }} className="text-center">
              <div className="w-32 h-32 bg-cyan-500/20 rounded-full mx-auto flex items-center justify-center border border-cyan-400 shadow-[0_0_50px_rgba(0,240,255,0.3)] animate-pulse">
                <Target size={64} className="text-cyan-400" />
              </div>
              <h2 className="text-4xl font-black mt-8 text-white tracking-widest uppercase">
                Anomaly Detected
              </h2>
              <p className="mt-4 text-cyan-200 text-lg max-w-xl">
                System analysis found an recurring pattern: <span className="text-white font-bold">{report.title}</span>. 
                Identify the critical failure mode before the timer runs out.
              </p>
              <button 
                onClick={() => setPhase("challenge")}
                className="mt-8 px-8 py-4 bg-cyan-500 text-black font-bold font-mono text-xl uppercase rounded hover:bg-cyan-400 transition hover:shadow-[0_0_30px_rgba(0,240,255,0.5)] hover:scale-105 active:scale-95"
              >
                Initiate Sequence
              </button>
            </motion.div>
          )}

          {/* CHALLENGE PHASE */}
          {phase === "challenge" && (
            <motion.div key="challenge" initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 1.1, opacity: 0 }} className="w-full">
              <div className="bg-[#0f1219] border border-white/10 p-8 rounded-2xl shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50" />
                
                <h3 className="text-sm font-mono text-cyan-400 uppercase tracking-widest mb-4">
                  // Case Evidence
                </h3>
                
                {report.evidence.length > 0 && (
                  <pre className="p-4 bg-black/50 border border-white/5 rounded-lg text-sm text-gray-300 font-mono mb-8 whitespace-pre-wrap max-h-48 overflow-y-auto">
                    {report.evidence.join("\n\n")}
                  </pre>
                )}

                <h3 className="text-xl font-bold text-white mb-6">
                  Why does this vulnerability critically compromise system integrity?
                </h3>

                <div className="grid gap-4">
                  {options.map((opt, idx) => {
                    const isSelected = selectedAnswer === idx;
                    const isRight = isSelected && idx === correctAnswer;
                    const isWrong = isSelected && idx !== correctAnswer;

                    let bgClass = "bg-white/5 hover:bg-white/10 border-white/10";
                    if (isRight) bgClass = "bg-green-500/20 border-green-500 text-green-300 shadow-[0_0_20px_rgba(34,197,94,0.3)]";
                    if (isWrong) bgClass = "bg-red-500/20 border-red-500 text-red-300 animate-shake";

                    return (
                      <button
                        key={idx}
                        disabled={selectedAnswer !== null}
                        onClick={() => handleSelect(idx)}
                        className={`text-left p-4 rounded-xl border transition-all duration-300 ${bgClass}`}
                      >
                        {opt}
                      </button>
                    )
                  })}
                </div>
              </div>
            </motion.div>
          )}

          {/* SUCCESS PHASE */}
          {phase === "success" && (
            <motion.div key="success" initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-center">
              <div className="relative">
                <motion.div animate={{ rotate: 360 }} transition={{ duration: 10, repeat: Infinity, ease: "linear" }} className="absolute -inset-10 border-[1px] border-dashed border-green-500/50 rounded-full" />
                <div className="w-40 h-40 bg-green-500/20 rounded-full mx-auto flex items-center justify-center border border-green-400 shadow-[0_0_80px_rgba(34,197,94,0.4)]">
                  <Trophy size={80} className="text-green-400 drop-shadow-[0_0_20px_rgba(34,197,94,1)]" />
                </div>
              </div>
              
              <h2 className="text-5xl font-black mt-12 text-white uppercase tracking-widest drop-shadow-md">
                Threat Neutralized
              </h2>
              
              <div className="flex items-center justify-center gap-6 mt-8">
                <div className="bg-green-900/30 border border-green-500/30 px-6 py-4 rounded-xl flex flex-col items-center">
                  <span className="text-green-500/70 text-xs font-mono uppercase tracking-widest">XP Earned</span>
                  <span className="text-3xl font-bold text-green-400">+{score}</span>
                </div>
                <div className="bg-yellow-900/30 border border-yellow-500/30 px-6 py-4 rounded-xl flex flex-col items-center">
                  <span className="text-yellow-500/70 text-xs font-mono uppercase tracking-widest">Badge Unlocked</span>
                  <span className="flex items-center gap-2 text-xl font-bold text-yellow-400"><Award size={24}/> Debug Master</span>
                </div>
              </div>

              <button 
                onClick={onClose}
                className="mt-12 px-8 py-3 bg-white/10 hover:bg-white/20 text-white font-bold font-mono text-sm uppercase rounded transition"
              >
                Return to Mission Control
              </button>
            </motion.div>
          )}

          {/* FAIL PHASE */}
          {phase === "fail" && (
            <motion.div key="fail" initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="text-center">
              <div className="w-40 h-40 bg-red-500/20 rounded-full mx-auto flex items-center justify-center border border-red-500 shadow-[0_0_80px_rgba(255,0,0,0.4)]">
                <Shield size={80} className="text-red-500" />
              </div>
              <h2 className="text-5xl font-black mt-8 text-white uppercase tracking-widest drop-shadow-md">
                System Compromised
              </h2>
              <p className="mt-4 text-red-200 text-lg">
                The anomaly breached the firewall. Correct answer was:
              </p>
              <div className="mt-4 p-4 bg-red-900/30 border border-red-500/30 rounded-xl text-red-100 max-w-xl mx-auto">
                {report.why_it_matters}
              </div>
              
              <button 
                onClick={() => {
                  setPhase("challenge");
                  setSelectedAnswer(null);
                  setTimeLeft(30);
                }}
                className="mt-8 px-8 py-3 bg-red-500 hover:bg-red-400 text-white font-bold font-mono text-sm uppercase rounded transition mr-4"
              >
                Retry Simulation
              </button>
              <button 
                onClick={onClose}
                className="mt-8 px-8 py-3 bg-white/10 hover:bg-white/20 text-white font-bold font-mono text-sm uppercase rounded transition"
              >
                Abort
              </button>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </motion.div>
  );
}
