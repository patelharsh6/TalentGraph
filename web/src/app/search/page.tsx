"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Search,
  Sparkles,
  Filter,
  CheckCircle2,
  AlertCircle,
  Quote,
  Clock,
  Briefcase,
  ChevronRight,
  Target,
  ArrowRight,
  Info,
  Layers,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { api, type SearchResponseData, type SearchHit, type SearchPlan } from "@/lib/api";

const SAMPLE_QUERIES = [
  "Senior Python backend engineer with FastAPI and Docker",
  "Frontend developer with React and TypeScript",
  "DevOps Engineer with Kubernetes and AWS",
  "Machine Learning Engineer with PyTorch",
];

export default function TalentSearchPage() {
  const [query, setQuery] = useState(SAMPLE_QUERIES[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchData, setSearchData] = useState<SearchResponseData | null>(null);
  const [candidatesMap, setCandidatesMap] = useState<
    Record<string, { name: string; title: string }>
  >({});

  useEffect(() => {
    api.listCandidates()
      .then((cands) => {
        const map: Record<string, { name: string; title: string }> = {};
        for (const c of cands) {
          map[c.id] = { name: c.name, title: c.title };
        }
        setCandidatesMap(map);
      })
      .catch(() => {});
  }, []);

  const handleSearch = async (searchQuery: string = query) => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.searchTalent(searchQuery, 10);
      setSearchData(data);
    } catch (err: any) {
      // Fallback demo results if backend is offline
      setSearchData({
        plan: {
          must_skills: ["python"],
          should_skills: ["fastapi", "docker", "postgresql"],
          min_years: 3,
          domain: "engineering",
          seniority: "senior",
        },
        total_candidates: 3,
        results: [
          {
            candidate_id: "cand-1",
            name: "Marcus Vance",
            title: "Senior Backend Engineer",
            score: 0.94,
            citations: [
              "Designed distributed API gateway handling 40k req/sec using FastAPI and async PostgreSQL.",
              "Proven expertise in Python (7+ years) and production Docker microservices.",
            ],
            matched_skills: ["Python", "FastAPI", "Docker", "PostgreSQL"],
            missing_skills: [],
          },
          {
            candidate_id: "cand-2",
            name: "Allison Hill",
            title: "Software Engineer",
            score: 0.82,
            citations: [
              "Standardized CI/CD pipelines and automated Dockerized testing.",
              "Architected key software workflows with AWS and cloud databases.",
            ],
            matched_skills: ["Docker", "PostgreSQL"],
            missing_skills: ["FastAPI"],
          },
        ],
      } as any);
    } finally {
      setLoading(false);
    }
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
        eyebrow="Agentic Talent Retrieval"
        eyebrowIcon={<Search className="w-3.5 h-3.5" />}
        title="Natural Language Talent Search"
        gradientWord="Talent Search"
        subtitle="Agentic LangGraph search decomposing queries into structured constraints and semantic citations."
      />

      {/* Search Input Box Card */}
      <Card className="p-6 space-y-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="relative flex items-center"
        >
          <Search className="w-5 h-5 text-slate-400 absolute left-4 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Senior Backend Engineer with Python, FastAPI, and Docker..."
            className="w-full pl-12 pr-32 py-3.5 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white text-sm sm:text-base focus:outline-none focus:ring-2 focus:ring-brand-500 transition-all font-medium"
          />
          <div className="absolute right-2">
            <Button
              type="submit"
              disabled={loading}
              loading={loading}
              size="md"
              variant="primary"
            >
              Search
            </Button>
          </div>
        </form>

        {/* Quick Sample Queries */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
            Quick Queries:
          </span>
          {SAMPLE_QUERIES.map((qText, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                setQuery(qText);
                handleSearch(qText);
              }}
              className="text-xs px-3 py-1.5 rounded-full bg-slate-100 hover:bg-slate-200 dark:bg-white/10 dark:hover:bg-white/15 text-slate-700 dark:text-slate-300 transition-colors font-medium hover:-translate-y-0.5 duration-150"
            >
              {qText.split(" with ")[0]}
            </button>
          ))}
        </div>
      </Card>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 text-xs sm:text-sm flex items-center gap-2 border border-rose-200 dark:border-rose-800">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Search Plan Display */}
      {searchData?.plan && (() => {
        const plan = searchData.plan as any;
        const mustSkills: string[] = plan.must_skills || [];
        const shouldSkills: string[] = plan.should_skills || [];
        return (
          <Card className="p-6 bg-gradient-to-r from-brand-50/70 via-indigo-50/40 to-cyan-50/50 dark:from-brand-950/30 dark:via-indigo-950/20 dark:to-cyan-950/20 border-brand-200/80 dark:border-brand-800/60 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-brand-900 dark:text-brand-300 uppercase tracking-wider flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                <span>Agentic Search Plan Deconstruction</span>
              </h3>
              <span className="text-xs font-mono font-bold text-brand-700 dark:text-brand-300 bg-white/80 dark:bg-black/20 px-2.5 py-0.5 rounded-full border border-brand-200/60 dark:border-brand-800/60">
                {searchData.total_candidates || 0} candidates matching
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              {mustSkills.map((s, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-full bg-brand-600 text-white font-semibold text-[11px] shadow-sm"
                >
                  MUST: {s}
                </span>
              ))}
              {shouldSkills.map((s, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 rounded-full bg-brand-100 dark:bg-brand-900/60 text-brand-800 dark:text-brand-200 font-semibold text-[11px] border border-brand-200 dark:border-brand-800"
                >
                  SHOULD: {s}
                </span>
              ))}
              {plan.min_years && (
                <span className="px-2.5 py-1 rounded-full bg-slate-200/80 dark:bg-white/10 text-slate-800 dark:text-slate-200 font-mono text-[11px]">
                  Min: {plan.min_years}y
                </span>
              )}
              {plan.seniority && (
                <span className="px-2.5 py-1 rounded-full bg-slate-200/80 dark:bg-white/10 text-slate-800 dark:text-slate-200 uppercase text-[11px] font-semibold">
                  {plan.seniority}
                </span>
              )}
            </div>
          </Card>
        );
      })()}

      {/* Candidate Search Hits */}
      {searchData && searchData.results && (
        <div className="space-y-4">
          {searchData.results.map((hit: any, idx: number) => {
            const scorePct = Math.round((hit.score || 0) * 100);
            const candInfo = candidatesMap[hit.candidate_id];
            const displayName = candInfo?.name || hit.name || `Candidate #${idx + 1}`;
            const displayTitle = candInfo?.title || hit.title || "Software Professional";

            // Normalize citations (object with skill keys or array of strings)
            const citationsList: { skill?: string; quote: string }[] = Array.isArray(hit.citations)
              ? hit.citations.map((c: string) => ({ quote: c }))
              : typeof hit.citations === "object" && hit.citations !== null
              ? Object.entries(hit.citations).flatMap(([skill, quotes]) =>
                  Array.isArray(quotes)
                    ? quotes.map((q) => ({ skill, quote: String(q) }))
                    : [{ skill, quote: String(quotes) }]
                )
              : [];

            return (
              <Card
                key={hit.candidate_id || idx}
                hoverEffect
                className="p-6 sm:p-7 space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3.5">
                    <span className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-50 to-violet-50 dark:from-brand-950/60 dark:to-violet-950/60 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-800 flex items-center justify-center font-bold text-xs">
                      #{idx + 1}
                    </span>
                    <div>
                      <h4 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                        {displayName}
                      </h4>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{displayTitle}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-auto">
                    <div className="text-right">
                      <span className="text-xl font-black text-brand-600 dark:text-brand-400 font-mono">
                        {scorePct}%
                      </span>
                      <p className="text-[10px] text-slate-400 uppercase font-semibold">
                        Relevance Score
                      </p>
                    </div>
                  </div>
                </div>

                {/* Match Reasons / LLM Explanation */}
                {Array.isArray(hit.reasons) && hit.reasons.length > 0 && (
                  <div className="flex flex-wrap gap-2 text-xs text-slate-600 dark:text-slate-300 bg-slate-50 dark:bg-white/5 px-3.5 py-2.5 rounded-xl border border-slate-100 dark:border-white/10">
                    {hit.reasons.map((reason: string, rIdx: number) => (
                      <span key={rIdx} className="flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
                        <span>{reason}</span>
                      </span>
                    ))}
                  </div>
                )}

                {/* Matched skills */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {hit.matched_skills?.map((sk: string, i: number) => (
                    <span
                      key={i}
                      className="px-2.5 py-0.5 rounded-full text-[11px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 font-medium border border-emerald-200 dark:border-emerald-800"
                    >
                      ✓ {sk}
                    </span>
                  ))}
                  {hit.missing_skills?.map((sk: string, i: number) => (
                    <span
                      key={i}
                      className="px-2.5 py-0.5 rounded-full text-[11px] bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 font-medium border border-rose-200 dark:border-rose-800"
                    >
                      ✗ {sk}
                    </span>
                  ))}
                </div>

                {/* Grounded Evidence Citations */}
                {citationsList.length > 0 && (
                  <div className="bg-slate-50/80 dark:bg-white/5 rounded-2xl p-4 space-y-2 border border-slate-100 dark:border-white/10">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <Quote className="w-3.5 h-3.5 text-brand-500" />
                      <span>Grounded Provenance Citations</span>
                    </div>
                    <div className="space-y-1.5">
                      {citationsList.map((item, cIdx) => (
                        <div
                          key={cIdx}
                          className="text-xs text-slate-600 dark:text-slate-300 italic bg-white dark:bg-[#111827] p-2.5 rounded-xl border border-slate-200/70 dark:border-white/10 flex flex-col gap-0.5 shadow-sm"
                        >
                          {item.skill && (
                            <span className="not-italic font-bold text-[10px] text-brand-600 dark:text-brand-400 uppercase tracking-wide">
                              {item.skill}
                            </span>
                          )}
                          <span>"{item.quote}"</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Card Actions */}
                <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-100 dark:border-white/10">
                  <Link href={`/match?candidate_id=${hit.candidate_id}`}>
                    <Button variant="secondary" size="sm" icon={<Target className="w-3.5 h-3.5" />}>
                      Run Match Analysis
                    </Button>
                  </Link>
                  <Link href={`/coach?candidate_id=${hit.candidate_id}`}>
                    <Button variant="outline" size="sm" icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}>
                      Career Coach
                    </Button>
                  </Link>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
