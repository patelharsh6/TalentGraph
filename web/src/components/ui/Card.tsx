"use client";

import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
  glass?: boolean;
}

export function Card({
  children,
  hoverEffect = false,
  glass = true,
  className = "",
  ...props
}: CardProps) {
  return (
    <div
      className={`rounded-[20px] border border-slate-200/80 dark:border-white/10 ${
        glass
          ? "bg-white/80 dark:bg-[#111827]/80 backdrop-blur-md"
          : "bg-white dark:bg-[#111827]"
      } shadow-card-light dark:shadow-card-dark transition-all duration-200 ${
        hoverEffect
          ? "hover:border-brand-500/30 dark:hover:border-brand-400/30 hover:shadow-soft hover:-translate-y-0.5"
          : ""
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

