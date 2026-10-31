"use client";

import { useState } from "react";
import { AlertTriangle, X, Zap } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function UploadWarning() {
  const [dismissed, setDismissed] = useState(false);

  return (
    <AnimatePresence>
      {!dismissed && (
        <motion.div
          initial={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0, marginBottom: 0 }}
          transition={{ duration: 0.25, ease: "easeInOut" }}
          className="overflow-hidden mb-6"
        >
          <div className="relative rounded-2xl border border-amber-300/60 dark:border-amber-500/20 bg-gradient-to-r from-amber-50/90 via-amber-50/60 to-orange-50/70 dark:from-amber-950/30 dark:via-amber-950/20 dark:to-orange-950/20 backdrop-blur-md p-4 sm:p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3 sm:gap-4">
              <div className="flex items-start gap-3">
                {/* Tinted icon square */}
                <div className="w-10 h-10 rounded-xl bg-amber-500/10 dark:bg-amber-400/15 border border-amber-400/30 flex items-center justify-center flex-shrink-0 text-amber-600 dark:text-amber-400">
                  <Zap className="w-5 h-5 fill-amber-500/20" />
                </div>
                <div className="space-y-1">
                  <h4 className="text-sm font-bold text-amber-950 dark:text-amber-200 tracking-tight">
                    Demo Caching Active & Zero-Quota Protection
                  </h4>
                  <p className="text-xs sm:text-[13px] text-amber-800/90 dark:text-amber-300/80 leading-relaxed max-w-3xl">
                    Pre-seeded resumes and job requisitions run with{" "}
                    <strong className="font-semibold text-amber-900 dark:text-amber-100">0 Gemini LLM calls</strong> via deterministic benchmark caches. Uploading custom resumes uses the live parser with rate-limit protection and RFC 7807 error boundaries.
                  </p>
                </div>
              </div>

              {/* Dismiss Button */}
              <button
                onClick={() => setDismissed(true)}
                className="p-1.5 rounded-lg text-amber-700/60 dark:text-amber-400/60 hover:text-amber-900 dark:hover:text-amber-200 hover:bg-amber-200/40 dark:hover:bg-amber-900/40 transition-colors flex-shrink-0"
                aria-label="Dismiss banner"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
