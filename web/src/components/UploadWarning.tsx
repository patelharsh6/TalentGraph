"use client";

import { useState } from "react";
import { AlertTriangle, X, ShieldCheck } from "lucide-react";

export default function UploadWarning() {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="bg-amber-50 dark:bg-amber-950/40 border-l-4 border-amber-400 p-3 sm:p-4 rounded-r-lg mb-6 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs sm:text-sm text-amber-900 dark:text-amber-200">
            <p className="font-semibold">Demo Caching Active & Free-Tier Quota Protection</p>
            <p className="mt-0.5 text-amber-800 dark:text-amber-300">
              Sample resumes and jobs are pre-cached and run with <strong>0 Gemini LLM calls</strong>. Uploading custom resumes uses the backend parser with rate-limit protection and RFC 7807 error boundaries.
            </p>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-amber-500 hover:text-amber-800 dark:text-amber-400 p-1"
          aria-label="Dismiss banner"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

