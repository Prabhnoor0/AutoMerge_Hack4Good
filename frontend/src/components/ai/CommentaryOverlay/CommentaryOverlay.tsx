"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bot } from "lucide-react";

export interface CommentaryMessage {
  id: string;
  text: string;
  type?: "info" | "success" | "warning" | "error";
}

// Global event emitter for commentary
type Listener = (msg: CommentaryMessage) => void;
let listeners: Listener[] = [];

export const pushCommentary = (text: string, type: "info" | "success" | "warning" | "error" = "info") => {
  const msg: CommentaryMessage = { id: Math.random().toString(36).substr(2, 9), text, type };
  listeners.forEach(l => l(msg));
};

export function CommentaryOverlay() {
  const [messages, setMessages] = useState<CommentaryMessage[]>([]);

  useEffect(() => {
    const handler = (msg: CommentaryMessage) => {
      setMessages(prev => [...prev.slice(-2), msg]); // Keep only max 3 messages
      
      // Auto dismiss after 4 seconds
      setTimeout(() => {
        setMessages(prev => prev.filter(m => m.id !== msg.id));
      }, 4000);
    };
    listeners.push(handler);
    return () => {
      listeners = listeners.filter(l => l !== handler);
    };
  }, []);

  return (
    <div className="fixed top-8 left-1/2 -translate-x-1/2 z-[100] flex flex-col items-center gap-2 pointer-events-none">
      <AnimatePresence>
        {messages.map((msg) => {
          let glow = "var(--glow-cyan)";
          let color = "var(--accent-cyan)";
          if (msg.type === "success") { glow = "rgba(34,197,94,0.5)"; color = "var(--accent-green)"; }
          if (msg.type === "warning") { glow = "rgba(245,158,11,0.5)"; color = "var(--accent-amber)"; }
          if (msg.type === "error") { glow = "rgba(239,68,68,0.5)"; color = "var(--accent-red)"; }

          return (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: -20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.9 }}
              className="flex items-center gap-3 px-4 py-2 rounded-full bg-black/80 backdrop-blur-md border border-white/10"
              style={{ boxShadow: `0 0 20px ${glow}` }}
            >
              <div className="flex items-center justify-center w-6 h-6 rounded-full" style={{ background: `${color}20` }}>
                <Bot size={14} style={{ color }} />
              </div>
              <span className="text-sm font-mono font-bold tracking-wide" style={{ color: "white" }}>
                {msg.text}
              </span>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
