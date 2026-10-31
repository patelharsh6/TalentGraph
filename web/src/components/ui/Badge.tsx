import React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "brand" | "violet" | "cyan" | "emerald" | "amber" | "rose" | "slate";
  size?: "sm" | "md";
  dot?: boolean;
}

export function Badge({
  children,
  variant = "brand",
  size = "sm",
  dot = false,
  className = "",
  ...props
}: BadgeProps) {
  const sizeClasses = {
    sm: "px-2 py-0.5 text-[11px] gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5",
  }[size];

  const variantClasses = {
    brand:
      "bg-brand-50 text-brand-700 border-brand-200/80 dark:bg-brand-950/60 dark:text-brand-300 dark:border-brand-800/60",
    violet:
      "bg-violet-50 text-violet-700 border-violet-200/80 dark:bg-violet-950/60 dark:text-violet-300 dark:border-violet-800/60",
    cyan:
      "bg-cyan-50 text-cyan-800 border-cyan-200/80 dark:bg-cyan-950/60 dark:text-cyan-300 dark:border-cyan-800/60",
    emerald:
      "bg-emerald-50 text-emerald-700 border-emerald-200/80 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800/60",
    amber:
      "bg-amber-50 text-amber-800 border-amber-200/80 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800/60",
    rose:
      "bg-rose-50 text-rose-700 border-rose-200/80 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800/60",
    slate:
      "bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/80 dark:text-slate-300 dark:border-white/10",
  }[variant];

  const dotClasses = {
    brand: "bg-brand-500",
    violet: "bg-violet-500",
    cyan: "bg-cyan-500",
    emerald: "bg-emerald-500",
    amber: "bg-amber-500",
    rose: "bg-rose-500",
    slate: "bg-slate-400",
  }[variant];

  return (
    <span
      className={`inline-flex items-center font-medium border rounded-full ${sizeClasses} ${variantClasses} ${className}`}
      {...props}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotClasses}`} />}
      {children}
    </span>
  );
}

