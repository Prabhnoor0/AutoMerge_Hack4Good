// "use client";

// import { motion } from "framer-motion";
// import { AlertCircle, CheckCircle2, Clock, Loader2, RotateCcw, Bug } from "lucide-react";
// import { formatRelative, confidenceLabel } from "@/lib/utils";
// import { STATUS_COLORS } from "@/lib/types";
// import type { Job } from "@/lib/types";

// interface JobListProps {
//   jobs: Job[];
//   selectedId: string | null;
//   onSelect: (id: string) => void;
// }

// const STATUS_ICONS: Record<string, React.ReactNode> = {
//   queued: <Clock size={14} />,
//   analyzing: <Loader2 size={14} className="animate-spin" />,
//   diagnosing: <Loader2 size={14} className="animate-spin" />,
//   patching: <Loader2 size={14} className="animate-spin" />,
//   validating: <Loader2 size={14} className="animate-spin" />,
//   summarizing: <Loader2 size={14} className="animate-spin" />,
//   retrying: <RotateCcw size={14} className="animate-spin" />,
//   completed: <CheckCircle2 size={14} />,
//   failed: <AlertCircle size={14} />,
// };

// export function JobList({ jobs, selectedId, onSelect }: JobListProps) {
//   return (
//     <>
//       {jobs.map((job, i) => (
//         <motion.button
//           key={job.id}
//           initial={{ opacity: 0, y: 8 }}
//           animate={{ opacity: 1, y: 0 }}
//           transition={{ delay: i * 0.05 }}
//           layout
//           onClick={() => onSelect(job.id)}
//           className="w-full text-left rounded-xl p-3 sm:p-4 transition-all group"
//           style={{
//             background: selectedId === job.id ? "var(--bg-elevated)" : "transparent",
//             border: selectedId === job.id ? "1px solid var(--border)" : "1px solid transparent",
//           }}
//           onMouseEnter={(e) => {
//             if (selectedId !== job.id) e.currentTarget.style.background = "var(--bg-hover)";
//           }}
//           onMouseLeave={(e) => {
//             if (selectedId !== job.id) e.currentTarget.style.background = "transparent";
//           }}
//         >
//           <div className="flex items-start justify-between gap-2">
//             <div className="flex items-center gap-2 min-w-0">
//               <span style={{ color: STATUS_COLORS[job.status] || "var(--text-muted)" }}>
//                 {STATUS_ICONS[job.status] || <Bug size={14} />}
//               </span>
//               <span
//                 className="text-[11px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
//                 style={{
//                   color: STATUS_COLORS[job.status],
//                   background: `${STATUS_COLORS[job.status]}15`,
//                 }}
//               >
//                 {job.status}
//               </span>
//             </div>
//             <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-muted)" }}>
//               {formatRelative(job.created_at)}
//             </span>
//           </div>

//           <p
//             className="text-sm font-medium mt-2 line-clamp-2 leading-snug break-words"
//             style={{ color: "var(--text-primary)" }}
//           >
//             {job.failure_title}
//           </p>

//           <div className="flex items-center gap-3 mt-2.5">
//             <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
//               {job.failure_type}
//             </span>
//             {job.confidence_score > 0 && (
//               <span
//                 className="text-[11px] flex items-center gap-1"
//                 style={{ 
//                   color: job.confidence_score >= 0.8 ? "var(--accent-green)" : 
//                          job.confidence_score >= 0.5 ? "var(--accent-amber)" : 
//                          "var(--accent-red)" 
//                 }}
//               >
//                 <span 
//                   className="inline-block w-1.5 h-1.5 rounded-full" 
//                   style={{ 
//                     background: job.confidence_score >= 0.8 ? "var(--accent-green)" : 
//                                job.confidence_score >= 0.5 ? "var(--accent-amber)" : 
//                                "var(--accent-red)" 
//                   }} 
//                 />
//                 {Math.round(job.confidence_score * 100)}% {confidenceLabel(job.confidence_score)}
//               </span>
//             )}
//             {job.mode === "demo" && (
//               <span
//                 className="text-[10px] px-1.5 py-0.5 rounded font-medium"
//                 style={{ background: "var(--glow-blue)", color: "var(--accent-blue)" }}
//               >
//                 DEMO
//               </span>
//             )}
//           </div>
//         </motion.button>
//       ))}
//     </>
//   );
// }


