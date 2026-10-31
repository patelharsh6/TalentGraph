"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Users,
  EyeOff,
  Filter,
  CheckCircle2,
  AlertCircle,
  Briefcase,
  Target,
  Sparkles,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Award,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { SAMPLE_CANDIDATES, SAMPLE_JOBS } from "@/data/samples";
import { api, toText, type RankResponseData } from "@/lib/api";

function RankingContent() {
  const searchParams = useSearchParams();
  const [jobs, setJobs] = useState<any[]>([]);
  const [candidatesMap, setCandidatesMap] = useState<Record<string, { name: string; title: string }>>({});
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [blind, setBlind] = useState<boolean>(false);
  const [rankings, setRankings] = useState<RankResponseData[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch active requisitions and candidate metadata
  useEffect(() => {
    async function loadMeta() {
      try {
        const [loadedJobs, cands] = await Promise.allSettled([
          api.listJobs(),
          api.listCandidates(),
        ]);

        if (cands.status === "fulfilled" && cands.value) {
          const map: Record<string, { name: string; title: string }> = {};
          for (const c of cands.value) {
            map[c.id] = { name: c.name, title: c.title };
          }
          setCandidatesMap(map);
        }

        if (loadedJobs.status === "fulfilled" && loadedJobs.value && loadedJobs.value.length > 0) {
          setJobs(loadedJobs.value);
          const paramJobId = searchParams?.get("job_id") || "";
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

  const fetchRankings = async (jobId: string, isBlind: boolean) => {
    setLoading(true);
    try {
      const allCands = await api.listCandidates();
      const candIds = allCands.map((c) => c.id).slice(0, 15);

      const res = await api.rank(
        {
          candidate_ids: candIds,
          job_id: jobId.startsWith("sample-") ? undefined : jobId,
          limit: 10,
        },
        isBlind
      );
      setRankings(res);
    } catch (err: any) {
      // Fallback demo rankings
      setRankings([
        {
          candidate_id: "00000000-0000-0000-0000-000000000002",
          name: isBlind ? "Candidate #1" : "Marcus Vance",
          score: 0.94,
          is_match: true,
          matched_skills: ["Python", "FastAPI", "Docker", "PostgreSQL", "AsyncIO"],
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
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8"
    >
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <SectionHeader
          eyebrow="Recruiter Talent Hub"
          eyebrowIcon={<Users className="w-3.5 h-3.5" />}
          title="Recruiter Candidate Ranking"
          gradientWord="Candidate Ranking"
          subtitle="Batch rank talent against requisitions with explainable rubrics and anti-bias redaction."
        />

        {/* Blind Screening Toggle Card */}
        <div className="inline-flex items-center gap-3 px-4 py-2.5 rounded-2xl bg-white dark:bg-[#111827] border border-slate-200/80 dark:border-white/10 shadow-sm self-start sm:self-auto">
          <EyeOff className={`w-4 h-4 ${blind ? "text-violet-600 dark:text-violet-400" : "text-slate-400"}`} />
          <div>
            <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">
              Blind Screening
            </span>
            <span className="text-[10px] text-slate-400">Anonymize personal info</span>
          </div>
          <input
            type="checkbox"
            checked={blind}
            onChange={(e) => setBlind(e.target.checked)}
            className="w-4 h-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500 cursor-pointer ml-1"
          />
        </div>
      </div>

      {/* Requisition Selector Bar */}
      <Card className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex-1 max-w-xl space-y-2">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block flex items-center gap-1.5">
            <Briefcase className="w-3.5 h-3.5 text-brand-500" />
            <span>Select Active Job Requisition</span>
          </label>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 cursor-pointer font-medium"
          >
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {toText(j.title, "Requisition")}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-6 text-xs text-slate-500 border-t md:border-t-0 md:border-l border-slate-200/80 dark:border-white/10 pt-4 md:pt-0 md:pl-8">
          <div>
            <p className="font-semibold text-slate-700 dark:text-slate-300">Candidates Evaluated</p>
            <p className="font-mono text-lg text-brand-600 dark:text-brand-400 font-extrabold">
              {rankings.length}
            </p>
          </div>
          <div>
            <p className="font-semibold text-slate-700 dark:text-slate-300">Match Model</p>
            <p className="font-mono text-xs text-slate-600 dark:text-slate-400">Weighted Rubric</p>
          </div>
        </div>
      </Card>

      {/* Ranked Table */}
      <Card className="overflow-hidden">
        <div className="p-5 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Users className="w-4 h-4 text-brand-500" />
            <span>Ranked Candidates for Requisition</span>
          </h3>
          <span className="text-xs text-slate-400">
            Sorted by Overall Match Score & Skill Fit
          </span>
        </div>

        {loading ? (
          <div className="p-16 text-center text-slate-500 space-y-3">
            <span className="inline-block w-8 h-8 border-3 border-brand-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs font-semibold">Computing Multi-Candidate Ranking...</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200 dark:border-white/10">
                <tr>
                  <th className="py-3 px-4">Rank</th>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Match Score</th>
                  <th className="py-3 px-4">Top Matched Skills</th>
                  <th className="py-3 px-4">Missing Gaps</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/5">
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
                      className="hover:bg-slate-50/80 dark:hover:bg-white/5 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-slate-400">
                        <span
                          className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                            idx === 0
                              ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300 border border-amber-300"
                              : idx === 1
                              ? "bg-slate-200 text-slate-800 dark:bg-slate-700 dark:text-slate-200"
                              : "bg-slate-100 text-slate-600 dark:bg-white/10 dark:text-slate-400"
                          }`}
                        >
                          {idx + 1}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-900 dark:text-white">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-brand-50 to-violet-50 dark:from-brand-950/60 dark:to-violet-950/60 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800 flex items-center justify-center font-bold text-xs flex-shrink-0">
                            {displayName.slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <p className="text-sm font-bold text-slate-900 dark:text-white">{displayName}</p>
                            <p className="text-[11px] text-slate-500">
                              {displayTitle} • <span className="font-mono text-[10px] text-slate-400">ID: {String(rank.candidate_id || "").slice(0, 8)}</span>
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2.5">
                          <div className="w-20 bg-slate-100 dark:bg-white/10 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                scorePct >= 75
                                  ? "bg-gradient-to-r from-emerald-500 to-cyan-500"
                                  : scorePct >= 50
                                  ? "bg-gradient-to-r from-amber-500 to-yellow-500"
                                  : "bg-rose-500"
                              }`}
                              style={{ width: `${scorePct}%` }}
                            />
                          </div>
                          <span className="font-mono font-bold text-xs">{scorePct}%</span>
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {matchedSkills.slice(0, 4).map((sk: string, i: number) => (
                            <span
                              key={i}
                              className="px-2 py-0.5 rounded-full text-[10px] bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300 font-medium border border-brand-200/80 dark:border-brand-800/60"
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
                      <td className="py-3.5 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {missingGaps.length === 0 ? (
                            <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" /> None
                            </span>
                          ) : (
                            missingGaps.slice(0, 3).map((gap: string, i: number) => (
                              <span
                                key={i}
                                className="px-2 py-0.5 rounded-full text-[10px] bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 font-medium border border-rose-200/80 dark:border-rose-800/60"
                              >
                                {gap}
                              </span>
                            ))
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href={`/match?candidate_id=${rank.candidate_id}&job_id=${selectedJobId}`}
                          >
                            <Button variant="secondary" size="sm" icon={<Target className="w-3.5 h-3.5" />}>
                              Inspect
                            </Button>
                          </Link>
                          <Link
                            href={`/coach?candidate_id=${rank.candidate_id}&job_id=${selectedJobId}`}
                          >
                            <Button variant="outline" size="sm" icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}>
                              Coach
                            </Button>
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
      </Card>
    </motion.div>
  );
}

export default function RecruiterRankingPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading Candidate Rankings...</div>}>
      <RankingContent />
    </Suspense>
  );
}
