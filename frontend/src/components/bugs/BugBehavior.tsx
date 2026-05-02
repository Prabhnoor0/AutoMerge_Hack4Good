"use client";

import { motion } from "framer-motion";
import { ReactNode, memo } from "react";

interface Props {
  type: string;
  isExpanded: boolean;
  onClick?: () => void;
  children: ReactNode;
}

export const BugBehavior = memo(function BugBehavior({ type, isExpanded, onClick, children }: Props) {
  let floatAnim: any = { y: [-3, 3, -3] };
  let floatDuration = 4;

  if (type === "glitch" || type === "virus") {
    floatAnim = { y: [-1, 1, -1], x: [-1, 1, -1] };
    floatDuration = 2;
  } else if (type === "shadow") {
    floatAnim = { y: [-6, 6, -6] };
    floatDuration = 7;
  }

  return (
    <motion.div
      onClick={onClick}
      className={`relative flex items-center justify-center w-full h-full ${!isExpanded ? 'cursor-pointer' : ''}`}
      whileHover={!isExpanded ? { scale: 1.05 } : {}}
      whileTap={!isExpanded ? { scale: 0.95 } : {}}
      animate={!isExpanded ? floatAnim : {}}
      transition={{ duration: floatDuration, repeat: Infinity, ease: "easeInOut" }}
      style={{ zIndex: isExpanded ? 50 : 10 }}
    >
      {children}
    </motion.div>
  );
});
