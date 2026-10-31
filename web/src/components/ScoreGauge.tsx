"use client";

interface ScoreGaugeProps {
  score: number; // 0.0 to 1.0 or 0 to 100
  threshold?: number;
  size?: number;
  showLabel?: boolean;
}

export default function ScoreGauge({
  score,
  threshold = 0.7,
  size = 140,
  showLabel = true,
}: ScoreGaugeProps) {
  // Normalize to 0-100
  const normalizedScore = score > 1 ? Math.min(100, Math.max(0, score)) : Math.min(100, Math.max(0, score * 100));
  const normalizedThreshold = threshold > 1 ? threshold : threshold * 100;

  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (normalizedScore / 100) * circumference;

  let color = "text-emerald-500 stroke-emerald-500";
  let bgFill = "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300";
  let statusText = "Strong Match";

  if (normalizedScore < 50) {
    color = "text-rose-500 stroke-rose-500";
    bgFill = "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300";
    statusText = "Low Alignment";
  } else if (normalizedScore < 75) {
    color = "text-amber-500 stroke-amber-500";
    bgFill = "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300";
    statusText = "Moderate Fit";
  }

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg className="w-full h-full -rotate-90 transform" viewBox={`0 0 ${size} ${size}`}>
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-slate-100 dark:text-slate-800"
            fill="transparent"
          />
          {/* Active progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={`${color} transition-all duration-1000 ease-out`}
            fill="transparent"
          />
        </svg>

        {/* Center score readout */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white font-mono">
            {Math.round(normalizedScore)}%
          </span>
          <span className="text-[11px] font-medium text-slate-500 dark:text-slate-400">
            Target {Math.round(normalizedThreshold)}%
          </span>
        </div>
      </div>

      {showLabel && (
        <span className={`mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${bgFill}`}>
          {statusText}
        </span>
      )}
    </div>
  );
}

