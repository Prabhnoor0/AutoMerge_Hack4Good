"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Zap, Play, ChevronDown, GitMerge, Code2, LayoutDashboard, GitFork, GraduationCap, Search, Rocket, Swords, Glasses } from "lucide-react";
import { GitHubDrawer } from "@/components/github/GitHubDrawer";
import { api } from "@/lib/api";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

export function Header() {
  const [demoOpen, setDemoOpen] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [githubOpen, setGithubOpen] = useState(false);
  const pathname = usePathname();
  const router = useRouter();

  const handleDemo = async (scenario: string) => {
    setTriggering(true);
    setDemoOpen(false);
    try {
      const res = await api.triggerDemo(scenario);
      // If not on dashboard, navigate to dashboard with query param or just navigate.
      // But we can also use a global event so the dashboard catches it if we are already there.
      if (pathname !== "/") {
        router.push(`/?demoJobId=${res.job_id}`);
      } else {
        window.dispatchEvent(new CustomEvent("demoTriggered", { detail: res.job_id }));
      }
    } catch (e) {
      console.error("Demo trigger failed:", e);
    } finally {
      setTriggering(false);
    }
  };

  const SCENARIOS = [
    { key: "test_failure", label: "Test Failure", desc: "Assertion error in calculate_total" },
    { key: "build_error", label: "Build Error", desc: "TypeScript compilation failure" },
    { key: "type_error", label: "Type Error", desc: "Missing await + undefined access" },
  ];

  return (
    <header
      className="h-16 flex items-center justify-between px-6 border-b flex-shrink-0"
      style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
    >
      {/* Logo + Nav */}
      <div className="flex items-center gap-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, #4f8ef7, #8b5cf6)",
            boxShadow: "0 0 20px rgba(79, 142, 247, 0.3)",
          }}
        >
          <GitMerge size={18} color="white" strokeWidth={2.5} />
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
            AutoMerge
          </h1>
          <p className="text-[10px] font-medium tracking-wider uppercase" style={{ color: "var(--text-muted)" }}>
            Autonomous Debugger
          </p>
        </div>

        <div className="h-5 w-px mx-1" style={{ background: "var(--border)" }} />

        <nav className="flex items-center gap-1">
          <Link
            href="/"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <LayoutDashboard size={13} />
            Dashboard
          </Link>
          <Link
            href="/workspace"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/workspace" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/workspace" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <Code2 size={13} />
            Workspace
          </Link>
          <Link
            href="/studio"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/studio" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/studio" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <Zap size={13} />
            Studio
          </Link>
          <Link
            href="/classroom"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/classroom" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/classroom" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <GraduationCap size={13} />
            Classroom
          </Link>
          <Link
            href="/repo-explorer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/repo-explorer" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/repo-explorer" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <Search size={13} />
            Devमित्र
          </Link>
          <Link
            href="/deploy"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/deploy" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/deploy" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <Rocket size={13} />
            Deploy
          </Link>
          <Link
            href="/battle"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/battle" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/battle" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <Swords size={13} />
            Battle
          </Link>
          <Link
            href="/ar"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors"
            style={{
              color: pathname === "/ar" ? "var(--text-primary)" : "var(--text-muted)",
              background: pathname === "/ar" ? "var(--bg-elevated)" : "transparent",
            }}
          >
            <Glasses size={13} />
            AR
          </Link>
        </nav>
      </div>

      {/* Status + Actions */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "var(--bg-elevated)" }}>
          <div className="status-dot running" style={{ background: "var(--accent-green)" }} />
          <span className="text-xs font-medium" style={{ color: "var(--text-secondary)" }}>
            System Online
          </span>
        </div>

        {/* Demo trigger */}
        <div className="relative">
          <button
            onClick={() => setDemoOpen(!demoOpen)}
            disabled={triggering}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all"
            style={{
              background: triggering
                ? "var(--bg-elevated)"
                : "linear-gradient(135deg, #4f8ef7, #6366f1)",
              color: "white",
              opacity: triggering ? 0.7 : 1,
            }}
          >
            {triggering ? (
              <>
                <Zap size={14} className="animate-pulse" />
                Running...
              </>
            ) : (
              <>
                <Play size={14} />
                Demo
                <ChevronDown size={14} />
              </>
            )}
          </button>

          {demoOpen && (
            <motion.div
              initial={{ opacity: 0, y: -4, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="absolute right-0 top-12 z-50 w-72 rounded-xl border shadow-2xl overflow-hidden"
              style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
            >
              <div className="p-3 border-b" style={{ borderColor: "var(--border)" }}>
                <p className="text-xs font-semibold" style={{ color: "var(--text-secondary)" }}>
                  DEMO SCENARIOS
                </p>
              </div>
              {SCENARIOS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => handleDemo(s.key)}
                  className="w-full text-left px-4 py-3 transition-colors flex items-start gap-3"
                  style={{ color: "var(--text-primary)" }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
                  onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                >
                  <Zap size={14} className="mt-0.5 flex-shrink-0" style={{ color: "var(--accent-amber)" }} />
                  <div>
                    <p className="text-sm font-medium">{s.label}</p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                      {s.desc}
                    </p>
                  </div>
                </button>
              ))}
            </motion.div>
          )}
        </div>

        {/* GitHub settings */}
        <button
          onClick={() => setGithubOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
          style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}
          onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-hover)")}
          onMouseLeave={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
        >
          <GitFork size={13} />
          GitHub
        </button>
      </div>

      {/* GitHub drawer */}
      <GitHubDrawer open={githubOpen} onClose={() => setGithubOpen(false)} />
    </header>
  );
}
