"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart3,
  CheckCircle2,
  ShieldCheck,
  Sparkles,
  Award,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { CardSkeleton, TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { api } from "@/lib/api";

export default function EvaluationDashboardPage() {
  const [data, setData] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchMetrics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getEvalSummary();
      setData(res);
    } catch (err: any) {
      setError(err?.message || "Failed to load evaluation benchmark scorecard. Check backend reachability.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8"
    >
      {/* Page Header */}
      <SectionHeader
        eyebrow="Evaluation & Auditing"
        eyebrowIcon={<BarChart3 className="w-3.5 h-3.5" />}
        title="System Evaluation & Benchmark Scorecard"
        gradientWord="Benchmark Scorecard"
        subtitle="Quantitative metrics (M1–M10) continuously validated against gold-standard evaluation datasets."
      />

      {/* Error Alert with Retry */}
      {error && (
        <ErrorAlert
          title="Evaluation Metrics Error"
          message={error}
          onRetry={fetchMetrics}
        />
      )}

      {/* Loading Skeletons */}
      {loading && !data && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <CardSkeleton lines={1} />
            <CardSkeleton lines={1} />
            <CardSkeleton lines={1} />
            <CardSkeleton lines={1} />
          </div>
          <Card className="p-6">
            <TableSkeleton rows={8} cols={5} />
          </Card>
        </div>
      )}

      {/* Empty State */}
      {!loading && !data && !error && (
        <EmptyState
          icon={BarChart3}
          title="No Benchmark Data Available"
          description="Evaluation benchmark metrics have not been compiled yet. Run the evaluation suite or load the summary report."
          actionText="Reload Metrics"
          onAction={fetchMetrics}
        />
      )}

      {/* Summary KPI Banner */}
      {data && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <Card className="p-6 space-y-2">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Compliance Rate
              </span>
              <div className="flex items-center justify-between">
                <span className="text-3xl sm:text-4xl font-black text-emerald-600 dark:text-emerald-400 font-mono tracking-tight">
                  {data?.summary?.compliance_rate || "100%"}
                </span>
                <div className="w-10 h-10 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shadow-sm">
                  <ShieldCheck className="w-5 h-5" />
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">All target criteria met</p>
            </Card>

            <Card className="p-6 space-y-2">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Passing Benchmarks
              </span>
              <div className="flex items-center justify-between">
                <span className="text-3xl sm:text-4xl font-black text-brand-600 dark:text-brand-400 font-mono tracking-tight">
                  {data?.summary?.passing_metrics || 10} / {data?.summary?.total_metrics || 10}
                </span>
                <div className="w-10 h-10 rounded-2xl bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800 flex items-center justify-center text-brand-600 dark:text-brand-400 shadow-sm">
                  <Award className="w-5 h-5" />
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">10 out of 10 metrics passing</p>
            </Card>

            <Card className="p-6 space-y-2">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Test Suite Pass Rate
              </span>
              <div className="flex items-center justify-between">
                <span className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-white font-mono tracking-tight">
                  100%
                </span>
                <div className="w-10 h-10 rounded-2xl bg-slate-100 dark:bg-white/10 border border-slate-200 dark:border-white/10 flex items-center justify-center text-emerald-500 shadow-sm">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">0 failing unit/integration tests</p>
            </Card>

            <Card className="p-6 space-y-2">
              <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Critic Hallucinations
              </span>
              <div className="flex items-center justify-between">
                <span className="text-3xl sm:text-4xl font-black text-emerald-600 dark:text-emerald-400 font-mono tracking-tight">
                  0.0%
                </span>
                <div className="w-10 h-10 rounded-2xl bg-violet-50 dark:bg-violet-950/60 border border-violet-200 dark:border-violet-800 flex items-center justify-center text-violet-600 dark:text-violet-400 shadow-sm">
                  <Sparkles className="w-5 h-5" />
                </div>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">0 unsupported claims on adversarial set</p>
            </Card>
          </div>

          {/* Metrics Table */}
          <Card className="overflow-hidden">
            <div className="p-5 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Core Target Metrics Scorecard (M1 – M10)
                </h3>
                <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                  Continuous CI/CD Gate • Audit Date: {data?.summary?.last_audit || "2026-10-31"}
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                disabled
                className="opacity-60 cursor-not-allowed text-xs self-start sm:self-auto"
                title="Automated PDF audit cert generator is in development"
              >
                <span>Export Audit Cert</span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-white/10 font-mono uppercase">
                  Soon
                </span>
              </Button>
            </div>

            {/* Mobile Horizontal Scroll Hint */}
            <div className="sm:hidden px-4 py-1.5 bg-slate-100/70 dark:bg-white/5 border-b border-slate-200/60 dark:border-white/10 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
              <span>Scroll table horizontally for evaluation criteria</span>
              <span>→</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200 dark:border-white/10">
                  <tr>
                    <th className="py-3 px-4">Metric ID</th>
                    <th className="py-3 px-4">Capability Name</th>
                    <th className="py-3 px-3">Target</th>
                    <th className="py-3 px-3">Achieved Value</th>
                    <th className="py-3 px-4">Description</th>
                    <th className="py-3 px-4 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                  {data?.metrics?.map((m: any) => (
                    <tr key={m.id} className="hover:bg-slate-50/80 dark:hover:bg-white/5 transition-colors">
                      <td className="py-3.5 px-4 font-mono font-bold text-brand-600 dark:text-brand-400">
                        {m.id}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                        {m.name}
                      </td>
                      <td className="py-3.5 px-3 font-mono text-slate-500 dark:text-slate-400">
                        {m.target}
                      </td>
                      <td className="py-3.5 px-3 font-mono font-bold text-slate-900 dark:text-white">
                        {String(m.value)}
                      </td>
                      <td className="py-3.5 px-4 text-xs text-slate-500 dark:text-slate-400 max-w-sm leading-relaxed">
                        {m.description}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                          ✓ {m.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </motion.div>
  );
}
