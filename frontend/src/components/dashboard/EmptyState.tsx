"use client";

import { Inbox } from "lucide-react";

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: "var(--bg-elevated)" }}
      >
        <Inbox size={24} style={{ color: "var(--text-muted)" }} />
      </div>
      <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
        No fix jobs yet
      </p>
      <p className="text-xs mt-1 max-w-[200px]" style={{ color: "var(--text-muted)" }}>
        Click the Demo button to see the autonomous debugging agent in action
      </p>
    </div>
  );
}
