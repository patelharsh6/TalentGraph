import React from "react";
import { Sparkles } from "lucide-react";

export interface SectionHeaderProps {
  eyebrow?: string;
  eyebrowIcon?: React.ReactNode;
  title: string;
  gradientWord?: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}

export function SectionHeader({
  eyebrow,
  eyebrowIcon = <Sparkles className="w-3.5 h-3.5" />,
  title,
  gradientWord,
  subtitle,
  action,
  className = "",
}: SectionHeaderProps) {
  // If gradientWord is provided, split title and style it
  let titleNode: React.ReactNode = title;
  if (gradientWord && title.includes(gradientWord)) {
    const parts = title.split(gradientWord);
    titleNode = (
      <>
        {parts[0]}
        <span className="bg-gradient-to-r from-brand-600 via-violet-600 to-cyan-500 bg-clip-text text-transparent">
          {gradientWord}
        </span>
        {parts.slice(1).join(gradientWord)}
      </>
    );
  }

  return (
    <div className={`flex flex-col sm:flex-row sm:items-end justify-between gap-4 ${className}`}>
      <div className="space-y-1.5 max-w-2xl">
        {eyebrow && (
          <div className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-brand-600 dark:text-brand-400 bg-brand-50/80 dark:bg-brand-950/40 px-2.5 py-0.5 rounded-full border border-brand-200/60 dark:border-brand-800/40">
            {eyebrowIcon}
            <span>{eyebrow}</span>
          </div>
        )}
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          {titleNode}
        </h1>
        {subtitle && (
          <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 leading-relaxed">
            {subtitle}
          </p>
        )}
      </div>
      {action && <div className="flex-shrink-0 self-start sm:self-auto">{action}</div>}
    </div>
  );
}

