"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface Props {
  isActive: boolean;
  children: React.ReactNode;
}

export function ChaosMode({ isActive, children }: Props) {
  const [glitching, setGlitching] = useState(false);

  useEffect(() => {
    if (!isActive) {
      setGlitching(false);
      return;
    }

    // Random glitch intervals
    const glitchLoop = () => {
      setGlitching(true);
      setTimeout(() => setGlitching(false), 100 + Math.random() * 200);
      
      const nextGlitch = 1000 + Math.random() * 4000;
      if (isActive) {
        timeoutId = setTimeout(glitchLoop, nextGlitch);
      }
    };

    let timeoutId = setTimeout(glitchLoop, 1000);
    return () => clearTimeout(timeoutId);
  }, [isActive]);

  return (
    <div className="relative w-full h-full">
      {/* Glitch Overlay Effect */}
      {isActive && (
        <div className="pointer-events-none fixed inset-0 z-[100] mix-blend-overlay opacity-30">
          <div className="w-full h-full bg-[url('/noise.png')] animate-noise" />
          {glitching && (
            <motion.div 
              className="absolute inset-0 bg-red-500/10"
              initial={{ opacity: 0 }}
              animate={{ opacity: [0.2, 0.8, 0] }}
              transition={{ duration: 0.2 }}
            />
          )}
        </div>
      )}

      {/* Main Content Wrapper */}
      <motion.div
        animate={isActive && glitching ? { 
          x: [-2, 2, -1, 1, 0],
          y: [1, -1, 2, -2, 0],
          filter: ["hue-rotate(90deg) contrast(150%)", "hue-rotate(-90deg) contrast(150%)", "none"]
        } : { x: 0, y: 0, filter: "none" }}
        transition={{ duration: 0.2 }}
        className="w-full h-full"
      >
        {children}
      </motion.div>

      {/* Global CSS for Noise if needed */}
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes noise {
          0%, 100% { transform: translate(0, 0); }
          10% { transform: translate(-5%, -5%); }
          20% { transform: translate(-10%, 5%); }
          30% { transform: translate(5%, -10%); }
          40% { transform: translate(-5%, 15%); }
          50% { transform: translate(-10%, 5%); }
          60% { transform: translate(15%, 0); }
          70% { transform: translate(0, 15%); }
          80% { transform: translate(3%, 35%); }
          90% { transform: translate(-10%, 10%); }
        }
        .animate-noise {
          animation: noise 0.2s infinite;
          background-size: 200px 200px;
        }
      `}} />
    </div>
  );
}
