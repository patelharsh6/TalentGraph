"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Users,
  EyeOff,
  CheckCircle2,
  Target,
  Sparkles,
  TrendingUp,
  Search,
  Filter,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
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
  const [error, setError] = useState<string | null>(null);

  // Filters and Sorting
  const [statusFilter, setStatusFilter] = useState<"all" | "qualified" | "high">("all");
  const [searchFilter, setSearchFilter] = useState<string>("");
  const [sortBy, setSortBy] = useState<"score" | "skill">("score");

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
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const allCands = await api.listCandidates();
      const candIds = allCands.map((c) => c.id);

      const res = await api.rank(
        {
          candidate_ids: candIds.length > 0 ? candIds : undefined,
          job_id: jobId.startsWith("sample-") ? undefined : jobId,
          limit: 30,
        },
        isBlind
      );
      setRankings(res);
    } catch (err: any) {
      setError(err?.message || "Failed to calculate candidate rankings. Check backend status.");
      setRankings([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedJobId) {
      fetchRankings(selectedJobId, blind);
    }
  }, [selectedJobId, blind]);

  // Reactive filtering and sorting
  const filteredRankings = useMemo(() => {
    let list = [...rankings];

    // Status filter
    if (statusFilter === "qualified") {
      list = list.filter((r) => r.match?.is_match);
    } else if (statusFilter === "high") {
      list = list.filter((r) => (r.match?.score || 0) >= 0.70);
    }

    // Keyword filter (name or matched skill)
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase().trim();
      list = list.filter((r) => {
        const candName = candidatesMap[r.candidate_id]?.name || "";
        const candTitle = candidatesMap[r.candidate_id]?.title || "";
        const matchedSkills =
          r.match?.breakdown?.filter((b: any) => b.match_type !== "missing").map((b: any) => b.requirement_name || "") || [];
        return (
          candName.toLowerCase().includes(q) ||
          candTitle.toLowerCase().includes(q) ||
          matchedSkills.some((s: string) => s.toLowerCase().includes(q))
        );
      });
    }

    // Sorting
    list.sort((a, b) => {
      if (sortBy === "skill") {
        const aSkill = a.match?.components?.skill_score || 0;
        const bSkill = b.match?.components?.skill_score || 0;
        return bSkill - aSkill;
      }
      return (b.match?.score || 0) - (a.match?.score || 0);
    });

    return list;
  }, [rankings, statusFilter, searchFilter, sortBy, candidatesMap]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8"
    >
      {/* Page Header */}
      <SectionHeader
        eyebrow="Recruiter Ranking Board"
        eyebrowIcon={<Users className="w-3.5 h-3.5" />}
        title="Multi-Candidate Role Ranking"
        gradientWord="Role Ranking"
        subtitle="Rank your candidate talent pool against open requisitions with explainable skill fit breakdowns."
      />

      {/* Control Ribbon */}
      <Card className="p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-1.5 flex-1 max-w-md">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
              Target Job Requisition
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

          <div className="flex items-center gap-6 self-start sm:self-center pt-2 sm:pt-0">
            {/* Blind Screening Toggle */}
            <label className="flex items-center gap-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={blind}
                onChange={(e) => setBlind(e.target.checked)}
                className="w-4 h-4 text-brand-600 rounded border-slate-300 focus:ring-brand-500 cursor-pointer"
              />
              <div>
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                  <EyeOff className="w-3.5 h-3.5 text-violet-500" />
                  Blind Screening
                </span>
                <span className="text-[11px] text-slate-400 block">Redacts names & institutions</span>
              </div>
            </label>

            <Button
              variant="secondary"
              size="sm"
              loading={loading}
              onClick={() => fetchRankings(selectedJobId, blind)}
              icon={<TrendingUp className="w-3.5 h-3.5 text-brand-500" />}
            >
              Refresh Ranking
            </Button>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="pt-4 border-t border-slate-100 dark:border-white/10 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-bold text-slate-400 flex items-center gap-1.5 mr-1">
              <Filter className="w-3.5 h-3.5" />
              <span>Filter:</span>
            </span>
            <button
              type="button"
              onClick={() => setStatusFilter("all")}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                statusFilter === "all"
                  ? "bg-brand-500 text-white shadow-sm"
                  : "bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10"
              }`}
            >
              All Candidates ({rankings.length})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("qualified")}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                statusFilter === "qualified"
                  ? "bg-brand-500 text-white shadow-sm"
                  : "bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10"
              }`}
            >
              Qualified Only ({rankings.filter((r) => r.match?.is_match).length})
            </button>
            <button
              type="button"
              onClick={() => setStatusFilter("high")}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                statusFilter === "high"
                  ? "bg-brand-500 text-white shadow-sm"
                  : "bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-white/10"
              }`}
            >
              High Match ≥70% ({rankings.filter((r) => (r.match?.score || 0) >= 0.70).length})
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Search Input */}
            <div className="relative flex-1 md:w-56">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Search candidate or skill..."
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>

            {/* Sort Toggle */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as "score" | "skill")}
              className="px-2.5 py-1.5 text-xs rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500 font-medium"
            >
              <option value="score">Sort: Match Score</option>
              <option value="skill">Sort: Skill Score</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Error Alert with Retry */}
      {error && (
        <ErrorAlert
          title="Ranking Calculation Error"
          message={error}
          onRetry={() => fetchRankings(selectedJobId, blind)}
        />
      )}

      {/* Ranking Results Card */}
      <Card className="overflow-hidden">
        <div className="p-5 border-b border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-brand-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Ranked Candidates for Requisition
            </h3>
            <span className="text-xs text-slate-500 dark:text-slate-400">
              ({filteredRankings.length} of {rankings.length} candidates)
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            disabled
            className="opacity-60 cursor-not-allowed text-xs self-start sm:self-auto"
            title="CSV export pipeline is in active development"
          >
            <span>Export Ranked CSV</span>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-white/10 font-mono uppercase">
              Soon
            </span>
          </Button>
        </div>

        {/* Mobile Horizontal Scroll Hint */}
        <div className="sm:hidden px-4 py-1.5 bg-slate-100/70 dark:bg-white/5 border-b border-slate-200/60 dark:border-white/10 text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between">
          <span>Scroll table horizontally for full candidate telemetry</span>
          <span>→</span>
        </div>

        {loading ? (
          <TableSkeleton rows={5} cols={6} />
        ) : !error && filteredRankings.length === 0 ? (
          <EmptyState
            icon={Users}
            title={rankings.length === 0 ? "No Candidates Ranked" : "No Candidates Match Active Filters"}
            description={
              rankings.length === 0
                ? "No candidates were found matching this requisition. Upload candidate resumes on the home page or select a different requisition."
                : "Try clearing your skill search or changing your threshold filter."
            }
            actionText={rankings.length === 0 ? "Upload Resumes" : "Reset Filters"}
            onAction={() => {
              if (rankings.length === 0) {
                window.location.href = "/";
              } else {
                setStatusFilter("all");
                setSearchFilter("");
              }
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300 uppercase tracking-wider text-[11px] font-semibold border-b border-slate-200 dark:border-white/10">
                <tr>
                  <th className="py-3 px-4">Rank</th>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Match Score</th>
                  <th className="py-3 px-4">Skill Score</th>
                  <th className="py-3 px-4">Top Matched Skills</th>
                  <th className="py-3 px-4">Missing Gaps</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                {filteredRankings.map((rank: any, idx: number) => {
                  const score = rank.match ? rank.match.score : (rank.score || 0);
                  const isPass = rank.match ? rank.match.is_match : (rank.is_match ?? true);
                  const scorePct = Math.round(score * 100);
                  const skillScore = rank.match?.components?.skill_score || 0;
                  const skillScorePct = Math.round(skillScore * 100);

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
                            {String(displayName || "Candidate").slice(0, 2).toUpperCase()}
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
                          <div className="w-16 bg-slate-100 dark:bg-white/10 h-2 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                isPass
                                  ? "bg-gradient-to-r from-emerald-500 to-cyan-500"
                                  : "bg-gradient-to-r from-rose-500 to-amber-500"
                              }`}
                              style={{ width: `${scorePct}%` }}
                            />
                          </div>
                          <span className="font-mono font-bold text-xs">{scorePct}%</span>
                          {isPass && (
                            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">
                              PASS
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-semibold text-xs text-slate-700 dark:text-slate-300">
                        {skillScorePct}%
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
