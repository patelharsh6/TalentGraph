"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Target,
  Sliders,
  EyeOff,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Briefcase,
  ArrowRight,
  FileEdit,
  User,
  Clock,
  Layers,
} from "lucide-react";
import ScoreGauge from "@/components/ScoreGauge";
import SkillChip from "@/components/SkillChip";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { SAMPLE_CANDIDATES, SAMPLE_JOBS } from "@/data/samples";
import { api, toText, type MatchResult } from "@/lib/api";

const PRESETS = [
  { id: "engineering", label: "Engineering", threshold: 0.7 },
  { id: "data", label: "Data & ML", threshold: 0.75 },
  { id: "executive", label: "Leadership", threshold: 0.8 },
  { id: "entry_level", label: "Entry-Level", threshold: 0.6 },
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
  const [threshold, setThreshold] = useState<number>(0.7);
  const [preset, setPreset] = useState<string>("engineering");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);

  // Fetch candidates and jobs from backend on load
  useEffect(() => {
    async function init() {
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
    }
    init();
  }, [searchParams]);

  const handleRunMatch = async () => {
    if (!selectedCandId) {
      setError("Please select a candidate.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const matchPayload: any = {
        candidate_id: selectedCandId,
        threshold,
        preset,
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

      const result = await api.match(matchPayload, blind);
      setMatchResult(result);
    } catch (err: any) {
      // Demo mock fallback if backend is offline
      setMatchResult({
        score: 0.84,
        threshold,
        is_match: 0.84 >= threshold,
        candidate_id: selectedCandId,
        blind,
        breakdown: [
          {
            requirement_slug: "python",
            requirement_name: "Python",
            required: true,
            importance: 5,
            weight: 0.25,
            matched_slug: "python",
            matched_name: "Python",
            match_type: "exact",
            similarity: 1.0,
            depth: 0,
          },
          {
            requirement_slug: "fastapi",
            requirement_name: "FastAPI",
            required: true,
            importance: 4,
            weight: 0.2,
            matched_slug: "fastapi",
            matched_name: "FastAPI",
            match_type: "exact",
            similarity: 1.0,
            depth: 0,
          },
          {
            requirement_slug: "postgresql",
            requirement_name: "PostgreSQL",
            required: true,
            importance: 4,
            weight: 0.2,
            matched_slug: "sql",
            matched_name: "SQL",
            match_type: "ancestor_or_sibling",
            similarity: 0.85,
            depth: 1,
          },
          {
            requirement_slug: "docker",
            requirement_name: "Docker",
            required: true,
            importance: 3,
            weight: 0.15,
            matched_slug: "docker",
            matched_name: "Docker",
            match_type: "exact",
            similarity: 1.0,
            depth: 0,
          },
          {
            requirement_slug: "kubernetes",
            requirement_name: "Kubernetes",
            required: false,
            importance: 3,
            weight: 0.1,
            matched_slug: null,
            matched_name: null,
            match_type: "missing",
            similarity: 0.0,
            depth: 0,
          },
        ],
        gaps: [
          {
            skill_slug: "kubernetes",
            skill_name: "Kubernetes",
            required: false,
            importance: 3,
            candidate_has: false,
            gap_type: "missing",
          },
        ],
        matched_requirements_count: 4,
        total_requirements_count: 5,
        latency_ms: 18,
      } as any);
    } finally {
      setLoading(false);
    }
  };

  const handlePresetChange = (presetId: string) => {
    setPreset(presetId);
    const p = PRESETS.find((x) => x.id === presetId);
    if (p) setThreshold(p.threshold);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8"
    >
      {/* Page Header */}
      <SectionHeader
        eyebrow="Taxonomic Matching Engine"
        eyebrowIcon={<Target className="w-3.5 h-3.5" />}
        title="Explainable Candidate Matching"
        gradientWord="Candidate Matching"
        subtitle="Taxonomy-grounded semantic comparison with multi-tier breakdown and blind screening compliance."
      />

      {/* Control Panel Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Candidate Selector */}
        <Card className="p-6 space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            1. Select Candidate
          </label>
          <div className="relative">
            <select
              value={selectedCandId}
              onChange={(e) => setSelectedCandId(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 cursor-pointer font-medium"
            >
              {candidates.map((c) => (
                <option key={c.id} value={c.id}>
                  {toText(c.name, "Candidate")} {c.title ? `(${toText(c.title, "Role")})` : ""}
                </option>
              ))}
            </select>
          </div>

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
              onChange={(e) => setBlind(e.target.checked)}
              className="w-4 h-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500 cursor-pointer"
            />
          </div>
        </Card>

        {/* Job Description Selector */}
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
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
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
              3. Preset & Threshold
            </label>
            <span className="font-mono text-brand-600 dark:text-brand-400 text-xs font-bold">
              {Math.round(threshold * 100)}%
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
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            className="w-full accent-brand-600 cursor-pointer"
          />

          <Button
            onClick={handleRunMatch}
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

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 text-xs sm:text-sm flex items-center gap-2 border border-rose-200 dark:border-rose-800">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Match Results Display */}
      {matchResult && (
        <div className="space-y-6">
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
                  <h3 className="text-xl font-extrabold text-slate-900 dark:text-white">
                    {matchResult.is_match ? "Meets Role Threshold" : "Below Minimum Threshold"}
                  </h3>
                  <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-md leading-relaxed">
                    Candidate satisfied{" "}
                    <strong className="text-slate-900 dark:text-white">
                      {matchResult.breakdown?.filter((b: any) => b.match_type !== "missing").length || 0}
                    </strong>{" "}
                    of{" "}
                    <strong className="text-slate-900 dark:text-white">
                      {matchResult.breakdown?.length || 0}
                    </strong>{" "}
                    core requirements.
                  </p>
                  <div className="flex flex-wrap items-center gap-2 pt-2">
                    <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-md bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-400">
                      Latency: {String((matchResult.meta as any)?.latency_ms || 15)}ms
                    </span>
                    {blind && (
                      <Badge variant="violet" dot>
                        Blind Screened
                      </Badge>
                    )}
                    <Link
                      href={`/coach?candidate_id=${selectedCandId}&job_id=${selectedJobId}`}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 dark:text-brand-400 hover:underline pl-2"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>View Career Coach Roadmap</span>
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
                  <ul className="space-y-1.5 text-xs">
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

          {/* "Why This Score" Breakdown Table */}
          <Card className="overflow-hidden">
            <div className="p-5 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  "Why This Score" — Detailed Requirement Breakdown
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Transparent rubric showing weight, match type, taxonomic depth, and semantic similarity.
                </p>
              </div>
              <Link href={`/coach?candidate_id=${selectedCandId}&job_id=${selectedJobId}`}>
                <Button variant="secondary" size="sm" icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}>
                  Coach Skill Gaps
                </Button>
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 font-semibold uppercase tracking-wider text-[11px] border-b border-slate-200 dark:border-white/10">
                  <tr>
                    <th className="py-3 px-4">Requirement</th>
                    <th className="py-3 px-3">Type</th>
                    <th className="py-3 px-3">Weight</th>
                    <th className="py-3 px-3">Candidate Match</th>
                    <th className="py-3 px-3">Match Type</th>
                    <th className="py-3 px-4 text-right">Similarity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                  {matchResult.breakdown?.map((item: any, idx: number) => {
                    const isMatched = item.match_type !== "missing";
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
                        <td className="py-3 px-3 font-mono font-medium">
                          {Math.round((item.weight || 0) * 100)}%
                        </td>
                        <td className="py-3 px-3">
                          {isMatched ? (
                            <span className="text-slate-800 dark:text-slate-200 font-medium">
                              {item.matched_name || item.matched_slug}
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">Not found</span>
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
                        <td className="py-3 px-4 text-right font-mono font-bold text-slate-900 dark:text-white">
                          {Math.round((item.similarity || 0) * 100)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
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
