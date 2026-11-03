import Link from "next/link";
import { Sparkles } from "lucide-react";

export default function Footer() {
  return (
    <footer className="relative mt-auto border-t border-slate-200/60 dark:border-white/10 bg-white/40 dark:bg-[#0B0F1A]/40 backdrop-blur-md py-8 transition-colors">
      {/* Thin gradient accent line at the top */}
      <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-brand-500/40 to-transparent" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500 dark:text-slate-400">
          {/* Left: Branding & Version */}
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              TalentGraph Enterprise Pipeline
            </span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-medium bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 border border-slate-200/80 dark:border-white/10">
              v0.1.0
            </span>
            <span className="hidden md:inline text-slate-300 dark:text-slate-700">•</span>
            <span className="hidden md:inline">FastAPI & Next.js 14 Semantic Engine</span>
          </div>

          {/* Right: Quick Links */}
          <div className="flex items-center gap-6">
            <Link
              href="/about"
              className="relative py-0.5 text-slate-600 dark:text-slate-300 hover:text-brand-600 dark:hover:text-white transition-colors after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[1px] after:bg-brand-500 after:scale-x-0 hover:after:scale-x-100 after:transition-transform"
            >
              Architecture
            </Link>
            <Link
              href="/evaluation"
              className="relative py-0.5 text-slate-600 dark:text-slate-300 hover:text-brand-600 dark:hover:text-white transition-colors after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[1px] after:bg-brand-500 after:scale-x-0 hover:after:scale-x-100 after:transition-transform"
            >
              Benchmarks
            </Link>
            <a
              href="/healthz"
              target="_blank"
              rel="noreferrer"
              className="relative py-0.5 text-slate-600 dark:text-slate-300 hover:text-brand-600 dark:hover:text-white transition-colors after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[1px] after:bg-brand-500 after:scale-x-0 hover:after:scale-x-100 after:transition-transform flex items-center gap-1.5"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
              <span>System Health</span>
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

