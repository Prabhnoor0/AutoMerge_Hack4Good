"use client";
import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { Job, JobDetail } from "@/lib/types";

/* ─── useJobs: polls job list ─── */
export function useJobs(pollInterval = 3000) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      const data = await api.listJobs();
      setJobs(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, pollInterval);
    return () => clearInterval(interval);
  }, [fetch, pollInterval]);

  return { jobs, loading, error, refetch: fetch };
}

/* ─── useJobDetail: polls single job detail ─── */
export function useJobDetail(jobId: string | null, pollInterval = 2000) {
  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const completedRef = useRef(false);

  const fetch = useCallback(async () => {
    if (!jobId) return;
    // Stop polling once completed or failed
    if (completedRef.current) return;

    try {
      const data = await api.getJob(jobId);
      setJob(data);
      setError(null);
      if (data.status === "completed" || data.status === "failed") {
        completedRef.current = true;
      }
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    completedRef.current = false;
    setLoading(true);
    setJob(null);
    fetch();
    const interval = setInterval(fetch, pollInterval);
    return () => clearInterval(interval);
  }, [fetch, pollInterval, jobId]);

  return { job, loading, error, refetch: fetch };
}
