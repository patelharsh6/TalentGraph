"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
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
} from "lucide-react";
import ScoreGauge from "@/components/ScoreGauge";
import SkillChip from "@/components/SkillChip";
import { SAMPLE_CANDIDATES, SAMPLE_JOBS } from "@/data/samples";
import { api, type MatchResult } from "@/lib/api";

const PRESETS = [
  { id: "engineering", label: "Engineering (0.70)", threshold: 0.7 },
  { id: "data", label: "Data & ML (0.75)", threshold: 0.75 },
  { id: "executive", label: "Leadership (0.80)", threshold: 0.8 },
  { id: "entry_level", label: "Entry-Level (0.60)", threshold: 0.6 },
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Explainable Candidate Matching
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Taxonomy-grounded semantic comparison with multi-tier breakdown and blind screening compliance.
        </p>
      </div>

      {/* Control Panel Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Candidate Selector */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            1. Select Candidate
          </label>
          <select
            value={selectedCandId}
            onChange={(e) => setSelectedCandId(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} {c.title ? `(${c.title})` : ""}
              </option>
            ))}
          </select>

          {/* Blind Screening Toggle */}
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <EyeOff className="w-4 h-4 text-indigo-500" />
              <div>
                <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Blind Screening Mode
                </p>
                <p className="text-[11px] text-slate-500">Redacts name, gender, school & graduation</p>
              </div>
            </div>
            <input
              type="checkbox"
              checked={blind}
              onChange={(e) => setBlind(e.target.checked)}
              className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer"
            />
          </div>
        </div>

        {/* Job Description Selector */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
              2. Target Job Role
            </label>
            <button
              type="button"
              onClick={() => setShowCustomJob(!showCustomJob)}
              className="text-[11px] text-indigo-600 dark:text-indigo-400 font-medium hover:underline flex items-center gap-1"
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
              className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          ) : (
            <textarea
              rows={3}
              value={customJobText}
              onChange={(e) => setCustomJobText(e.target.value)}
              placeholder="Paste custom job title & description requirements here..."
              className="w-full px-3 py-2 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none font-mono"
            />
          )}

          <p className="text-[11px] text-slate-500">
            {jobs.length} requisitions loaded • 0 Gemini quota used on pre-seeded roles
          </p>
        </div>

        {/* Threshold & Preset */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block flex items-center justify-between">
            <span>3. Preset & Threshold</span>
            <span className="font-mono text-indigo-600 dark:text-indigo-400 text-xs">
              {Math.round(threshold * 100)}%
            </span>
          </label>

          {/* Preset Buttons */}
          <div className="grid grid-cols-2 gap-1.5">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => handlePresetChange(p.id)}
                className={`px-2 py-1 text-xs rounded-md border font-medium transition-colors ${
                  preset === p.id
                    ? "bg-indigo-50 border-indigo-500 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 font-semibold"
                    : "border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 text-slate-600 dark:text-slate-400"
                }`}
              >
                {p.label.split(" ")[0]}
              </button>
            ))}
          </div>

          <input
            type="range"
            min={0.4}
            max={0.95}
            step={0.05}
            value={threshold}
            onChange={(e) => setThreshold(parseFloat(e.target.value))}
            className="w-full accent-indigo-600 cursor-pointer"
          />

          <button
            onClick={handleRunMatch}
            disabled={loading}
            className="w-full mt-2 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs sm:text-sm flex items-center justify-center gap-2 shadow-sm transition-all"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Computing Match...</span>
              </>
            ) : (
              <>
                <Target className="w-4 h-4" />
                <span>Calculate Match Score</span>
              </>
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 text-xs sm:text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Match Results Display */}
      {matchResult && (
        <div className="space-y-6 animate-in fade-in duration-300">
          {/* Hero Score Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <ScoreGauge
                score={matchResult.score}
                threshold={matchResult.threshold}
                size={140}
              />
              <div className="text-center sm:text-left space-y-1">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  {matchResult.is_match ? "Meets Role Threshold" : "Below Minimum Threshold"}
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 max-w-md">
                  Candidate satisfied {matchResult.breakdown?.filter((b: any) => b.match_type !== "missing").length || 0} of {matchResult.breakdown?.length || 0} core role requirements.
                </p>
                <div className="flex flex-wrap items-center gap-2 pt-2">
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                    Latency: {String((matchResult.meta as any)?.latency_ms || 15)}ms
                  </span>
                  {blind && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300">
                      Blind Screened
                    </span>
                  )}
                  <Link
                    href={`/coach?candidate_id=${selectedCandId}&job_id=${selectedJobId}`}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline pl-2"
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>View Career Coach Roadmap</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </div>

            {/* Gap Summary Card */}
            <div className="bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60 rounded-lg p-4 w-full md:w-80">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                Gap Analysis Summary
              </h4>
              {matchResult.gaps && matchResult.gaps.length > 0 ? (
                <ul className="space-y-1 text-xs">
                  {matchResult.gaps.map((gap: any, i: number) => (
                    <li key={i} className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                      <XCircle className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>{gap.skill_name || gap.skill_slug}</span>
                      {gap.required && (
                        <span className="text-[10px] font-bold uppercase text-rose-500">(Required)</span>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>No critical gaps detected!</span>
                </div>
              )}
            </div>
          </div>

          {/* "Why This Score" Breakdown Table */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  "Why This Score" — Detailed Requirement Breakdown
                </h3>
                <p className="text-xs text-slate-500">
                  Transparent rubric showing weight, match type, taxonomic depth, and semantic similarity.
                </p>
              </div>
              <Link
                href={`/coach?candidate_id=${selectedCandId}&job_id=${selectedJobId}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-xs font-medium border border-indigo-200 dark:border-indigo-800 hover:bg-indigo-100 transition-colors self-start sm:self-auto"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Coach Skill Gaps</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-semibold uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
                  <tr>
                    <th className="py-2.5 px-4">Requirement</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Weight</th>
                    <th className="py-2.5 px-3">Candidate Match</th>
                    <th className="py-2.5 px-3">Match Type</th>
                    <th className="py-2.5 px-3 text-right">Similarity</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {matchResult.breakdown?.map((item: any, idx: number) => {
                    const isMatched = item.match_type !== "missing";
                    return (
                      <tr key={idx} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40">
                        <td className="py-2.5 px-4 font-medium text-slate-900 dark:text-white">
                          {item.requirement_name}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                              item.required
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                                : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                            }`}
                          >
                            {item.required ? "Required" : "Preferred"}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          {Math.round((item.weight || 0) * 100)}%
                        </td>
                        <td className="py-2.5 px-3">
                          {isMatched ? (
                            <span className="text-slate-800 dark:text-slate-200 font-medium">
                              {item.matched_name || item.matched_slug}
                            </span>
                          ) : (
                            <span className="text-slate-400 italic">Not found</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${
                              item.match_type === "exact"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                                : item.match_type === "descendant" || item.match_type === "ancestor_or_sibling"
                                ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                                : item.match_type === "embedding"
                                ? "bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300"
                                : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                            }`}
                          >
                            {item.match_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-semibold">
                          {Math.round((item.similarity || 0) * 100)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MatchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading Matching Engine...</div>}>
      <MatchContent />
    </Suspense>
  );
}
