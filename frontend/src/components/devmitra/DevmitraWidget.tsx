"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, X, Send, Bot, User, Trash2, Minus, Code2, Sparkles, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useDevmitra } from "@/store/DevmitraContext";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "Explain this file",
  "Find the bug",
  "What does this function do?",
  "Suggest a cleaner version"
];

export function DevmitraWidget() {
  const { context } = useDevmitra();
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (text: string = input) => {
    if (!text.trim() || loading) return;

    const userMessage: Message = { role: "user", content: text };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.devmitraChat(text, context, sessionId || undefined);
      if (!sessionId) setSessionId(res.session_id);
      
      setMessages(res.history);
    } catch (e) {
      console.error("Chat error:", e);
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!sessionId) return;
    try {
      await api.devmitraResetSession(sessionId);
      setMessages([]);
    } catch (e) {
      console.error("Reset error:", e);
    }
  };

  const hasContext = !!(context.code || context.repoUrl || context.logs);

  return (
    <>
      {/* Floating Action Button */}
      {!isOpen && (
        <motion.button
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => { setIsOpen(true); setIsMinimized(false); }}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full text-white shadow-2xl"
          style={{
            background: "linear-gradient(135deg, #4f8ef7, #8b5cf6)",
            boxShadow: "0 8px 32px rgba(79, 142, 247, 0.4)",
          }}
        >
          <Sparkles size={18} />
          <span className="text-sm font-semibold pr-1">Chat with Devमित्र</span>
        </motion.button>
      )}

      {/* Chat Drawer/Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ y: 100, opacity: 0, scale: 0.95 }}
            animate={{ 
              y: isMinimized ? "calc(100% - 60px)" : 0, 
              opacity: 1, 
              scale: 1 
            }}
            exit={{ y: 100, opacity: 0, scale: 0.95 }}
            transition={{ type: "spring", bounce: 0.15, duration: 0.4 }}
            className="fixed bottom-6 right-6 z-50 w-[400px] flex flex-col rounded-2xl shadow-2xl border overflow-hidden"
            style={{ 
              height: "600px", 
              maxHeight: "80vh",
              background: "var(--bg-card)", 
              borderColor: "var(--border)",
              boxShadow: "0 24px 48px -12px rgba(0,0,0,0.5)"
            }}
          >
            {/* Header */}
            <div 
              className="flex items-center justify-between px-4 py-3 border-b"
              style={{ background: "var(--bg-secondary)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600">
                  <Sparkles size={14} color="white" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-[var(--text-primary)]">Devमित्र</h3>
                  <p className="text-[10px] text-[var(--text-muted)]">Code Understanding Copilot</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-[var(--text-muted)]">
                {messages.length > 0 && (
                  <button onClick={handleReset} className="p-1.5 hover:bg-[var(--bg-hover)] rounded-md transition-colors" title="Clear Chat">
                    <Trash2 size={14} />
                  </button>
                )}
                <button onClick={() => setIsMinimized(!isMinimized)} className="p-1.5 hover:bg-[var(--bg-hover)] rounded-md transition-colors" title="Minimize">
                  <Minus size={14} />
                </button>
                <button onClick={() => setIsOpen(false)} className="p-1.5 hover:bg-[var(--bg-hover)] rounded-md transition-colors" title="Close">
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Context Badge */}
            <div className="px-4 py-2 border-b flex items-center gap-2 bg-[var(--bg-elevated)]" style={{ borderColor: "var(--border)" }}>
              <Code2 size={12} className="text-[var(--accent-blue)]" />
              <span className="text-[11px] font-medium text-[var(--text-secondary)] truncate">
                {hasContext 
                  ? `Context: ${context.filename || context.repoUrl || 'Pasted Code snippet'}` 
                  : "No code context loaded"}
              </span>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-70">
                  <div className="w-16 h-16 rounded-2xl flex items-center justify-center bg-[var(--bg-elevated)]">
                    <Bot size={24} className="text-[var(--text-muted)]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[var(--text-primary)]">How can I help you code?</p>
                    <p className="text-xs text-[var(--text-muted)] mt-1 max-w-[250px]">
                      {hasContext ? "I see you have code loaded. Ask me to explain it or find bugs!" : "Open the Studio or Workspace to load code context."}
                    </p>
                  </div>
                  
                  {hasContext && (
                    <div className="flex flex-wrap gap-2 justify-center mt-4">
                      {SUGGESTIONS.map(s => (
                         <button 
                          key={s}
                          onClick={() => handleSend(s)}
                          className="px-3 py-1.5 text-[11px] font-medium rounded-full bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:text-white border border-[var(--border)] transition-colors"
                         >
                           {s}
                         </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <>
                  {messages.map((m, i) => (
                    <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${m.role === 'user' ? 'bg-[var(--bg-elevated)]' : 'bg-gradient-to-br from-blue-500 to-purple-600'}`}>
                        {m.role === 'user' ? <User size={12} /> : <Sparkles size={12} color="white" />}
                      </div>
                      <div 
                        className={`px-3.5 py-2.5 rounded-2xl max-w-[80%] text-sm ${
                          m.role === 'user' 
                            ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)] rounded-tr-sm' 
                            : 'bg-[#1a1c23] border border-[var(--border)] text-[var(--text-secondary)] rounded-tl-sm prose prose-invert prose-sm leading-relaxed'
                        }`}
                        dangerouslySetInnerHTML={m.role === 'assistant' ? { __html: m.content.replace(/\n/g, '<br/>') } : undefined}
                      >
                        {m.role === 'user' ? m.content : null}
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex gap-3">
                      <div className="w-7 h-7 rounded-full flex items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600">
                        <Sparkles size={12} color="white" />
                      </div>
                      <div className="px-4 py-3 rounded-2xl bg-[#1a1c23] border border-[var(--border)] rounded-tl-sm flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                        <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>

            {/* Input Area */}
            <div className="p-3 bg-[var(--bg-secondary)] border-t" style={{ borderColor: "var(--border)" }}>
              <form 
                onSubmit={(e) => { e.preventDefault(); handleSend(); }}
                className="flex items-center gap-2 bg-[var(--bg-card)] border rounded-xl p-1 pr-2"
                style={{ borderColor: "var(--border)" }}
              >
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask Devमित्र about your code..."
                  className="flex-1 bg-transparent px-3 py-2 text-sm outline-none text-[var(--text-primary)]"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || loading}
                  className="p-1.5 rounded-lg text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:bg-[var(--bg-elevated)] transition-colors"
                >
                  <Send size={14} />
                </button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
