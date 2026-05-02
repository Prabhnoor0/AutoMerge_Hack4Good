"use client";
import { useEffect, useRef, useState, useCallback } from "react";

export function MermaidDiagram({ code, title }: { code: string; title?: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgHtml, setSvgHtml] = useState<string | null>(null);
  const [error, setError] = useState(false);

  const renderDiagram = useCallback(async () => {
    if (!code) return;
    try {
      const mermaid = (await import("mermaid")).default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        themeVariables: {
          primaryColor: "#4f8ef7",
          primaryTextColor: "#e8eaf0",
          primaryBorderColor: "#2a2d3e",
          lineColor: "#5c5f73",
          secondaryColor: "#8b5cf6",
          tertiaryColor: "#161822",
          background: "#161822",
          mainBkg: "#1c1f2e",
          nodeBorder: "#4f8ef7",
          clusterBkg: "#12141c",
          titleColor: "#e8eaf0",
          edgeLabelBackground: "#12141c",
        },
        flowchart: { curve: "basis", padding: 16 },
        sequence: { mirrorActors: false },
        fontFamily: "Inter, system-ui, sans-serif",
      });

      const id = `mermaid-${Math.random().toString(36).slice(2, 10)}`;
      const { svg } = await mermaid.render(id, code);
      setSvgHtml(svg);
    } catch {
      setError(true);
    }
  }, [code]);

  useEffect(() => {
    setSvgHtml(null);
    setError(false);
    renderDiagram();
  }, [renderDiagram]);

  if (error) {
    return (
      <div className="rounded-lg p-4 overflow-auto" style={{ background: "var(--bg-elevated)" }}>
        <pre className="text-xs font-mono whitespace-pre" style={{ color: "var(--text-secondary)" }}>{code}</pre>
      </div>
    );
  }

  return (
    <div className="rounded-xl overflow-hidden border" style={{ borderColor: "var(--border)", background: "var(--bg-elevated)" }}>
      {title && (
        <div className="px-4 py-2 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--accent-blue)" }}>{title}</span>
          <button
            onClick={() => navigator.clipboard.writeText(code)}
            className="text-[10px] px-2 py-1 rounded-md transition-colors"
            style={{ color: "var(--text-muted)", background: "var(--bg-card)" }}
          >
            Copy
          </button>
        </div>
      )}
      {svgHtml ? (
        <div
          ref={containerRef}
          className="p-4 flex justify-center overflow-auto [&_svg]:max-w-full"
          dangerouslySetInnerHTML={{ __html: svgHtml }}
        />
      ) : (
        <div className="p-4 flex justify-center" style={{ minHeight: 80 }}>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--accent-blue)", borderTopColor: "transparent" }} />
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>Rendering diagram…</span>
          </div>
        </div>
      )}
    </div>
  );
}
