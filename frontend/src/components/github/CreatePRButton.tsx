"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitPullRequest, Loader2, Check, ExternalLink, AlertCircle,
  GitBranch, GitCommit, GitMerge,
} from "lucide-react";
import { api } from "@/lib/api";

interface Props {
  jobId: string;
  disabled?: boolean;
  token?: string;
  baseBranch?: string;
}

export function CreatePRButton({ jobId, disabled, token, baseBranch }: Props) {
  const [loading, setLoading] = useState(false);
  const [merging, setMerging] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    pr?: { pr_number: number; pr_url: string };
    branch?: { branch: string; url: string };
    commit?: { commit_sha: string };
    is_mock?: boolean;
    error?: string;
  } | null>(null);
  const [merged, setMerged] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleCreate = async () => {
    setShowConfirm(false);
    setLoading(true);
    try {
      if (token) {
        // New per-request flow
        const res = await api.createRepoPR({
          job_id: jobId,
          token,
          base_branch: baseBranch || "main",
        });
        setResult(res);
      } else {
        // Legacy flow (uses global config)
        const res = await api.githubCreatePR(jobId, baseBranch);
        setResult(res);
      }
    } catch (e: any) {
      setResult({ success: false, error: e.message || "Failed to create PR" });
    } finally {
      setLoading(false);
    }
  };

  const handleMerge = async () => {
    if (!token || !result?.pr?.pr_number) return;
    setMerging(true);
    try {
      const res = await api.mergeRepoPR({ job_id: jobId, token });
      if (res.success) {
        setMerged(true);
      }
    } catch (e: any) {
      // Show error but don't reset result
      console.error("Merge failed:", e);
    } finally {
      setMerging(false);
    }
  };

  if (result?.success) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="p-4 rounded-xl space-y-3"
        style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2">
          <Check size={16} style={{ color: "var(--accent-green)" }} />
          <span className="text-sm font-semibold" style={{ color: "var(--accent-green)" }}>
            Pull Request Created
          </span>
          {result.is_mock && (
            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium"
              style={{ background: "var(--bg-elevated)", color: "var(--text-muted)" }}>
              MOCK
            </span>
          )}
        </div>

        <div className="space-y-2 text-xs">
          {result.branch && (
            <div className="flex items-center gap-2">
              <GitBranch size={12} style={{ color: "var(--accent-blue)" }} />
              <span style={{ color: "var(--text-muted)" }}>Branch:</span>
              <span className="font-mono font-medium" style={{ color: "var(--text-primary)" }}>
                {result.branch.branch}
              </span>
            </div>
          )}
          {result.commit && (
            <div className="flex items-center gap-2">
              <GitCommit size={12} style={{ color: "var(--accent-amber)" }} />
              <span style={{ color: "var(--text-muted)" }}>Commit:</span>
              <span className="font-mono font-medium" style={{ color: "var(--text-primary)" }}>
                {result.commit.commit_sha.slice(0, 8)}
              </span>
            </div>
          )}
          {result.pr && (
            <div className="flex items-center gap-2">
              <GitPullRequest size={12} style={{ color: "var(--accent-purple)" }} />
              <span style={{ color: "var(--text-muted)" }}>PR #{result.pr.pr_number}:</span>
              <a
                href={result.pr.pr_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 font-medium hover:underline"
                style={{ color: "var(--accent-blue)" }}
              >
                View on GitHub <ExternalLink size={10} />
              </a>
            </div>
          )}
        </div>

        {/* Merge button */}
        {token && result.pr && !merged && (
          <button
            onClick={handleMerge}
            disabled={merging}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all mt-2"
            style={{
              background: merging ? "var(--bg-elevated)" : "var(--glow-green)",
              color: "var(--accent-green)",
              border: "1px solid rgba(34,197,94,0.2)",
              opacity: merging ? 0.5 : 1,
            }}
          >
            {merging ? (
              <><Loader2 size={12} className="animate-spin" /> Merging...</>
            ) : (
              <><GitMerge size={12} /> Merge PR</>
            )}
          </button>
        )}

        {merged && (
          <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: "var(--accent-green)" }}>
            <Check size={14} /> PR Merged Successfully
          </div>
        )}
      </motion.div>
    );
  }

  if (result && !result.success) {
    return (
      <div className="flex items-center gap-2 p-3 rounded-lg text-xs"
        style={{ background: "var(--glow-red)", color: "var(--accent-red)" }}>
        <AlertCircle size={14} />
        <span className="flex-1">{result.error}</span>
        <button onClick={() => setResult(null)} className="ml-auto underline">Retry</button>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Confirm dialog */}
      <AnimatePresence>
        {showConfirm && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="mb-3 p-3 rounded-xl text-xs space-y-2"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <p className="font-medium" style={{ color: "var(--text-primary)" }}>
              Create a branch, commit the fix, and open a PR?
            </p>
            <p style={{ color: "var(--text-muted)" }}>
              This action will push changes to GitHub. You can review and merge later.
            </p>
            <div className="flex gap-2 pt-1">
              <button
                onClick={handleCreate}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold"
                style={{ background: "linear-gradient(135deg, #4f8ef7, #6366f1)", color: "white" }}
              >
                <GitPullRequest size={12} />
                Confirm
              </button>
              <button
                onClick={() => setShowConfirm(false)}
                className="px-3 py-1.5 rounded-md text-xs font-medium"
                style={{ background: "var(--bg-elevated)", color: "var(--text-secondary)" }}
              >
                Cancel
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <button
        onClick={() => setShowConfirm(true)}
        disabled={disabled || loading}
        className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition-all w-full justify-center"
        style={{
          background: disabled ? "var(--bg-elevated)" : "linear-gradient(135deg, #4f8ef7, #6366f1)",
          color: "white",
          opacity: disabled || loading ? 0.5 : 1,
          boxShadow: disabled || loading ? "none" : "0 4px 16px rgba(79,142,247,0.25)",
        }}
      >
        {loading ? (
          <><Loader2 size={13} className="animate-spin" /> Creating PR...</>
        ) : (
          <><GitPullRequest size={13} /> Create Pull Request</>
        )}
      </button>
    </div>
  );
}
