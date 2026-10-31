"use client";

import { useEffect, useState } from "react";
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
} from "lucide-react";
import ScoreGauge from "@/components/ScoreGauge";
import SkillChip from "@/components/SkillChip";
import { SAMPLE_JOBS } from "@/data/samples";
import { api, type RankResponseData } from "@/lib/api";

export default function RecruiterRankingPage() {
  const [selectedJobId, setSelectedJobId] = useState<string>("sample-job-1");
  const [blind, setBlind] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [rankings, setRankings] = useState<RankResponseData[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<any | null>(null);

  // Fetch rankings for selected job
  const fetchRankings = async (jobId: string, isBlind: boolean) => {
    setLoading(true);
    try {
      const selectedJob = SAMPLE_JOBS.find((j) => j.id === jobId);
      const res = await api.rank(
        {
          job: {
            title: selectedJob ? selectedJob.title : "Target Role",
            description: selectedJob ? selectedJob.description : "Engineering role",
          },
          limit: 20,
        },
        isBlind
      );
      setRankings(res);
    } catch {
      // Fallback demo rankings
      setRankings([
        {
          candidate_id: "00000000-0000-0000-0000-000000000002",
          name: isBlind ? "Candidate #2" : "Marcus Vance",
          score: 0.92,
          is_match: true,
          matched_skills: ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Redis"],
          missing_skills: [],
          quality: 1.0,
        },
        {
          candidate_id: "00000000-0000-0000-0000-000000000001",
          name: isBlind ? "Candidate #1" : "Allison Hill",
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
    fetchRankings(selectedJobId, blind);
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
        <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <EyeOff className={`w-4 h-4 ${blind ? "text-purple-600" : "text-slate-400"}`} />
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            Blind Screening
          </span>
          <input
            type="checkbox"
            checked={blind}
            onChange={(e) => setBlind(e.target.checked)}
            className="w-4 h-4 text-purple-600 rounded border-slate-300 focus:ring-purple-500 cursor-pointer"
          />
        </div>
      </div>

      {/* Requisition Selector Bar */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Briefcase className="w-5 h-5 text-indigo-500 flex-shrink-0" />
          <div className="flex-1">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
              Active Job Requisition
            </label>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="mt-1 font-semibold text-sm bg-transparent border-0 text-slate-900 dark:text-white focus:ring-0 cursor-pointer"
            >
              {SAMPLE_JOBS.map((j) => (
                <option key={j.id} value={j.id} className="dark:bg-slate-900">
                  {j.title} ({j.company})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>{rankings.length} candidates evaluated</span>
          <span className="h-4 w-px bg-slate-200 dark:bg-slate-700" />
          <button
            onClick={() => fetchRankings(selectedJobId, blind)}
            className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 font-medium hover:bg-indigo-100 transition-colors"
          >
            Re-rank Pool
          </button>
        </div>
      </div>

      {/* Rankings Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="p-12 text-center text-slate-500">
            <span className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin inline-block mb-2" />
            <p className="text-sm">Ranking candidates against job requirements...</p>
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
                  <th className="py-3 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {rankings.map((rank: any, idx: number) => {
                  const scorePct = Math.round((rank.score || 0) * 100);
                  const isPass = rank.is_match;
                  return (
                    <tr
                      key={rank.candidate_id || idx}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-3 px-4 font-mono font-bold text-slate-500">
                        #{idx + 1}
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">
                        <div className="flex items-center gap-2">
                          <span className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold text-xs">
                            {idx + 1}
                          </span>
                          <div>
                            <p>{rank.name || `Candidate #${idx + 1}`}</p>
                            <p className="text-[10px] text-slate-400 font-mono">
                              ID: {String(rank.candidate_id || "").slice(0, 8)}...
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
                          <span className="font-mono font-bold">{scorePct}%</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {rank.matched_skills?.slice(0, 4).map((sk: string, i: number) => (
                            <span
                              key={i}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 font-medium"
                            >
                              {sk}
                            </span>
                          ))}
                          {rank.matched_skills && rank.matched_skills.length > 4 && (
                            <span className="text-[10px] text-slate-400 self-center">
                              +{rank.matched_skills.length - 4}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {rank.missing_skills?.length > 0 ? (
                            rank.missing_skills.map((gap: string, i: number) => (
                              <span
                                key={i}
                                className="px-1.5 py-0.5 rounded text-[10px] bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 font-medium"
                              >
                                {gap}
                              </span>
                            ))
                          ) : (
                            <span className="text-emerald-500 text-[11px] font-medium flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> None
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
                            isPass
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                              : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                          }`}
                        >
                          {isPass ? "Qualified" : "Borderline"}
                        </span>
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
