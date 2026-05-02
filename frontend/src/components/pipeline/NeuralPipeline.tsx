"use client";

import { motion } from "framer-motion";
import { useMemo } from "react";
import { Shield, Brain, FileCode, CheckCircle2, Zap } from "lucide-react";

interface Props {
  currentStatus: string;
}

const PIPELINE_STEPS = [
  { id: "queued", label: "SCAN", icon: Zap },
  { id: "analyzing", label: "ANALYZE", icon: Brain },
  { id: "patching", label: "FIX", icon: FileCode },
  { id: "validating", label: "VALIDATE", icon: Shield },
  { id: "completed", label: "DEPLOY", icon: CheckCircle2 }
];

export function NeuralPipeline({ currentStatus }: Props) {
  // Map internal status to pipeline step
  const statusIndexMap: Record<string, number> = {
    queued: 0,
    analyzing: 1,
    diagnosing: 1,
    patching: 2,
    validating: 3,
    summarizing: 4,
    completed: 4,
    failed: -1 // handled separately
  };

  const currentIndex = statusIndexMap[currentStatus] ?? 0;
  const isFailed = currentStatus === "failed";

  return (
    <div className="w-full flex justify-center items-center py-10 relative">
      <div className="relative flex items-center justify-between w-full max-w-4xl px-8">
        
        {/* Background Connecting Line */}
        <div className="absolute left-[10%] right-[10%] top-1/2 -translate-y-1/2 h-[2px] bg-white/10 z-0" />

        {/* Active Progress Line (Heartbeat) */}
        <motion.div 
          className="absolute left-[10%] top-1/2 -translate-y-1/2 h-[40px] z-0"
          initial={{ width: "0%" }}
          animate={{ width: `${Math.max(0, Math.min(100, (currentIndex / (PIPELINE_STEPS.length - 1)) * 80))}%` }}
          transition={{ duration: 1, ease: "easeInOut" }}
          style={{ 
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='120' height='40' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 20 L 40 20 L 45 5 L 55 35 L 60 20 L 120 20' stroke='%2300f0ff' stroke-width='2' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
            backgroundRepeat: "repeat-x",
            backgroundPosition: "left center",
            filter: "drop-shadow(0 0 4px #00f0ff)"
          }}
        />

        {PIPELINE_STEPS.map((step, index) => {
          const isCompleted = index < currentIndex;
          const isActive = index === currentIndex && !isFailed;
          const isCurrentFailed = index === currentIndex && isFailed;

          let glowColor = "var(--text-muted)";
          let blobColor = "transparent";
          let pulseClass = "";
          let iconColor = "text-white/40";
          let animation = {};

          if (isCompleted) {
            glowColor = "rgba(0, 240, 255, 0.4)";
            blobColor = "rgba(59, 130, 246, 0.3)"; // Deep blue for completed
            iconColor = "text-cyan-400";
            animation = { scale: 1, opacity: 1 };
          } else if (isActive) {
            glowColor = "rgba(0, 240, 255, 0.8)";
            blobColor = "rgba(168, 85, 247, 0.4)"; // Purple for active
            iconColor = "text-white";
            pulseClass = "animate-pulse";
            animation = { scale: [1, 1.1, 1], filter: ["brightness(1)", "brightness(1.5)", "brightness(1)"] };
          } else if (isCurrentFailed) {
            glowColor = "rgba(255, 50, 50, 0.8)";
            blobColor = "rgba(239, 68, 68, 0.4)";
            iconColor = "text-red-400";
            animation = { x: [-2, 2, -2, 2, 0], filter: "hue-rotate(90deg)" };
          } else {
            animation = { scale: 0.9, opacity: 0.5 };
          }

          const Icon = step.icon;

          return (
            <div key={step.id} className="relative z-10 flex flex-col items-center gap-4">
              <div className="relative">
                {/* Outer Aura (Blob) */}
                <motion.div
                  animate={isActive ? { scale: [1, 1.3, 1], opacity: [0.3, 0.6, 0.3] } : {}}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute inset-0 rounded-full blur-xl pointer-events-none"
                  style={{ background: isActive || isCompleted ? blobColor : "transparent", width: "200%", height: "200%", left: "-50%", top: "-50%" }}
                />

                {/* Node Core */}
                <motion.div
                  animate={animation as any}
                  transition={isActive ? { duration: 1.5, repeat: Infinity } : { duration: 0.3 }}
                  className={`relative w-14 h-14 rounded-full flex items-center justify-center border-2 border-white/10 ${pulseClass}`}
                  style={{
                    background: isActive ? "var(--bg-elevated)" : isCompleted ? "var(--glow-cyan)" : "var(--bg-card)",
                    boxShadow: isActive ? `0 0 10px ${glowColor}, inset 0 0 5px ${glowColor}` : isCompleted ? `0 0 5px ${glowColor}` : "none",
                    borderColor: isActive || isCompleted ? "rgba(0, 240, 255, 0.4)" : "rgba(255, 255, 255, 0.1)"
                  }}
                >
                  <Icon size={20} className={iconColor} />
                </motion.div>
              </div>

              {/* Label */}
              <div className="text-[10px] font-mono tracking-widest uppercase font-bold" style={{ color: isActive || isCompleted ? "white" : "rgba(255,255,255,0.3)" }}>
                {step.label}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
