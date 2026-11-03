"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Target,
  Sparkles,
  ArrowRight,
  EyeOff,
  CheckCircle2,
  XCircle,
  FileEdit,
  ShieldAlert,
} from "lucide-react";
import ScoreGauge from "@/components/ScoreGauge";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Skeleton, TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { SAMPLE_CANDIDATES, SAMPLE_JOBS } from "@/data/samples";
import { api, toText, type MatchResult } from "@/lib/api";

const PRESETS = [
  { id: "balanced", label: "Balanced (60%)", threshold: 0.60 },
  { id: "precision", label: "Strict (75%)", threshold: 0.75 },
  { id: "recall", label: "Broad (45%)", threshold: 0.45 },
  { id: "executive", label: "Leadership (80%)", threshold: 0.80 },
];

function MatchContent() {
  const searchParams = useSearchParams();
  const [candidates, setCandidates] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedCandId, setSelectedCandId] = useState<string>("");
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [customJobText, setCustomJobText] = useState<string>("");
  const [showCustomJob, setShowCustomJob] = useState<boolean>(false);
  const [blind, setBlind] = useState<boolean>(false);
  const [threshold, setThreshold] = useState<number>(0.60);
  const [preset, setPreset] = useState<string>("balanced");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);

  // Fetch candidates and jobs from backend on load
  const loadInitialData = async () => {
    const paramCandId = searchParams?.get("candidate_id") || "";
    const paramJobId = searchParams?.get("job_id") || "";

    try {
      const [cands, loadedJobs] = await Promise.allSettled([
        api.listCandidates(),
        api.listJobs(),
      ]);

      if (cands.status === "fulfilled" && cands.value && cands.value.length > 0) {
        setCandidates(cands.value);
        const foundC = paramCandId && cands.value.find((c: any) => c.id === paramCandId);
        setSelectedCandId(foundC ? paramCandId : cands.value[0].id);
      } else {
        const fallbackCands = SAMPLE_CANDIDATES.map((sc, i) => ({
          id: `00000000-0000-0000-0000-00000000000${i + 1}`,
          name: sc.name,
          title: sc.title,
        }));
        setCandidates(fallbackCands);
        setSelectedCandId(fallbackCands[0].id);
      }

      if (loadedJobs.status === "fulfilled" && loadedJobs.value && loadedJobs.value.length > 0) {
        setJobs(loadedJobs.value);
        const foundJ = paramJobId && loadedJobs.value.find((j: any) => j.id === paramJobId);
        setSelectedJobId(foundJ ? paramJobId : loadedJobs.value[0].id);
      } else {
        setJobs(SAMPLE_JOBS as any);
        setSelectedJobId(SAMPLE_JOBS[0].id);
      }
    } catch {
      const fallbackCands = SAMPLE_CANDIDATES.map((sc, i) => ({
        id: `00000000-0000-0000-0000-00000000000${i + 1}`,
        name: sc.name,
        title: sc.title,
      }));
      setCandidates(fallbackCands);
      setSelectedCandId(fallbackCands[0].id);
      setJobs(SAMPLE_JOBS as any);
      setSelectedJobId(SAMPLE_JOBS[0].id);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, [searchParams]);

  const handleRunMatch = async (forceBlind?: boolean) => {
    const isBlindMode = typeof forceBlind === "boolean" ? forceBlind : blind;
    if (!selectedCandId) {
      setError("Please select a candidate first.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const matchPayload: any = {
        candidate_id: selectedCandId,
        threshold,
        preset: preset !== "custom" ? preset : undefined,
      };

      const selectedJob = jobs.find((j) => j.id === selectedJobId) || SAMPLE_JOBS.find((j) => j.id === selectedJobId);

      if (customJobText.trim()) {
        matchPayload.job = {
          title: selectedJob ? selectedJob.title : "Custom Role",
          description: customJobText.trim(),
        };
      } else if (selectedJobId && !selectedJobId.startsWith("sample-")) {
        matchPayload.job_id = selectedJobId;
      } else {
        matchPayload.job = {
          title: selectedJob ? selectedJob.title : "Target Role",
          description: selectedJob ? (selectedJob.description || selectedJob.raw_text) : "Software Engineer",
        };
      }

      const result = await api.match(matchPayload, isBlindMode);
      setMatchResult(result);
    } catch (err: any) {
      setError(err?.message || "Failed to calculate match score. Check backend reachability.");
      setMatchResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handlePresetChange = (presetId: string) => {
    setPreset(presetId);
    const p = PRESETS.find((x) => x.id === presetId);
    if (p) {
      const newThresh = p.threshold;
      setThreshold(newThresh);
      if (matchResult) {
        setMatchResult({
          ...matchResult,
          threshold: newThresh,
          preset: presetId,
          is_match: matchResult.score >= newThresh,
        });
      }
    }
  };

  const handleSliderChange = (newVal: number) => {
    setThreshold(newVal);
    const matchedPreset = PRESETS.find((x) => Math.abs(x.threshold - newVal) < 0.01);
    const presetName = matchedPreset ? matchedPreset.id : "custom";
    setPreset(presetName);
    if (matchResult) {
      setMatchResult({
        ...matchResult,
        threshold: newVal,
        preset: presetName,
        is_match: matchResult.score >= newVal,
      });
    }
  };

  const handleToggleBlind = (isBlind: boolean) => {
    setBlind(isBlind);
    if (matchResult && selectedCandId && (selectedJobId || customJobText)) {
      handleRunMatch(isBlind);
    }
  };

  const activeCandidate = candidates.find((c) => c.id === selectedCandId);
  const activeJob = jobs.find((j) => j.id === selectedJobId);

  const displayCandidateName = blind
    ? `Candidate #ANON-${selectedCandId.slice(0, 8).toUpperCase()}`
    : toText(activeCandidate?.name, "Selected Candidate");

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8"
    >
      {/* Page Header */}
      <SectionHeader
        eyebrow="Explainable Rubric Engine"
        eyebrowIcon={<Target className="w-3.5 h-3.5" />}
        title="Explainable Candidate Matching"
        gradientWord="Candidate Matching"
        subtitle="Taxonomy-grounded semantic comparison with transparent credit breakdown and blind screening compliance."
      />

      {/* Control Panel Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Candidate Selector */}
        <Card className="p-6 space-y-4">
          <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
            1. Select Candidate
          </label>
          <select
            value={selectedCandId}
            onChange={(e) => setSelectedCandId(e.target.value)}
            className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 cursor-pointer font-medium"
          >
            {candidates.map((c, i) => (
              <option key={c.id} value={c.id}>
                {blind ? `Candidate #${i + 1} (Masked Profile)` : toText(c.name, `Candidate #${i + 1}`)} — {toText(c.title, "Professional")}
              </option>
            ))}
          </select>

          {/* Blind Screening Toggle */}
          <div className="pt-3 border-t border-slate-100 dark:border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-violet-50 dark:bg-violet-950/60 border border-violet-200 dark:border-violet-800 flex items-center justify-center text-violet-600 dark:text-violet-400">
                <EyeOff className="w-4 h-4" />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                  Blind Screening Mode
                </p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Redacts demographic & academic proxies
                </p>
              </div>
            </div>
            <input
              type="checkbox"
              checked={blind}
              onChange={(e) => handleToggleBlind(e.target.checked)}
              className="w-4 h-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500 cursor-pointer"
            />
          </div>
        </Card>

        {/* Target Job Role */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
              2. Target Job Role
            </label>
            <button
              type="button"
              onClick={() => setShowCustomJob(!showCustomJob)}
              className="text-xs text-brand-600 dark:text-brand-400 font-semibold hover:underline flex items-center gap-1"
            >
              <FileEdit className="w-3 h-3" />
              <span>{showCustomJob ? "Use Requisitions" : "Paste Custom JD"}</span>
            </button>
          </div>

          {!showCustomJob ? (
            <select
              value={selectedJobId}
              onChange={(e) => {
                setSelectedJobId(e.target.value);
                setCustomJobText("");
              }}
              className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 cursor-pointer font-medium"
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {toText(j.title, "Requisition")}
                </option>
              ))}
            </select>
          ) : (
            <textarea
              rows={3}
              value={customJobText}
              onChange={(e) => setCustomJobText(e.target.value)}
              placeholder="Paste custom job title & requirements here..."
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none font-mono"
            />
          )}

          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            {jobs.length} requisitions loaded • 0 Gemini quota on pre-seeded roles
          </p>
        </Card>

        {/* Threshold & Preset */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
              3. Preset & Threshold
            </label>
            <span className="font-mono text-brand-600 dark:text-brand-400 text-xs font-bold">
              Cutoff: {Math.round(threshold * 100)}%
            </span>
          </div>

          {/* Preset Buttons */}
          <div className="grid grid-cols-2 gap-2">
            {PRESETS.map((p) => {
              const isActive = preset === p.id;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handlePresetChange(p.id)}
                  className={`px-2.5 py-1.5 text-xs rounded-xl border font-semibold transition-all duration-150 ${
                    isActive
                      ? "bg-brand-50 text-brand-700 border-brand-500 dark:bg-brand-950/70 dark:text-brand-300 dark:border-brand-600 shadow-sm"
                      : "bg-white dark:bg-white/5 border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-white/20"
                  }`}
                >
                  {p.label}
                </button>
              );
            })}
          </div>

          <input
            type="range"
            min={0.4}
            max={0.95}
            step={0.05}
            value={threshold}
            onChange={(e) => handleSliderChange(parseFloat(e.target.value))}
            className="w-full accent-brand-600 cursor-pointer"
          />

          <Button
            onClick={() => handleRunMatch()}
            loading={loading}
            icon={<Target className="w-4 h-4" />}
            size="md"
            variant="primary"
            className="w-full"
          >
            Calculate Match Score
          </Button>
        </Card>
      </div>

      {/* Error state with Retry */}
      {error && (
        <ErrorAlert
          title="Matching Engine Error"
          message={error}
          onRetry={() => handleRunMatch()}
        />
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-6">
          <Card className="p-8">
            <div className="flex flex-col sm:flex-row items-center gap-8">
              <Skeleton className="w-36 h-36 rounded-full" />
              <div className="space-y-3 flex-1">
                <Skeleton className="h-6 w-48 rounded-md" />
                <Skeleton className="h-4 w-72 rounded-md" />
                <div className="flex gap-2 pt-2">
                  <Skeleton className="h-5 w-24 rounded-full" />
                  <Skeleton className="h-5 w-20 rounded-full" />
                </div>
              </div>
            </div>
          </Card>
          <TableSkeleton rows={5} cols={6} />
        </div>
      )}

      {/* Empty State before running match */}
      {!loading && !matchResult && !error && (
        <EmptyState
          icon={Target}
          title="No Match Analysis Calculated"
          description="Select a candidate and target job requisition from the options above, then click 'Calculate Match Score' to compute an explainable taxonomy-grounded breakdown."
          actionText="Calculate Match Score"
          onAction={() => handleRunMatch()}
        />
      )}

      {/* Match Results Display */}
      {!loading && matchResult && (
        <div className="space-y-6">
          {/* Blind Screening Notice Banner */}
          {blind && (
            <div className="p-4 rounded-2xl bg-violet-50/80 dark:bg-violet-950/40 border border-violet-200 dark:border-violet-800/60 flex items-center gap-3">
              <EyeOff className="w-5 h-5 text-violet-600 dark:text-violet-400 flex-shrink-0" />
              <div className="space-y-0.5">
                <p className="text-xs font-bold text-violet-900 dark:text-violet-200">
                  Blind Screening Active (Demographic Proxies Redacted)
                </p>
                <p className="text-[11px] text-violet-700 dark:text-violet-300">
                  Candidate name, academic institutions, and graduation years are redacted to eliminate demographic bias.
                </p>
              </div>
            </div>
          )}

          {/* Hero Score Card */}
          <Card className="p-6 sm:p-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-8">
              <div className="flex flex-col sm:flex-row items-center gap-8">
                <ScoreGauge
                  score={matchResult.score}
                  threshold={matchResult.threshold}
                  size={150}
                />
                <div className="text-center sm:text-left space-y-2">
                  <div className="flex items-center justify-center sm:justify-start gap-2">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        matchResult.is_match
                          ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700"
                          : "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-300 dark:border-rose-700"
                      }`}
                    >
                      {matchResult.is_match ? "✓ Meets Role Threshold" : "✗ Below Minimum Threshold"}
                    </span>
                    <span className="text-xs font-mono text-slate-500">
                      Score: {Math.round(matchResult.score * 100)}% vs Threshold: {Math.round(matchResult.threshold * 100)}%
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    {displayCandidateName}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Target Role: <strong className="text-slate-800 dark:text-slate-200">{toText(activeJob?.title, "Requisition")}</strong>
                  </p>

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-400">
                      Preset: {matchResult.preset || preset}
                    </span>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-400">
                      Latency: {String((matchResult.meta as any)?.latency_ms || 12)}ms
                    </span>
                    {blind && (
                      <Badge variant="violet" dot>
                        Blind Evaluated
                      </Badge>
                    )}
                    <Link
                      href={`/coach?candidate_id=${selectedCandId}&job_id=${selectedJobId}`}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline pl-2"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Career Coach Plan</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>

              {/* Gap Summary Card */}
              <div className="p-5 rounded-2xl bg-slate-50 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 w-full md:w-80 space-y-2.5">
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Gap Analysis Summary
                </h4>
                {matchResult.gaps && matchResult.gaps.length > 0 ? (
                  <ul className="space-y-1.5 text-xs max-h-36 overflow-y-auto">
                    {matchResult.gaps.map((gap: any, i: number) => (
                      <li key={i} className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400 font-medium">
                        <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>{gap.skill_name || gap.skill_slug}</span>
                        {gap.required && (
                          <span className="text-[10px] font-bold uppercase text-rose-500">(Required)</span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>No critical gaps detected!</span>
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Mathematical Score Formula Breakdown */}
          {matchResult.components && (
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 p-5 bg-slate-50/80 dark:bg-white/5 rounded-2xl border border-slate-200/80 dark:border-white/10">
              <div className="space-y-1">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  1. Skill Score (70%)
                </span>
                <p className="text-xl font-extrabold text-brand-600 dark:text-brand-400 font-mono">
                  {Math.round((matchResult.components.skill_score || 0) * 100)}%
                </p>
                <p className="text-[11px] text-slate-400">Sum of requirement credits below</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  2. Experience Score (30%)
                </span>
                <p className="text-xl font-extrabold text-indigo-600 dark:text-indigo-400 font-mono">
                  {Math.round((matchResult.components.experience_score || 0) * 100)}%
                </p>
                <p className="text-[11px] text-slate-400">Seniority & duration alignment</p>
              </div>

              <div className="space-y-1">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  3. Missing Skills Penalty
                </span>
                <p className="text-xl font-extrabold text-rose-600 dark:text-rose-400 font-mono">
                  -{Math.round((matchResult.components.penalty || 0) * 100)}%
                </p>
                <p className="text-[11px] text-slate-400">Missing required items (imp ≥ 4)</p>
              </div>

              <div className="space-y-1 sm:border-l sm:border-slate-200 dark:sm:border-white/10 sm:pl-4">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Final Match Score
                </span>
                <p className="text-xl font-extrabold text-slate-900 dark:text-white font-mono">
                  {Math.round(matchResult.score * 100)}%
                </p>
                <p className="text-[11px] text-slate-400">
                  {matchResult.is_match ? "Passes" : "Fails"} threshold ({Math.round(matchResult.threshold * 100)}%)
                </p>
              </div>
            </div>
          )}

          {/* "Why This Score" Breakdown Table */}
          <Card className="overflow-hidden">
            <div className="p-5 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  "Why This Score" — Detailed Requirement Breakdown
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Each requirement receives credit weighted by importance; contributions sum directly to the Skill Score.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Link href={`/coach?candidate_id=${selectedCandId}&job_id=${selectedJobId}`}>
                  <Button variant="secondary" size="sm" icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}>
                    Coach Skill Gaps
                  </Button>
                </Link>
                <Button
                  variant="outline"
                  size="sm"
                  disabled
                  className="opacity-60 cursor-not-allowed text-xs"
                  title="PDF / CSV export is in active development"
                >
                  <span>Export Report</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-white/10 font-mono uppercase">
                    Soon
                  </span>
                </Button>
              </div>
            </div>

            {/* Mobile Horizontal Scroll Hint */}
            <div className="sm:hidden px-4 py-1.5 bg-slate-100/70 dark:bg-white/5 border-b border-slate-200/60 dark:border-white/10 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
              <span>Scroll table horizontally for requirement math</span>
              <span>→</span>
            </div>

            <div className="overflow-x-auto">
              {(() => {
                const totalBreakdownWeight =
                  matchResult.breakdown?.reduce((acc: number, b: any) => acc + (b.weight || 0), 0) || 1;
                const sumContributions =
                  matchResult.breakdown?.reduce((acc: number, b: any) => acc + (b.contribution || 0), 0) || 0;

                return (
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-200 dark:border-white/10">
                      <tr>
                        <th className="py-3 px-4">Requirement</th>
                        <th className="py-3 px-3">Type</th>
                        <th className="py-3 px-3">Weight Share</th>
                        <th className="py-3 px-3">Candidate Match</th>
                        <th className="py-3 px-3">Match Type</th>
                        <th className="py-3 px-3 text-right">Credit</th>
                        <th className="py-3 px-4 text-right">Contribution</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                      {matchResult.breakdown?.map((item: any, idx: number) => {
                        const isMatched = item.match_type !== "missing";
                        const weightPercent = Math.round(((item.weight || 0) / totalBreakdownWeight) * 100);
                        const creditPercent = Math.round((item.credit || 0) * 100);
                        const contribPercent = ((item.contribution || 0) * 100).toFixed(1);

                        return (
                          <tr key={idx} className="hover:bg-slate-50/80 dark:hover:bg-white/5 transition-colors">
                            <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">
                              {item.requirement_name}
                            </td>
                            <td className="py-3 px-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                  item.required
                                    ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-800"
                                    : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-white/10"
                                }`}
                              >
                                {item.required ? "Required" : "Preferred"}
                              </span>
                            </td>
                            <td
                              className="py-3 px-3 font-mono font-medium text-slate-700 dark:text-slate-300"
                              title={`Importance: ${item.importance}/5, Raw weight: ${item.weight?.toFixed(2)}`}
                            >
                              {weightPercent}%
                            </td>
                            <td className="py-3 px-3">
                              {isMatched ? (
                                <span className="text-slate-800 dark:text-slate-200 font-medium">
                                  {item.matched_name || item.matched_slug}
                                </span>
                              ) : (
                                <span className="text-slate-400 italic">Missing</span>
                              )}
                            </td>
                            <td className="py-3 px-3">
                              <span
                                className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-medium ${
                                  item.match_type === "exact"
                                    ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                                    : item.match_type === "descendant" || item.match_type === "ancestor_or_sibling"
                                    ? "bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300 border border-brand-200 dark:border-brand-800"
                                    : item.match_type === "embedding"
                                    ? "bg-violet-50 text-violet-700 dark:bg-violet-950/60 dark:text-violet-300 border border-violet-200 dark:border-violet-800"
                                    : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-white/10"
                                }`}
                              >
                                {item.match_type}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-right font-mono font-medium">
                              {creditPercent}%
                            </td>
                            <td className="py-3 px-4 text-right font-mono font-bold text-brand-600 dark:text-brand-400">
                              +{contribPercent}%
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className="bg-slate-50 dark:bg-white/5 border-t border-slate-200 dark:border-white/10 font-bold">
                      <tr>
                        <td colSpan={5} className="py-3 px-4 text-slate-700 dark:text-slate-300 text-xs">
                          Total Requirements Contribution (Skill Score)
                        </td>
                        <td colSpan={2} className="py-3 px-4 text-right font-mono text-brand-600 dark:text-brand-400 text-xs">
                          {(sumContributions * 100).toFixed(1)}%
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                );
              })()}
            </div>
          </Card>
        </div>
      )}
    </motion.div>
  );
}

export default function MatchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading Matching Engine...</div>}>
      <MatchContent />
    </Suspense>
  );
}
