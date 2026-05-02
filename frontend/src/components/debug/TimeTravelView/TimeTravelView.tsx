"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, Rewind, FastForward, Activity } from "lucide-react";
import type { Job, Summary } from "@/lib/types";

interface Props {
  jobs: Job[];
  onClose?: () => void;
}

export function TimeTravelView({ jobs, onClose }: Props) {
  // Sort jobs by creation time (assuming id or created_at correlates with time)
  const sortedJobs = [...jobs].reverse(); // newest last for timeline
  
  const [currentIndex, setCurrentIndex] = useState(sortedJobs.length - 1);
  const [isPlaying, setIsPlaying] = useState(false);

  const currentJob = sortedJobs[currentIndex];

  const handleScrub = (index: number) => {
    setCurrentIndex(index);
    setIsPlaying(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#0a0f18] text-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-black/50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-500/20 rounded-lg border border-blue-500/30">
            <Clock size={20} className="text-blue-400" />
          </div>
          <div>
            <h2 className="font-mono text-lg font-bold text-blue-400 uppercase tracking-widest">
              Time Travel Debugging
            </h2>
            <p className="text-[10px] text-white/50 uppercase tracking-wider">
              Temporal System State Analysis
            </p>
          </div>
        </div>
        {onClose && (
          <button onClick={onClose} className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-md text-xs font-bold transition">
            Exit Simulation
          </button>
        )}
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-hidden relative flex">
        {/* State View */}
        <AnimatePresence mode="wait">
          {currentJob ? (
            <motion.div 
              key={currentIndex}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex-1 p-8 overflow-y-auto"
            >
              <div className="max-w-4xl mx-auto space-y-6">
                <div className="flex items-start justify-between bg-black/40 border border-white/10 p-6 rounded-2xl">
                  <div>
                    <span className="text-[10px] text-blue-400 font-mono uppercase tracking-widest border border-blue-400/30 bg-blue-400/10 px-2 py-1 rounded">
                      Snapshot {currentIndex + 1} / {sortedJobs.length}
                    </span>
                    <h3 className="text-2xl font-bold mt-4">{currentJob.failure_title}</h3>
                    <p className="text-sm text-white/60 mt-1">Status: <span className="uppercase text-white">{currentJob.status}</span></p>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-white/40 uppercase">Job ID</span>
                    <p className="font-mono text-xs">{currentJob.id.split("-")[0]}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  {/* Summary */}
                  {(currentJob as any).summary && (
                    <div className="bg-black/40 border border-white/10 p-6 rounded-2xl">
                      <h4 className="text-xs uppercase text-white/40 mb-3 flex items-center gap-2"><Activity size={14}/> System Assessment</h4>
                      <p className="text-sm text-white/80 leading-relaxed">{(currentJob as any).summary?.root_cause || (currentJob as any).summary?.title || 'Analysis pending...'}</p>
                      <div className="mt-4 p-3 bg-white/5 rounded border border-white/5">
                        <span className="text-[10px] uppercase text-white/40 block mb-1">Proposed Fix</span>
                        <p className="text-xs font-mono text-cyan-200">{(currentJob as any).summary?.fix_description || 'N/A'}</p>
                      </div>
                    </div>
                  )}

                  {/* Logs/Trace */}
                  {(currentJob as any).reasoning_trace && (
                    <div className="bg-black/40 border border-white/10 p-6 rounded-2xl">
                      <h4 className="text-xs uppercase text-white/40 mb-3">Neural Trace</h4>
                      <pre className="text-xs font-mono text-white/60 bg-black/50 p-4 rounded-lg border border-white/5 overflow-x-auto">
                        {(currentJob as any).reasoning_trace}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-white/40 font-mono text-sm">
              No temporal data available.
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Scrubber / Timeline */}
      <div className="h-32 bg-black/80 border-t border-white/10 p-6 flex flex-col justify-center">
        <div className="flex items-center gap-4 mb-4 justify-center">
          <button 
            onClick={() => handleScrub(Math.max(0, currentIndex - 1))}
            disabled={currentIndex === 0}
            className="p-2 bg-white/5 hover:bg-white/10 rounded disabled:opacity-30"
          >
            <Rewind size={16} />
          </button>
          <div className="font-mono text-xs text-blue-400 w-24 text-center">
            T-{sortedJobs.length - currentIndex - 1}
          </div>
          <button 
            onClick={() => handleScrub(Math.min(sortedJobs.length - 1, currentIndex + 1))}
            disabled={currentIndex === sortedJobs.length - 1}
            className="p-2 bg-white/5 hover:bg-white/10 rounded disabled:opacity-30"
          >
            <FastForward size={16} />
          </button>
        </div>

        <div className="relative w-full max-w-4xl mx-auto h-2 bg-white/10 rounded-full cursor-pointer flex items-center">
          {sortedJobs.map((_, idx) => (
            <div 
              key={idx}
              onClick={() => handleScrub(idx)}
              className={`absolute w-3 h-3 rounded-full -mt-0.5 transition-all duration-300 ${idx === currentIndex ? 'bg-blue-400 scale-150 shadow-[0_0_10px_#60a5fa]' : idx < currentIndex ? 'bg-blue-900' : 'bg-white/20'}`}
              style={{ left: `${(idx / Math.max(1, sortedJobs.length - 1)) * 100}%`, transform: 'translateX(-50%)' }}
            />
          ))}
          <div 
            className="absolute left-0 top-0 bottom-0 bg-blue-500/50 rounded-full transition-all duration-300 pointer-events-none" 
            style={{ width: `${(currentIndex / Math.max(1, sortedJobs.length - 1)) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
