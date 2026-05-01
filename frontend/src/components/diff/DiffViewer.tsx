"use client";

import type { Patch } from "@/lib/types";

interface Props {
  patch: Patch;
}

export function DiffViewer({ patch }: Props) {
  const diffLines = parseDiff(patch.diff_text);

  return (
    <div className="space-y-3">
      {/* File header */}
      <div
        className="flex items-center justify-between px-4 py-2.5 rounded-t-lg"
        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border)", borderBottom: "none" }}
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-semibold" style={{ color: "var(--accent-blue)" }}>
            {patch.file_path}
          </span>
          <span
            className="text-[10px] px-1.5 py-0.5 rounded font-medium uppercase"
            style={{ background: "var(--bg-hover)", color: "var(--text-muted)" }}
          >
            {patch.language}
          </span>
        </div>
      </div>

      {/* Diff content */}
      <div
        className="rounded-b-lg overflow-hidden font-mono text-xs"
        style={{ border: "1px solid var(--border)", borderTop: "none" }}
      >
        {diffLines.map((line, i) => (
          <div
            key={i}
            className={`px-4 py-0.5 flex ${
              line.type === "added"
                ? "diff-line-added"
                : line.type === "removed"
                ? "diff-line-removed"
                : line.type === "header"
                ? ""
                : "diff-line-context"
            }`}
            style={{
              background:
                line.type === "header"
                  ? "var(--bg-elevated)"
                  : line.type === "added"
                  ? "rgba(34, 197, 94, 0.08)"
                  : line.type === "removed"
                  ? "rgba(239, 68, 68, 0.08)"
                  : "var(--bg-primary)",
            }}
          >
            <span
              className="w-5 flex-shrink-0 select-none text-right mr-3"
              style={{ color: "var(--text-muted)" }}
            >
              {line.type === "header" ? "" : line.type === "added" ? "+" : line.type === "removed" ? "-" : " "}
            </span>
            <span
              style={{
                color:
                  line.type === "added"
                    ? "var(--accent-green)"
                    : line.type === "removed"
                    ? "var(--accent-red)"
                    : line.type === "header"
                    ? "var(--accent-cyan)"
                    : "var(--text-secondary)",
              }}
            >
              {line.content}
            </span>
          </div>
        ))}
      </div>

      {/* Explanation */}
      {patch.explanation && (
        <div
          className="p-3 rounded-lg text-xs leading-relaxed"
          style={{ background: "var(--glow-blue)", color: "var(--accent-blue)", border: "1px solid rgba(79, 142, 247, 0.15)" }}
        >
          <span className="font-semibold">Fix explanation: </span>
          {patch.explanation}
        </div>
      )}
    </div>
  );
}

interface DiffLine {
  type: "added" | "removed" | "context" | "header";
  content: string;
}

function parseDiff(diffText: string): DiffLine[] {
  if (!diffText) return [];

  return diffText.split("\n").map((line) => {
    if (line.startsWith("+++") || line.startsWith("---")) {
      return { type: "header" as const, content: line };
    }
    if (line.startsWith("@@")) {
      return { type: "header" as const, content: line };
    }
    if (line.startsWith("+")) {
      return { type: "added" as const, content: line.substring(1) };
    }
    if (line.startsWith("-")) {
      return { type: "removed" as const, content: line.substring(1) };
    }
    return { type: "context" as const, content: line.startsWith(" ") ? line.substring(1) : line };
  });
}
