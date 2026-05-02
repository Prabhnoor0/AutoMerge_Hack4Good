"use client";

import { motion } from "framer-motion";
import { memo } from "react";

export const BugCore = memo(function BugCore({ type, isExpanded }: { type: string, isExpanded: boolean }) {
  const size = isExpanded ? 50 : 12;
  
  let color = "white";
  let anim;
  
  if (type === "glitch") {
    color = "#e0ffff";
    anim = { opacity: [0.7, 1, 0.5, 1, 0.7] };
  } else if (type === "blob") {
    color = "#ffddaa";
    anim = { scale: [1, 1.1, 0.95, 1] };
  } else if (type === "shadow") {
    color = "#e0d0ff";
    anim = { opacity: [0.3, 0.7, 0.3] };
  } else if (type === "teleporting") {
    color = "#cceeff";
    anim = { x: [0, 2, -2, 0], opacity: [0.6, 1, 0.6] };
  } else if (type === "virus") {
    color = "#ffaaaa";
    anim = { scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] };
  }

  return (
    <motion.div
      className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none rounded-full blur-[1px]"
      animate={anim}
      transition={{ duration: type === "glitch" ? 0.3 : 1.5, repeat: Infinity, ease: "easeInOut" }}
      style={{
        width: size,
        height: size,
        background: color,
        boxShadow: `0 0 ${isExpanded ? 40 : 15}px ${color}`
      }}
    />
  );
});
