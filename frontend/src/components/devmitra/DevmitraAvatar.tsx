"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Bot, Sparkles, AlertTriangle, CheckCircle2 } from "lucide-react";

type AvatarState = "idle" | "thinking" | "happy" | "celebration" | "concerned";

interface Props {
  currentState?: AvatarState;
}

export function DevmitraAvatar({ currentState = "idle" }: Props) {
  const [internalState, setInternalState] = useState<AvatarState>(currentState);

  useEffect(() => {
    setInternalState(currentState);
  }, [currentState]);

  // Visual parameters based on state
  let glowColor = "rgba(0, 240, 255, 0.4)";
  let coreColor = "var(--bg-elevated)";
  let borderColor = "var(--accent-cyan)";
  let iconColor = "text-cyan-400";
  let pulseSpeed = 4;
  let floatAnim = { y: [-2, 2, -2] };
  let ringAnim = { scale: [1, 1.05, 1], opacity: [0.3, 0.6, 0.3] };

  if (internalState === "thinking") {
    glowColor = "rgba(168, 85, 247, 0.6)"; // purple
    borderColor = "var(--accent-purple)";
    iconColor = "text-purple-400";
    pulseSpeed = 1.5;
    floatAnim = { y: [-1, 1, -1] };
    ringAnim = { scale: [1, 1.15, 1], opacity: [0.5, 0.8, 0.5] };
  } else if (internalState === "happy" || internalState === "celebration") {
    glowColor = "rgba(34, 197, 94, 0.6)"; // green
    borderColor = "var(--accent-green)";
    iconColor = "text-green-400";
    pulseSpeed = internalState === "celebration" ? 0.5 : 2;
    floatAnim = { y: [-5, 5, -5] };
    ringAnim = { scale: [1, 1.2, 1], opacity: [0.4, 0.9, 0.4] };
  } else if (internalState === "concerned") {
    glowColor = "rgba(245, 158, 11, 0.6)"; // amber
    borderColor = "var(--accent-amber)";
    iconColor = "text-amber-400";
    pulseSpeed = 0.8;
    floatAnim = { y: [0, 1, 0, -1, 0] }; // jitter
    ringAnim = { scale: [1, 1.02, 1], opacity: [0.6, 0.8, 0.6] };
  }

  return (
    <div className="relative flex items-center justify-center w-16 h-16 group">
      
      {/* Outer Glow Ring */}
      <motion.div
        animate={ringAnim}
        transition={{ duration: pulseSpeed, repeat: Infinity, ease: "easeInOut" }}
        className="absolute inset-0 rounded-full blur-md"
        style={{ background: glowColor }}
      />
      
      {/* Dynamic Pulse Ring */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: pulseSpeed * 4, repeat: Infinity, ease: "linear" }}
        className="absolute -inset-1 rounded-full border border-dashed opacity-50"
        style={{ borderColor }}
      />

      {/* Main Avatar Core */}
      <motion.div
        animate={floatAnim}
        transition={{ duration: pulseSpeed, repeat: Infinity, ease: "easeInOut" }}
        className="relative z-10 w-12 h-12 rounded-full flex items-center justify-center border shadow-lg overflow-hidden"
        style={{ background: coreColor, borderColor, boxShadow: `inset 0 0 10px ${glowColor}` }}
      >
        {/* Scanning line effect */}
        {internalState === "thinking" && (
          <motion.div
            animate={{ y: [-24, 24, -24] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            className="absolute left-0 right-0 h-[2px] bg-purple-400 blur-[1px] opacity-70"
          />
        )}
        
        {/* State Icons */}
        {internalState === "idle" && <Bot size={22} className={iconColor} />}
        {internalState === "thinking" && <Bot size={22} className={iconColor} />}
        {internalState === "happy" && <Sparkles size={22} className={iconColor} />}
        {internalState === "celebration" && <CheckCircle2 size={24} className={iconColor} />}
        {internalState === "concerned" && <AlertTriangle size={22} className={iconColor} />}

      </motion.div>
    </div>
  );
}
