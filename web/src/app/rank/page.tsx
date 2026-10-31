"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Users,
  EyeOff,
  Filter,
  CheckCircle2,
  XCircle,
  Briefcase,
  ChevronRight,
  Sparkles,
  ArrowUpDown,
  Target,
} from "lucide-react";
import ScoreGauge from "@/components/ScoreGauge";
import SkillChip from "@/components/SkillChip";
import { SAMPLE_JOBS, SAMPLE_CANDIDATES } from "@/data/samples";
import { api, type RankResponseData } from "@/lib/api";

function RankingContent() {
  const searchParams = useSearchParams();
  const [jobs, setJobs] = useState<any[]>([]);
  const [candidatesMap, setCandidatesMap] = useState<Record<string, { name: string; title: string }>>({});
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [blind, setBlind] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [rankings, setRankings] = useState<RankResponseData[]>([]);

  // 1. Initial load: fetch jobs and candidates map
  useEffect(() => {
    async function loadMeta() {
      const paramJobId = searchParams?.get("job_id") || "";
      try {
        const [loadedJobs, loadedCands] = await Promise.allSettled([
          api.listJobs(),
          api.listCandidates(),
        ]);

        const map: Record<string, { name: string; title: string }> = {};
        if (loadedCands.status === "fulfilled" && loadedCands.value) {
          loadedCands.value.forEach((c) => {
            map[c.id] = { name: c.name, title: c.title };
          });
        }
        SAMPLE_CANDIDATES.forEach((c) => {
          if (!map[c.id]) map[c.id] = { name: c.name, title: c.title };
        });
        setCandidatesMap(map);

        if (loadedJobs.status === "fulfilled" && loadedJobs.value && loadedJobs.value.length > 0) {
          setJobs(loadedJobs.value);
          const found = paramJobId && loadedJobs.value.find((j: any) => j.id === paramJobId);
          setSelectedJobId(found ? paramJobId : loadedJobs.value[0].id);
        } else {
          setJobs(SAMPLE_JOBS as any);
          setSelectedJobId(SAMPLE_JOBS[0].id);
        }
      } catch {
        setJobs(SAMPLE_JOBS as any);
        setSelectedJobId(SAMPLE_JOBS[0].id);
      }
    }
    loadMeta();
  }, [searchParams]);

  // 2. Fetch rankings for selected job
  const fetchRankings = async (jobId: string, isBlind: boolean) => {
    if (!jobId) return;
    setLoading(true);
    try {
      const selectedJob = jobs.find((j) => j.id === jobId) || SAMPLE_JOBS.find((j) => j.id === jobId);

      const rankPayload: any = {
        limit: 20,
      };

      if (jobId && !jobId.startsWith("sample-")) {
        rankPayload.job_id = jobId;
      } else {
        rankPayload.job = {
          title: selectedJob ? selectedJob.title : "Target Role",
          description: selectedJob ? (selectedJob.description || selectedJob.raw_text) : "Engineering role",
        };
      }

      const res = await api.rank(rankPayload, isBlind);
      setRankings(res);
    } catch {
      // Fallback demo rankings
      setRankings([
        {
          candidate_id: "00000000-0000-0000-0000-000000000002",
          name: isBlind ? "Candidate #1" : "Marcus Vance",
          score: 0.92,
          is_match: true,
          matched_skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis"],
          missing_skills: [],
          quality: 1.0,
        },
        {
          candidate_id: "00000000-0000-0000-0000-000000000001",
          name: isBlind ? "Candidate #2" : "Allison Hill",
          score: 0.81,
          is_match: true,
          matched_skills: ["TypeScript", "Docker", "AWS", "CI/CD Pipelines", "PostgreSQL"],
          missing_skills: ["FastAPI"],
          quality: 0.98,
        },
        {
          candidate_id: "00000000-0000-0000-0000-000000000003",
          name: isBlind ? "Candidate #3" : "Elena Rostova",
          score: 0.74,
          is_match: true,
          matched_skills: ["Python", "Docker", "Kubernetes"],
          missing_skills: ["FastAPI", "PostgreSQL"],
          quality: 1.0,
        },
      ] as any);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedJobId) {
      fetchRankings(selectedJobId, blind);
    }
  }, [selectedJobId, blind]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            Recruiter Candidate Ranking
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Batch rank talent against requisitions with explainable rubrics and anti-bias redaction.
          </p>
        </div>

        {/* Blind Screening Toggle */}
        <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm self-start sm:self-auto">
          <EyeOff className={`w-4 h-4 ${blind ? "text-purple-600" : "text-slate-400"}`} />
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Blind Screening
          </span>
          <input
            type="checkbox"
            checked={blind}
            onChange={(e) => setBlind(e.target.checked)}
            className="w-4 h-4 text-purple-600 rounded border-slate-300 focus:ring-purple-500 cursor-pointer ml-1"
          />
        </div>
      </div>

      {/* Requisition Selector Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1 max-w-xl">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1.5 flex items-center gap-1.5">
            <Briefcase className="w-3.5 h-3.5 text-indigo-500" />
            <span>Select Active Job Requisition</span>
          </label>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4 text-xs text-slate-500 border-t md:border-t-0 md:border-l border-slate-200 dark:border-slate-800 pt-3 md:pt-0 md:pl-6">
          <div>
            <p className="font-semibold text-slate-700 dark:text-slate-300">Candidates Evaluated</p>
            <p className="font-mono text-sm text-indigo-600 dark:text-indigo-400 font-bold">
              {rankings.length}
            </p>
          </div>
          <div>
            <p className="font-semibold text-slate-700 dark:text-slate-300">Match Model</p>
            <p className="font-mono text-xs">Weighted Rubric</p>
          </div>
        </div>
      </div>

      {/* Ranked Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="w-4 h-4 text-indigo-500" />
            <span>Ranked Candidates for Requisition</span>
          </h3>
          <span className="text-xs text-slate-400">
            Sorted by Overall Match Score & Skill Fit
          </span>
        </div>

        {loading ? (
          <div className="p-12 text-center text-slate-500 space-y-2">
            <span className="inline-block w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs font-medium">Computing Multi-Candidate Ranking...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200 dark:border-slate-700">
                <tr>
                  <th className="py-3 px-4">Rank</th>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-3">Match Score</th>
                  <th className="py-3 px-4">Top Matched Skills</th>
                  <th className="py-3 px-4">Missing Gaps</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {rankings.map((rank: any, idx: number) => {
                  const score = rank.match ? rank.match.score : (rank.score || 0);
                  const isPass = rank.match ? rank.match.is_match : (rank.is_match ?? true);
                  const scorePct = Math.round(score * 100);

                  const matchedSkills: string[] = rank.match
                    ? rank.match.breakdown?.filter((b: any) => b.match_type !== "missing").map((b: any) => b.matched_name || b.requirement_name) || []
                    : (rank.matched_skills || []);

                  const missingGaps: string[] = rank.match
                    ? rank.match.gaps?.map((g: any) => g.skill_name || g.skill_slug) || []
                    : (rank.missing_skills || []);

                  const candMeta = candidatesMap[rank.candidate_id] || { name: `Candidate #${idx + 1}`, title: "Professional" };
                  const displayName = blind ? `Candidate #${idx + 1}` : (candMeta.name || rank.name || `Candidate #${idx + 1}`);
                  const displayTitle = blind ? "Screened Applicant" : (candMeta.title || "Applicant");

                  return (
                    <tr
                      key={rank.candidate_id || idx}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3 px-4 font-mono font-bold text-slate-500">
                        #{idx + 1}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">
                        <div className="flex items-center gap-2.5">
                          <span className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold text-xs">
                            {idx + 1}
                          </span>
                          <div>
                            <p className="text-sm font-semibold text-slate-900 dark:text-white">{displayName}</p>
                            <p className="text-[11px] text-slate-500">
                              {displayTitle} • <span className="font-mono text-[10px] text-slate-400">ID: {String(rank.candidate_id || "").slice(0, 8)}</span>
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                scorePct >= 75
                                  ? "bg-emerald-500"
                                  : scorePct >= 50
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${scorePct}%` }}
                            />
                          </div>
                          <span className="font-mono font-bold text-xs">{scorePct}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {matchedSkills.slice(0, 4).map((sk: string, i: number) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 font-medium"
                            >
                              {sk}
                            </span>
                          ))}
                          {matchedSkills.length > 4 && (
                            <span className="text-[10px] text-slate-400 self-center">
                              +{matchedSkills.length - 4}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {missingGaps.length === 0 ? (
                            <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> None
                            </span>
                          ) : (
                            missingGaps.slice(0, 3).map((gap: string, i: number) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 rounded text-[10px] bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 font-medium"
                              >
                                {gap}
                              </span>
                            ))
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link
                            href={`/match?candidate_id=${rank.candidate_id}&job_id=${selectedJobId}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 text-xs font-medium transition-colors"
                          >
                            <Target className="w-3 h-3" />
                            <span>Inspect</span>
                          </Link>
                          <Link
                            href={`/coach?candidate_id=${rank.candidate_id}&job_id=${selectedJobId}`}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 text-xs font-medium transition-colors"
                          >
                            <Sparkles className="w-3 h-3" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default function RecruiterRankingPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading Candidate Rankings...</div>}>
      <RankingContent />
    </Suspense>
  );
}
