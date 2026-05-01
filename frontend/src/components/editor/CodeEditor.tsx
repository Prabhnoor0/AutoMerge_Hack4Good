"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

// Monaco must be loaded client-side only
const Editor = dynamic(() => import("@monaco-editor/react").then((mod) => mod.default), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center" style={{ background: "#1e1e2e" }}>
      <Loader2 size={20} className="animate-spin" style={{ color: "var(--accent-blue)" }} />
    </div>
  ),
});

const LANGUAGE_MAP: Record<string, string> = {
  python: "python",
  py: "python",
  typescript: "typescript",
  ts: "typescript",
  tsx: "typescriptreact",
  javascript: "javascript",
  js: "javascript",
  jsx: "javascriptreact",
  java: "java",
  go: "go",
  rust: "rust",
  cpp: "cpp",
  c: "c",
};

interface Props {
  value: string;
  language: string;
  onChange: (value: string | undefined) => void;
}

export function CodeEditor({ value, language, onChange }: Props) {
  const monacoLang = LANGUAGE_MAP[language] || language;

  return (
    <Editor
      height="100%"
      language={monacoLang}
      value={value}
      onChange={onChange}
      theme="vs-dark"
      options={{
        fontSize: 13,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        lineHeight: 20,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        padding: { top: 16, bottom: 16 },
        renderLineHighlight: "line",
        cursorBlinking: "smooth",
        smoothScrolling: true,
        bracketPairColorization: { enabled: true },
        automaticLayout: true,
        wordWrap: "on",
        tabSize: 4,
        folding: true,
        glyphMargin: false,
        lineNumbersMinChars: 3,
        overviewRulerLanes: 0,
        hideCursorInOverviewRuler: true,
        scrollbar: {
          verticalScrollbarSize: 6,
          horizontalScrollbarSize: 6,
        },
      }}
    />
  );
}
