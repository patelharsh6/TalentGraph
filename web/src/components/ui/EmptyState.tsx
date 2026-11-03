"use client";

import { ReactNode } from "react";
import { LucideIcon } from "lucide-react";
import { Button } from "./Button";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  actionIcon?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionText,
  onAction,
  actionIcon,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`p-10 sm:p-14 rounded-2xl border border-dashed border-slate-200 dark:border-white/10 bg-slate-50/50 dark:bg-white/[0.02] text-center flex flex-col items-center justify-center space-y-4 ${className}`}
    >
      <div className="w-12 h-12 rounded-2xl bg-brand-50 dark:bg-brand-950/60 border border-brand-200/80 dark:border-brand-800/60 flex items-center justify-center text-brand-600 dark:text-brand-400 shadow-sm">
        <Icon className="w-6 h-6" />
      </div>
      <div className="space-y-1.5 max-w-md">
        <h3 className="text-base font-bold text-slate-900 dark:text-white">{title}</h3>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
          {description}
        </p>
      </div>
      {actionText && onAction && (
        <div className="pt-2">
          <Button variant="secondary" size="sm" onClick={onAction} icon={actionIcon}>
            {actionText}
          </Button>
        </div>
      )}
    </div>
  );
}