"use client";

import { motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Loader2,
  RotateCcw,
  Bug,
} from "lucide-react";
import { formatRelative, confidenceLabel } from "@/lib/utils";
import { STATUS_COLORS } from "@/lib/types";
import type { Job } from "@/lib/types";

interface JobListProps {
  jobs: Job[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  queued: <Clock size={14} />,
  analyzing: <Loader2 size={14} className="animate-spin" />,
  diagnosing: <Loader2 size={14} className="animate-spin" />,
  patching: <Loader2 size={14} className="animate-spin" />,
  validating: <Loader2 size={14} className="animate-spin" />,
  summarizing: <Loader2 size={14} className="animate-spin" />,
  retrying: <RotateCcw size={14} className="animate-spin" />,
  completed: <CheckCircle2 size={14} />,
  failed: <AlertCircle size={14} />,
};

function getConfidenceColor(score: number) {
  if (score >= 0.8) return "var(--accent-green)";
  if (score >= 0.5) return "var(--accent-amber)";
  return "var(--accent-red)";
}

export function JobList({ jobs, selectedId, onSelect }: JobListProps) {
  return (
    <div className="space-y-1 p-1">
      {jobs.map((job, i) => {
        const isSelected = selectedId === job.id;
        const statusColor = STATUS_COLORS[job.status] || "var(--text-muted)";
        const confidenceColor =
          job.confidence_score > 0 ? getConfidenceColor(job.confidence_score) : null;

        return (
          <motion.button
            key={job.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            layout
            onClick={() => onSelect(isSelected ? null : job.id)}
            className="w-full text-left rounded-xl p-3 sm:p-4 transition-all group"
            style={{
              background: isSelected ? "var(--bg-elevated)" : "transparent",
              border: isSelected ? "1px solid var(--border)" : "1px solid transparent",
            }}
            onMouseEnter={(e) => {
              if (!isSelected) e.currentTarget.style.background = "var(--bg-hover)";
            }}
            onMouseLeave={(e) => {
              if (!isSelected) e.currentTarget.style.background = "transparent";
            }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span style={{ color: statusColor }}>
                  {STATUS_ICONS[job.status] || <Bug size={14} />}
                </span>

                <span
                  className="text-[11px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded"
                  style={{
                    color: statusColor,
                    background: `${statusColor}15`,
                  }}
                >
                  {job.status}
                </span>
              </div>

              <span className="text-[11px] flex-shrink-0" style={{ color: "var(--text-muted)" }}>
                {formatRelative(job.created_at)}
              </span>
            </div>

            <p
              className="text-sm font-medium mt-2 line-clamp-2 leading-snug break-words"
              style={{ color: "var(--text-primary)" }}
            >
              {job.failure_title}
            </p>

            <div className="flex flex-wrap items-center gap-3 mt-2.5">
              <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
                {job.failure_type}
              </span>

              {job.confidence_score > 0 && confidenceColor && (
                <span
                  className="text-[11px] flex items-center gap-1"
                  style={{ color: confidenceColor }}
                >
                  <span
                    className="inline-block w-1.5 h-1.5 rounded-full"
                    style={{ background: confidenceColor }}
                  />
                  {Math.round(job.confidence_score * 100)}%{" "}
                  {confidenceLabel(job.confidence_score)}
                </span>
              )}

              {job.mode === "demo" && (
                <span
                  className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                  style={{ background: "var(--glow-blue)", color: "var(--accent-blue)" }}
                >
                  DEMO
                </span>
              )}
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}