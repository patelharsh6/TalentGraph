"use client";

import { useState } from "react";
import { CheckCircle2, Sparkles, X, Quote } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface SkillChipProps {
  name: string;
  category?: string | null;
  proficiency?: number | null;
  years?: number | null;
  inferred?: boolean | null;
  confidence?: number | null;
  evidence?: string[] | null;
}

export default function SkillChip({
  name,
  category = "technical",
  proficiency = 3,
  years,
  inferred = false,
  confidence,
  evidence,
}: SkillChipProps) {
  const [showEvidence, setShowEvidence] = useState(false);

  const cat = (category || "technical").toLowerCase();
  let catStyle =
    "bg-brand-50/80 text-brand-700 border-brand-200/80 dark:bg-brand-950/40 dark:text-brand-300 dark:border-brand-800/60";
  if (cat === "soft") {
    catStyle =
      "bg-violet-50/80 text-violet-700 border-violet-200/80 dark:bg-violet-950/40 dark:text-violet-300 dark:border-violet-800/60";
  } else if (cat === "domain" || cat === "business") {
    catStyle =
      "bg-emerald-50/80 text-emerald-700 border-emerald-200/80 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800/60";
  } else if (cat === "tools") {
    catStyle =
      "bg-cyan-50/80 text-cyan-800 border-cyan-200/80 dark:bg-cyan-950/40 dark:text-cyan-300 dark:border-cyan-800/60";
  }

  const hasQuotes = evidence && evidence.length > 0;

  return (
    <div className="relative inline-block">
      <div
        onClick={() => hasQuotes && setShowEvidence(!showEvidence)}
        className={`group inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${catStyle} ${
          hasQuotes ? "cursor-pointer hover:shadow-sm hover:scale-[1.02]" : ""
        } transition-all duration-150 select-none`}
      >
        <span>{name}</span>

        {years !== null && years !== undefined && years > 0 && (
          <span className="text-[10px] opacity-70 font-mono">({years}y)</span>
        )}

        {inferred ? (
          <span
            title="Inferred from related taxonomy concepts"
            className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded-full text-[9px] bg-slate-200/80 text-slate-700 dark:bg-slate-700/80 dark:text-slate-200 font-medium"
          >
            <Sparkles className="w-2.5 h-2.5 text-brand-500" />
            inferred
          </span>
        ) : (
          <span title="Explicitly mentioned in resume">
            <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
          </span>
        )}
      </div>

      {/* Popover Evidence Box with motion */}
      <AnimatePresence>
        {showEvidence && hasQuotes && (
          <motion.div
            initial={{ opacity: 0, y: 4, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 4, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute z-30 mt-2 left-0 w-72 p-3 bg-white/95 dark:bg-[#111827]/95 backdrop-blur-xl rounded-2xl shadow-xl border border-slate-200 dark:border-white/10 text-xs text-slate-700 dark:text-slate-300 space-y-2"
          >
            <div className="font-semibold text-slate-900 dark:text-white flex items-center justify-between border-b border-slate-100 dark:border-white/10 pb-1.5">
              <span className="flex items-center gap-1.5 text-xs">
                <Quote className="w-3.5 h-3.5 text-brand-500" />
                <span>Verbatim Grounding</span>
              </span>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-400 font-mono font-medium">
                  {confidence ? `${Math.round(confidence * 100)}%` : "100%"}
                </span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowEvidence(false);
                  }}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5 rounded-md hover:bg-slate-100 dark:hover:bg-white/10 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
            <ul className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
              {evidence.map((quote, idx) => (
                <li
                  key={idx}
                  className="italic text-[11px] text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-white/5 p-2 rounded-xl border-l-2 border-brand-500 leading-relaxed"
                >
                  "{quote}"
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
