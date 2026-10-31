"use client";

import React from "react";
import { motion, type HTMLMotionProps } from "framer-motion";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "cyan";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      loading = false,
      icon,
      className = "",
      disabled,
      ...props
    },
    ref
  ) => {
    const sizeClasses = {
      sm: "px-3 py-1.5 text-xs rounded-xl gap-1.5",
      md: "px-4 py-2 text-sm rounded-xl gap-2",
      lg: "px-5 py-2.5 text-base rounded-xl gap-2.5",
    }[size];

    const variantClasses = {
      primary:
        "relative overflow-hidden bg-gradient-to-r from-brand-600 via-indigo-600 to-violet-600 text-white font-semibold shadow-soft hover:shadow-glow hover:brightness-105 active:brightness-95 border border-white/15",
      cyan:
        "relative overflow-hidden bg-gradient-to-r from-cyan-600 to-brand-600 text-white font-semibold shadow-soft hover:shadow-glow-cyan hover:brightness-105 active:brightness-95 border border-white/15",
      secondary:
        "bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200/90 dark:border-white/10 font-medium hover:bg-slate-50 dark:hover:bg-slate-700/80 shadow-sm hover:border-slate-300 dark:hover:border-white/20 hover:-translate-y-0.5",
      outline:
        "bg-transparent text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-white/15 font-medium hover:bg-slate-100/70 dark:hover:bg-slate-800/60",
      ghost:
        "bg-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100/80 dark:hover:bg-white/5 font-medium",
    }[variant];

    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={`inline-flex items-center justify-center transition-all duration-200 select-none ${sizeClasses} ${variantClasses} ${
          isDisabled ? "opacity-60 cursor-not-allowed transform-none hover:shadow-none hover:translate-y-0" : ""
        } ${className}`}
        {...props}
      >
        {loading ? (
          <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin flex-shrink-0" />
        ) : (
          icon && <span className="flex-shrink-0">{icon}</span>
        )}
        <span>{children}</span>
      </button>
    );
  }
);

Button.displayName = "Button";

