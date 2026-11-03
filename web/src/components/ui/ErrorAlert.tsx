"use client";

import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "./Button";

interface ErrorAlertProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorAlert({
  title = "An Error Occurred",
  message,
  onRetry,
  className = "",
}: ErrorAlertProps) {
  // Strip any accidental stack traces or raw JSON from user display
  let cleanMessage = message;
  if (message.includes("Traceback") || message.includes("File \"")) {
    cleanMessage = "A backend processing exception occurred. Please try again or contact support.";
  } else if (message.startsWith("{") && message.endsWith("}")) {
    try {
      const parsed = JSON.parse(message);
      cleanMessage = parsed.detail || parsed.message || parsed.title || "Operation failed.";
    } catch {
      cleanMessage = "Operation failed. Please try again.";
    }
  }

  return (
    <div
      className={`p-4 sm:p-5 rounded-2xl bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-200 border border-rose-200 dark:border-rose-800 space-y-3 ${className}`}
    >
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-xl bg-rose-500/10 border border-rose-400/30 flex items-center justify-center flex-shrink-0 text-rose-600 dark:text-rose-400">
          <AlertCircle className="w-4 h-4" />
        </div>
        <div className="space-y-1 flex-1">
          <h4 className="text-xs sm:text-sm font-bold text-rose-900 dark:text-rose-100">
            {title}
          </h4>
          <p className="text-xs text-rose-800/90 dark:text-rose-300/90 leading-relaxed">
            {cleanMessage}
          </p>
        </div>
        {onRetry && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRetry}
            icon={<RotateCcw className="w-3.5 h-3.5" />}
            className="text-xs font-semibold text-rose-800 dark:text-rose-200 hover:bg-rose-100 dark:hover:bg-rose-900/40 flex-shrink-0"
          >
            Retry
          </Button>
        )}
      </div>
    </div>
  );
}

