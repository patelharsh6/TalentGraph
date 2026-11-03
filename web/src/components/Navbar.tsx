"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileText,
  Target,
  Users,
  Search,
  Sparkles,
  GitBranch,
  BarChart3,
  Info,
  Menu,
  X,
  Zap,
} from "lucide-react";
import { ThemeToggle } from "./ui/ThemeToggle";

const NAV_LINKS = [
  { href: "/", label: "Upload & Profile", icon: FileText },
  { href: "/match", label: "Match & Score", icon: Target },
  { href: "/rank", label: "Recruiter Ranking", icon: Users },
  { href: "/search", label: "Talent Search", icon: Search },
  { href: "/coach", label: "Career Coach", icon: Sparkles },
  { href: "/taxonomy", label: "Taxonomy", icon: GitBranch },
  { href: "/evaluation", label: "Evaluation", icon: BarChart3 },
  { href: "/about", label: "About", icon: Info },
];

export default function Navbar() {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-xl bg-white/70 dark:bg-[#0B0F1A]/75 border-b border-slate-200/60 dark:border-white/10 transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-2">
          {/* Brand Logo & Demo Mode Pill */}
          <div className="flex items-center gap-3 flex-shrink-0">
            <Link href="/" className="group flex items-center gap-2.5 font-extrabold text-lg text-slate-900 dark:text-white transition-transform">
              <span className="relative w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-600 to-violet-500 text-white flex items-center justify-center font-mono text-sm font-black shadow-glow group-hover:scale-105 transition-transform duration-200">
                TG
              </span>
              <span className="tracking-tight text-slate-900 dark:text-white">
                Talent<span className="bg-gradient-to-r from-brand-600 to-violet-500 dark:from-brand-400 dark:to-violet-400 bg-clip-text text-transparent">Graph</span>
              </span>
            </Link>

            {/* Demo Mode Badge */}
            <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50/80 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300/80 dark:border-emerald-700/50 shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span>Demo Mode (0 Quota)</span>
            </div>
          </div>

          {/* Desktop Navigation on a single line (>= xl) */}
          <nav className="hidden xl:flex items-center gap-0.5">
            {NAV_LINKS.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={`relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors duration-150 ${
                    isActive
                      ? "text-brand-600 dark:text-brand-300 font-semibold"
                      : "text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/70 dark:hover:bg-white/5"
                  }`}
                >
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className="absolute inset-0 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200/80 dark:border-brand-800/60 -z-10 shadow-sm"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Medium Desktop Compact View (lg to xl) - All 8 links with compact labels */}
          <nav className="hidden lg:flex xl:hidden items-center gap-0.5">
            {NAV_LINKS.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href;
              const shortLabel =
                label === "Recruiter Ranking"
                  ? "Rank"
                  : label === "Evaluation"
                  ? "Eval"
                  : label.split(" ")[0];
              return (
                <Link
                  key={href}
                  href={href}
                  className={`relative flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                    isActive
                      ? "text-brand-600 dark:text-brand-300 font-semibold"
                      : "text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/70 dark:hover:bg-white/5"
                  }`}
                >
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-pill-lg"
                      className="absolute inset-0 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200/80 dark:border-brand-800/60 -z-10 shadow-sm"
                      transition={{ type: "spring", stiffness: 380, damping: 30 }}
                    />
                  )}
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{shortLabel}</span>
                </Link>
              );
            })}
          </nav>

          {/* Right Controls: Theme Toggle & Mobile Menu Button */}
          <div className="flex items-center gap-2">
            <ThemeToggle />

            {/* Mobile Hamburger Button */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 rounded-xl text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle Navigation Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer with smooth framer-motion slide down */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="lg:hidden border-b border-slate-200/80 dark:border-white/10 bg-white/95 dark:bg-[#111827]/95 backdrop-blur-xl px-4 pt-2 pb-4 space-y-1 shadow-card-light overflow-hidden"
          >
            <div className="sm:hidden pb-2 mb-2 border-b border-slate-200 dark:border-white/10 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500">Talent Intelligence</span>
              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>Demo Mode (0 Quota)</span>
              </div>
            </div>
            {NAV_LINKS.map(({ href, label, icon: Icon }) => {
              const isActive = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-brand-50 text-brand-700 dark:bg-brand-950/70 dark:text-brand-300 font-semibold border border-brand-200 dark:border-brand-800/60"
                      : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5"
                  }`}
                >
                  <Icon className="w-4 h-4 text-brand-500" />
                  <span>{label}</span>
                </Link>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
