"use client";

import { useId } from "react";

interface ScoreGaugeProps {
  score: number; // 0.0 to 1.0 or 0 to 100
  threshold?: number;
  size?: number;
  showLabel?: boolean;
}

export default function ScoreGauge({
  score,
  threshold = 0.7,
  size = 148,
  showLabel = true,
}: ScoreGaugeProps) {
  const gradientId = useId();

  // Normalize to 0-100
  const normalizedScore = score > 1 ? Math.min(100, Math.max(0, score)) : Math.min(100, Math.max(0, score * 100));
  const normalizedThreshold = threshold > 1 ? threshold : threshold * 100;

  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (normalizedScore / 100) * circumference;

  let stopStart = "#10B981";
  let stopEnd = "#06B6D4";
  let bgFill = "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800";
  let statusText = "Strong Match";

  if (normalizedScore < 50) {
    stopStart = "#F43F5E";
    stopEnd = "#FB923C";
    bgFill = "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800";
    statusText = "Low Alignment";
  } else if (normalizedScore < 75) {
    stopStart = "#F59E0B";
    stopEnd = "#EAB308";
    bgFill = "bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800";
    statusText = "Moderate Fit";
  }

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg className="w-full h-full -rotate-90 transform" viewBox={`0 0 ${size} ${size}`}>
          <defs>
            <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={stopStart} />
              <stop offset="100%" stopColor={stopEnd} />
            </linearGradient>
          </defs>

          {/* Background track circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-100 dark:text-white/10"
            fill="transparent"
          />

          {/* Active gradient progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke={`url(#${gradientId})`}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
            fill="transparent"
          />
        </svg>

        {/* Center score readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-3xl font-black tracking-tight text-slate-900 dark:text-white font-mono">
            {Math.round(normalizedScore)}%
          </span>
          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500 mt-0.5">
            Target {Math.round(normalizedThreshold)}%
          </span>
        </div>
      </div>

      {showLabel && (
        <span className={`mt-2.5 inline-flex items-center px-3 py-0.5 rounded-full text-xs font-semibold border ${bgFill}`}>
          {statusText}
        </span>
      )}
    </div>
  );
}
