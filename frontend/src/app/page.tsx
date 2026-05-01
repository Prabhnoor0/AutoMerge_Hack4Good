"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { JobList } from "@/components/dashboard/JobList";
import { JobDetailPanel } from "@/components/dashboard/JobDetailPanel";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { useJobs, useJobDetail } from "@/hooks/useJobs";

export default function DashboardPage() {
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const { jobs, loading, refetch } = useJobs(2500);
  const { job: selectedJob, loading: jobLoading } = useJobDetail(selectedJobId);

  const handleDemoTriggered = (jobId: string) => {
    setSelectedJobId(jobId);
    refetch();
  };

  useEffect(() => {
    const handleEvent = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail) {
        handleDemoTriggered(customEvent.detail);
      }
    };
    window.addEventListener("demoTriggered", handleEvent);
    return () => window.removeEventListener("demoTriggered", handleEvent);
  }, [refetch]);

  // Check URL params for demoJobId when coming from another page
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const demoJobId = params.get("demoJobId");
    if (demoJobId) {
      handleDemoTriggered(demoJobId);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  return (
    <div className="h-full flex flex-col" style={{ background: "var(--bg-primary)" }}>
      <main className="flex-1 flex overflow-hidden">
        {/* Left: Job list */}
        <motion.aside
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-[380px] flex-shrink-0 border-r flex flex-col overflow-hidden"
          style={{ borderColor: "var(--border)", background: "var(--bg-secondary)" }}
        >
          <div className="p-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
            <h2 className="text-sm font-semibold" style={{ color: "var(--text-secondary)" }}>
              FIX JOBS
            </h2>
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}
            >
              {jobs.length}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <AnimatePresence mode="popLayout">
              {loading && jobs.length === 0 ? (
                <LoadingSkeleton />
              ) : jobs.length === 0 ? (
                <EmptyState />
              ) : (
                <JobList
                  jobs={jobs}
                  selectedId={selectedJobId}
                  onSelect={setSelectedJobId}
                />
              )}
            </AnimatePresence>
          </div>
        </motion.aside>

        {/* Right: Detail panel */}
        <div className="flex-1 overflow-y-auto">
          <AnimatePresence mode="wait">
            {selectedJob ? (
              <motion.div
                key={selectedJob.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <JobDetailPanel job={selectedJob} loading={jobLoading} />
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="h-full flex items-center justify-center"
              >
                <div className="text-center">
                  <div
                    className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
                    style={{ background: "var(--bg-elevated)" }}
                  >
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5">
                      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
                    Select a job to view details
                  </p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    Or trigger a demo to see AutoMerge in action
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-2">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-20 rounded-xl animate-pulse"
          style={{ background: "var(--bg-elevated)" }}
        />
      ))}
    </div>
  );
}
