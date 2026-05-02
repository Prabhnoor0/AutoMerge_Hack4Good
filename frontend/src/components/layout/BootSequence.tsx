"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const bootSequence = [
  "Initializing AI Engine...",
  "Loading Code Intelligence...",
  "Analyzing system architecture...",
  "Connecting to Devmitra...",
  "Boot sequence complete."
];

const GlitchStreaks = () => {
  const [blocks, setBlocks] = useState<{ id: number, top: string, left: string, width: string, height: string, opacity: number }[]>([]);

  useEffect(() => {
    let timeout: NodeJS.Timeout;
    const triggerGlitchBlock = () => {
      // Create a small burst of blocks
      const burstSize = Math.floor(Math.random() * 8) + 3; // 3-10 blocks at a time
      const newBlocks = Array.from({ length: burstSize }).map(() => {
        // Concentrate heavily on top 25% and bottom 25%
        const isTop = Math.random() > 0.5;
        const topPos = isTop ? Math.random() * 25 : 75 + Math.random() * 25;
        
        return {
          id: Math.random(),
          top: `${topPos}%`,
          left: `${Math.random() * 90}%`,
          width: `${Math.random() * 10 + 2}%`, // 2% to 12% width
          height: `${Math.random() * 3 + 1}px`, // 1px to 4px height
          opacity: Math.random() * 0.4 + 0.1 // 0.1 to 0.5 opacity (subtle black and white)
        };
      });
      
      setBlocks(newBlocks);
      
      // Clear them quickly for that flicker effect
      setTimeout(() => {
        setBlocks([]);
      }, 30 + Math.random() * 80);

      // trigger next burst quickly but randomly
      timeout = setTimeout(triggerGlitchBlock, 80 + Math.random() * 400);
    };
    
    triggerGlitchBlock();
    return () => clearTimeout(timeout);
  }, []);

  return (
    <div className="absolute inset-0 z-50 pointer-events-none">
      {blocks.map(b => (
        <div
          key={b.id}
          className="absolute bg-white"
          style={{
            top: b.top,
            left: b.left,
            width: b.width,
            height: b.height,
            opacity: b.opacity,
          }}
        />
      ))}
    </div>
  );
};

export function BootSequence() {
  const [isBooting, setIsBooting] = useState(true);
  const [currentLineIndex, setCurrentLineIndex] = useState(0);
  const [displayedText, setDisplayedText] = useState("");
  const [finishedLines, setFinishedLines] = useState<string[]>([]);
  const [finalSweep, setFinalSweep] = useState(false);

  useEffect(() => {
    if (!isBooting || currentLineIndex >= bootSequence.length) return;

    const fullLine = bootSequence[currentLineIndex];
    
    if (displayedText.length < fullLine.length) {
      const timer = setTimeout(() => {
        setDisplayedText(fullLine.slice(0, displayedText.length + 1));
      }, 30 + Math.random() * 20); // Typing speed variance
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(() => {
        setFinishedLines(prev => [...prev, fullLine]);
        setDisplayedText("");
        setCurrentLineIndex(prev => prev + 1);
        
        if (currentLineIndex === bootSequence.length - 1) {
          // Finished the whole sequence
          setTimeout(() => {
            setFinalSweep(true);
            setTimeout(() => setIsBooting(false), 300);
          }, 600);
        }
      }, 300); // Delay between lines
      return () => clearTimeout(timer);
    }
  }, [displayedText, currentLineIndex, isBooting]);

  return (
    <AnimatePresence>
      {isBooting && (
        <motion.div
          key="boot-sequence"
          className="fixed inset-0 z-[9999] flex flex-col items-center justify-center overflow-hidden cyber-scanline-overlay cyber-subtle-shake bg-black"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8, ease: "easeInOut" }}
        >
          {/* Neuron Background Image */}
          <div 
            className="absolute inset-0 z-0 opacity-50 mix-blend-screen" 
            style={{ 
              backgroundImage: "url('/neuron-bg.jpg')", 
              backgroundSize: "cover", 
              backgroundPosition: "center" 
            }} 
          />
          <div className="absolute inset-0 z-0 bg-gradient-to-b from-[#0a0d18]/70 to-[#020204]/90 pointer-events-none" />

          {/* Edge distorion flashes */}
          <div className="absolute inset-0 cyber-edge-glitch-bars cyber-animate-edge-flash pointer-events-none z-10" />

          {/* Glitch Streaks */}
          <GlitchStreaks />

          {/* Final sweep transition */}
          {finalSweep && (
            <motion.div
              className="absolute left-0 w-full h-[10px] bg-white z-[100] shadow-[0_0_30px_#fff,-5px_0_10px_gray,5px_0_10px_gray]"
              initial={{ top: "-10%", opacity: 1 }}
              animate={{ top: "110%", opacity: 0 }}
              transition={{ duration: 0.3, ease: "linear" }}
            />
          )}

          {/* Top Title */}
          <div className="absolute top-20 md:top-24 flex flex-col items-center z-20 w-full px-4">
            <h1 
              className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl tracking-[0.05em] text-[#e0f0ff] cyber-title-intro cyber-title-micro-glitch text-center drop-shadow-lg whitespace-nowrap"
              style={{ lineHeight: "1.1" }}
            >
              DEV VIDYALAYA
            </h1>
          </div>

          {/* Terminal container */}
          <div className="relative z-20 w-full max-w-3xl p-8 mt-48 font-mono">
            {/* Log Output */}
            <div className="space-y-4 min-h-[200px] flex flex-col justify-start text-sm md:text-base text-[var(--cyber-neon-cyan)] opacity-90">
              {finishedLines.map((line, i) => (
                <div key={i} className="flex items-start">
                  <span className="text-white/20 mr-4 select-none shrink-0">{`[SYS-${(i + 1).toString().padStart(2, '0')}]`}</span>
                  <span className={i === bootSequence.length - 1 ? 'text-[var(--cyber-success)] font-bold drop-shadow-[0_0_8px_rgba(0,255,100,0.5)]' : ''}>{line}</span>
                </div>
              ))}
              
              {/* Current typing line */}
              {currentLineIndex < bootSequence.length && (
                <div className="flex items-start">
                  <span className="text-white/20 mr-4 select-none shrink-0">{`[SYS-${(currentLineIndex + 1).toString().padStart(2, '0')}]`}</span>
                  <span>{displayedText}</span>
                  <motion.div
                    animate={{ opacity: [1, 0] }}
                    transition={{ repeat: Infinity, duration: 0.8, ease: "circInOut" }}
                    className="w-2.5 h-5 bg-[var(--cyber-neon-cyan)] ml-1 inline-block shrink-0"
                  />
                </div>
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
