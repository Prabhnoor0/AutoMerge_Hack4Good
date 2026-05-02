"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import type { Job } from "@/lib/types";

interface Props {
  jobs: Job[];
}

export function CodeHealthPlanet({ jobs }: Props) {
  const [healing, setHealing] = useState(false);
  const [prevCompleted, setPrevCompleted] = useState(0);

  const activeJobs = jobs.filter(j => j.status !== "completed");
  const completedJobs = jobs.filter(j => j.status === "completed");
  
  const totalJobs = jobs.length || 1;
  const healthScore = Math.max(0, 100 - (activeJobs.length / totalJobs) * 100);
  
  // Triggers heal animation when completed jobs increase
  useEffect(() => {
    if (completedJobs.length > prevCompleted) {
      setHealing(true);
      setTimeout(() => setHealing(false), 2000);
    }
    setPrevCompleted(completedJobs.length);
  }, [completedJobs.length, prevCompleted]);

  // Visual parameters
  const isCritical = healthScore < 50;
  const isHealthy = healthScore >= 80;

  const planetGlow = isCritical 
    ? "rgba(239, 68, 68, 0.4)" // Red
    : isHealthy 
      ? "rgba(16, 185, 129, 0.4)" // Green
      : "rgba(59, 130, 246, 0.4)"; // Blue

  const coreColor = isCritical 
    ? "radial-gradient(circle at 30% 30%, #f87171, #b91c1c, #450a0a)"
    : isHealthy
      ? "radial-gradient(circle at 30% 30%, #34d399, #10b981, #064e3b)"
      : "radial-gradient(circle at 30% 30%, #60a5fa, #3b82f6, #1e3a8a)";

  return (
    <div className="relative flex flex-col items-center justify-center p-8">
      <div className="relative flex items-center justify-center w-80 h-80">
        {/* Atmospheric Glow */}
        <motion.div
          animate={{ scale: [1, 1.05, 1], opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          className="absolute w-full h-full rounded-full blur-3xl z-0 pointer-events-none"
          style={{ background: planetGlow }}
        />

        {/* Outer HUD Ring */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0 rounded-full z-10"
          style={{ border: "2px dashed rgba(255, 255, 255, 0.1)" }}
        >
          {/* Orbiting Blip */}
          <div className="absolute top-0 left-1/2 w-2 h-2 rounded-full -translate-x-1/2 -translate-y-1/2"
               style={{ background: isHealthy ? "#10b981" : isCritical ? "#ef4444" : "#00f0ff", boxShadow: `0 0 10px ${planetGlow}` }} />
        </motion.div>

        {/* Inner HUD Ring */}
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
          className="absolute rounded-full z-10"
          style={{ width: "75%", height: "75%", border: "2px dotted rgba(0, 240, 255, 0.2)" }}
        />

        {/* Core Sphere */}
        <motion.div
          animate={isCritical ? { scale: [1, 1.02, 0.98, 1.02, 1] } : { scale: [1, 1.02, 1] }}
          transition={{ duration: isCritical ? 0.5 : 4, repeat: Infinity, ease: "easeInOut" }}
          className="relative z-20 w-44 h-44 rounded-full overflow-hidden"
          style={{ 
            background: coreColor, 
            boxShadow: `inset -20px -20px 40px rgba(0,0,0,0.8), inset 10px 10px 20px rgba(255,255,255,0.3), 0 0 50px ${planetGlow}` 
          }}
        >
          {/* Subtle Surface Shimmer */}
          <motion.div 
            animate={{ opacity: [0.2, 0.5, 0.2] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="absolute inset-0 mix-blend-overlay rounded-full"
            style={{ backgroundImage: "radial-gradient(circle at 30% 30%, rgba(255,255,255,0.4), transparent)" }}
          />

          {/* Active Jobs as Core Anomalies */}
          {activeJobs.map((_, i) => (
            <motion.div
              key={i}
              animate={{ rotate: 360 }}
              transition={{ duration: 5 + (i * 1), repeat: Infinity, ease: "linear", delay: i * 0.5 }}
              className="absolute inset-0"
            >
              <div 
                className="absolute w-2 h-2 rounded-full"
                style={{
                  top: `${20 + (i * 15)}%`,
                  left: `${50}%`,
                  background: isCritical ? "#ef4444" : "#00f0ff",
                  boxShadow: `0 0 10px ${isCritical ? 'red' : 'cyan'}`,
                  filter: "blur(1px)"
                }}
              />
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Status Overlay */}
      <div className="mt-8 bg-black/60 backdrop-blur-sm border border-white/10 px-6 py-2 rounded-full z-20 flex items-center gap-3 shadow-xl">
        <span className="text-xs uppercase font-mono tracking-widest text-white/50">Core Health</span>
        <span className="text-sm font-bold font-mono" style={{ color: isCritical ? "#ef4444" : isHealthy ? "#10b981" : "#3b82f6" }}>
          {healthScore.toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
