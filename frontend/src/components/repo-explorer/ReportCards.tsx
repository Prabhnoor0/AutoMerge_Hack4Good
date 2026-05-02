"use client";
import { useState } from "react";

export function Card({ title, children, accent, collapsible, defaultOpen = true }: {
  title: string; children: React.ReactNode; accent?: string; collapsible?: boolean; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="glass-card overflow-hidden">
      <button onClick={collapsible ? () => setOpen(!open) : undefined}
        className={`w-full text-left px-4 py-3 flex items-center justify-between ${collapsible ? "cursor-pointer" : "cursor-default"}`}
        style={{ borderBottom: open ? "1px solid var(--border)" : "none" }}>
        <h4 className="text-xs font-semibold uppercase tracking-wider" style={{ color: accent || "var(--accent-blue)" }}>{title}</h4>
        {collapsible && <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{open ? "▲" : "▼"}</span>}
      </button>
      {open && <div className="p-4">{children}</div>}
    </div>
  );
}

export function Badge({ text, color }: { text: string; color: string }) {
  return <span className="px-2 py-0.5 rounded-full text-[10px] font-medium" style={{ background: `${color}22`, color }}>{text}</span>;
}

export function ScoreRing({ score, label, size = 64 }: { score: number; label: string; size?: number }) {
  const color = score >= 70 ? "var(--accent-green)" : score >= 40 ? "var(--accent-amber)" : "var(--accent-red)";
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score / 100);
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--bg-elevated)" strokeWidth={4} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={4}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          style={{ transform: "rotate(-90deg)", transformOrigin: "center", transition: "stroke-dashoffset 1s ease" }} />
        <text x="50%" y="50%" textAnchor="middle" dy="0.35em" fill={color} fontSize={size/4} fontWeight="bold">{score}</text>
      </svg>
      <span className="text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>{label}</span>
    </div>
  );
}

export function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="glass-card p-3 text-center">
      <div className="text-xl font-bold" style={{ color }}>{value}</div>
      <p className="text-[10px] font-medium mt-0.5" style={{ color: "var(--text-muted)" }}>{label}</p>
    </div>
  );
}

export function FileImportanceBar({ file }: { file: any }) {
  return (
    <div className="flex items-center gap-2 py-1.5">
      <span className="text-[11px] font-mono truncate flex-1" style={{ color: "var(--text-secondary)" }}>{file.path}</span>
      <div className="w-20 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--bg-elevated)" }}>
        <div className="h-full rounded-full" style={{
          width: `${file.importance}%`,
          background: file.importance >= 70 ? "var(--accent-blue)" : file.importance >= 40 ? "var(--accent-cyan)" : "var(--text-muted)"
        }} />
      </div>
      <span className="text-[10px] w-6 text-right" style={{ color: "var(--text-muted)" }}>{file.importance}</span>
    </div>
  );
}

export function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="text-[10px] px-2 py-1 rounded-md transition-colors"
      style={{ color: copied ? "var(--accent-green)" : "var(--text-muted)", background: "var(--bg-elevated)" }}>
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}
