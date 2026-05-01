"use client";

import React, { createContext, useContext, useState, ReactNode, useCallback } from "react";

interface DevmitraContextState {
  code: string;
  filename: string;
  language: string;
  logs: string;
  repoUrl: string;
}

interface DevmitraContextType {
  context: DevmitraContextState;
  setContext: (updates: Partial<DevmitraContextState>) => void;
}

const DevmitraContext = createContext<DevmitraContextType | undefined>(undefined);

export function DevmitraProvider({ children }: { children: ReactNode }) {
  const [context, setContextState] = useState<DevmitraContextState>({
    code: "",
    filename: "",
    language: "auto",
    logs: "",
    repoUrl: "",
  });

  const setContext = useCallback((updates: Partial<DevmitraContextState>) => {
    setContextState((prev) => {
      // Only update if there are actual changes to prevent unnecessary re-renders
      let hasChanges = false;
      for (const key in updates) {
        if (updates[key as keyof DevmitraContextState] !== prev[key as keyof DevmitraContextState]) {
          hasChanges = true;
          break;
        }
      }
      return hasChanges ? { ...prev, ...updates } : prev;
    });
  }, []);

  return (
    <DevmitraContext.Provider value={{ context, setContext }}>
      {children}
    </DevmitraContext.Provider>
  );
}

export function useDevmitra() {
  const ctx = useContext(DevmitraContext);
  if (!ctx) {
    throw new Error("useDevmitra must be used within a DevmitraProvider");
  }
  return ctx;
}
