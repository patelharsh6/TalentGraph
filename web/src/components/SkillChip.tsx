"use client";

import { useState } from "react";
import { CheckCircle2, HelpCircle, Sparkles, X } from "lucide-react";

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
  let catStyle = "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-800";
  if (cat === "soft") {
    catStyle = "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-800";
  } else if (cat === "domain") {
    catStyle = "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800";
  }

  return (
    <div className="relative inline-block">
      <div
        onClick={() => evidence && evidence.length > 0 && setShowEvidence(!showEvidence)}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${catStyle} ${
          evidence && evidence.length > 0 ? "cursor-pointer hover:shadow-sm" : ""
        } transition-all`}
      >
        <span>{name}</span>

        {years !== null && years !== undefined && years > 0 && (
          <span className="text-[10px] opacity-75 font-mono">({years}y)</span>
        )}

        {inferred ? (
          <span
            title="Inferred from related taxonomy concepts"
            className="inline-flex items-center gap-0.5 px-1 py-0.2 rounded text-[9px] bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200"
          >
            <Sparkles className="w-2.5 h-2.5" />
            inferred
          </span>
        ) : (
          <span title="Explicitly mentioned in resume">
            <CheckCircle2 className="w-3 h-3 text-emerald-500" />
          </span>
        )}
      </div>

      {/* Popover Evidence Box */}
      {showEvidence && evidence && evidence.length > 0 && (
        <div className="absolute z-20 mt-1.5 left-0 w-64 p-2.5 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300">
          <div className="font-semibold text-slate-900 dark:text-white mb-1 flex items-center justify-between">
            <span className="flex items-center gap-1">Verbatim Evidence</span>
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-slate-400 font-mono">
                {confidence ? `${Math.round(confidence * 100)}%` : "100%"}
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowEvidence(false);
                }}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5 rounded"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </div>
          <ul className="space-y-1 max-h-32 overflow-y-auto">
            {evidence.map((quote, idx) => (
              <li key={idx} className="italic text-slate-600 dark:text-slate-300 border-l-2 border-indigo-400 pl-1.5">
                "{quote}"
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
