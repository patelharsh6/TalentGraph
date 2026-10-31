"use client";

import { useEffect, useState } from "react";
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

export default function MatchPage() {
  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedCandId, setSelectedCandId] = useState<string>("");
  const [selectedJobId, setSelectedJobId] = useState<string>("sample-job-1");
  const [customJobText, setCustomJobText] = useState<string>("");
  const [blind, setBlind] = useState<boolean>(false);
  const [threshold, setThreshold] = useState<number>(0.7);
  const [preset, setPreset] = useState<string>("engineering");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);

  // Fetch candidates from backend on load
  useEffect(() => {
    async function init() {
      try {
        const cands = await api.listCandidates();
        if (cands && cands.length > 0) {
          setCandidates(cands);
          setSelectedCandId(cands[0].id);
        } else {
          // Fallback to sample candidate UUIDs
          setCandidates(
            SAMPLE_CANDIDATES.map((sc, i) => ({
              id: `00000000-0000-0000-0000-00000000000${i + 1}`,
              name: sc.name,
              title: sc.title,
            }))
          );
          setSelectedCandId("00000000-0000-0000-0000-000000000001");
        }
      } catch {
        setCandidates(
          SAMPLE_CANDIDATES.map((sc, i) => ({
            id: `00000000-0000-0000-0000-00000000000${i + 1}`,
            name: sc.name,
            title: sc.title,
          }))
        );
        setSelectedCandId("00000000-0000-0000-0000-000000000001");
      }
    }
    init();
  }, []);

  const handleRunMatch = async () => {
    if (!selectedCandId) {
      setError("Please select a candidate.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      const selectedSampleJob = SAMPLE_JOBS.find((j) => j.id === selectedJobId);
      const jobPayload = {
        title: selectedSampleJob ? selectedSampleJob.title : "Target Role",
        description: customJobText || (selectedSampleJob ? selectedSampleJob.description : "Software Engineer"),
      };

      const result = await api.match(
        {
          candidate_id: selectedCandId,
          job: jobPayload,
          threshold,
          preset,
        },
        blind
      );
      setMatchResult(result);
    } catch (err: any) {
      // Demo mock fallback if offline
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
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            2. Target Job Role
          </label>
          <select
            value={selectedJobId}
            onChange={(e) => {
              setSelectedJobId(e.target.value);
              setCustomJobText("");
            }}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {SAMPLE_JOBS.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title}
              </option>
            ))}
          </select>
          <p className="text-[11px] text-slate-500">
            Selected: {SAMPLE_JOBS.find((j) => j.id === selectedJobId)?.company} • Min {SAMPLE_JOBS.find((j) => j.id === selectedJobId)?.minYears}y exp
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
            <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                "Why This Score" — Detailed Requirement Breakdown
              </h3>
              <p className="text-xs text-slate-500">
                Transparent rubric showing weight, match type, taxonomic depth, and semantic similarity.
              </p>
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
