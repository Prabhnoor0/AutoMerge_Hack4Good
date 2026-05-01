"use client";

interface Props {
  logs: string;
}

export function LogViewer({ logs }: Props) {
  const lines = logs.split("\n");

  return (
    <div
      className="rounded-lg overflow-hidden font-mono text-xs max-h-80 overflow-y-auto"
      style={{ background: "var(--bg-primary)", border: "1px solid var(--border-subtle)" }}
    >
      {lines.map((line, i) => {
        const type = getLineType(line);
        return (
          <div
            key={i}
            className="flex px-3 py-0.5 hover:opacity-90"
            style={{
              background:
                type === "error"
                  ? "rgba(239, 68, 68, 0.06)"
                  : type === "pass"
                  ? "rgba(34, 197, 94, 0.04)"
                  : "transparent",
            }}
          >
            <span
              className="w-8 flex-shrink-0 text-right mr-3 select-none"
              style={{ color: "var(--text-muted)" }}
            >
              {i + 1}
            </span>
            <span
              style={{
                color:
                  type === "error"
                    ? "var(--accent-red)"
                    : type === "pass"
                    ? "var(--accent-green)"
                    : type === "warning"
                    ? "var(--accent-amber)"
                    : type === "header"
                    ? "var(--accent-cyan)"
                    : "var(--text-secondary)",
              }}
            >
              {line || "\u00A0"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function getLineType(line: string): "error" | "pass" | "warning" | "header" | "normal" {
  const lower = line.toLowerCase();
  if (lower.includes("error") || lower.includes("failed") || lower.includes("fail") || line.startsWith("E ") || line.startsWith(">"))
    return "error";
  if (lower.includes("passed") || lower.includes("pass") || lower.includes("success"))
    return "pass";
  if (lower.includes("warning") || lower.includes("warn"))
    return "warning";
  if (line.startsWith("===") || line.startsWith("---") || line.startsWith("$"))
    return "header";
  return "normal";
}
