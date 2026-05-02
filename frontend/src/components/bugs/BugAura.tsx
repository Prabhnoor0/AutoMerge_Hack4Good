"use client";

import { motion } from "framer-motion";
import { memo } from "react";

export const BugAura = memo(function BugAura({ type, isExpanded }: { type: string, isExpanded: boolean }) {
  const size = isExpanded ? 300 : 80;
  
  let color1 = "rgba(168, 85, 247, 0.4)";
  let color2 = "rgba(168, 85, 247, 0.05)";
  let anim;
  let dur = 3;
  
  if (type === "glitch") {
    color1 = "rgba(0, 240, 255, 0.3)";
    color2 = "rgba(255, 255, 255, 0.05)";
    anim = { scale: [1, 1.05, 0.98, 1.05, 1], opacity: [0.5, 0.8, 0.4, 0.7, 0.5] };
    dur = 0.5;
  } else if (type === "blob") {
    color1 = "rgba(255, 120, 0, 0.35)";
    color2 = "rgba(255, 50, 0, 0.05)";
    anim = { scale: [1, 1.15, 0.95, 1.1, 1], opacity: [0.4, 0.6, 0.3, 0.5, 0.4] };
    dur = 4;
  } else if (type === "shadow") {
    color1 = "rgba(80, 40, 220, 0.4)";
    color2 = "rgba(20, 10, 80, 0.1)";
    anim = { scale: [1, 1.1, 1], opacity: [0.2, 0.5, 0.2] };
    dur = 6;
  } else if (type === "teleporting") {
    color1 = "rgba(0, 120, 255, 0.4)";
    color2 = "rgba(0, 40, 255, 0.05)";
    anim = { scale: [1, 1.1, 1], opacity: [0.4, 0.7, 0.4], x: [0, 3, -3, 0] };
    dur = 2;
  } else if (type === "virus") {
    color1 = "rgba(255, 0, 60, 0.4)";
    color2 = "rgba(120, 0, 0, 0.05)";
    anim = { scale: [1, 1.08, 1], opacity: [0.5, 0.9, 0.5] };
    dur = 1.5;
  }

  return (
    <motion.div
      className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none rounded-full"
      animate={anim}
      transition={{ duration: dur, repeat: Infinity, ease: "easeInOut" }}
      style={{
        width: size,
        height: size,
        background: `radial-gradient(circle, ${color1} 0%, ${color2} 50%, transparent 100%)`,
        filter: "blur(15px)"
      }}
    />
  );
});
