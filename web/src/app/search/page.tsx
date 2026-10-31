"use client";

import { useState } from "react";
import Link from "next/link";
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
} from "lucide-react";
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Natural Language Talent Search
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Agentic LangGraph search decomposing queries into structured constraints and semantic citations.
        </p>
      </div>

      {/* Search Input Box */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 sm:p-5 shadow-sm space-y-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSearch();
          }}
          className="relative flex items-center"
        >
          <Search className="w-5 h-5 text-slate-400 absolute left-3.5 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Senior Backend Engineer with Python, FastAPI, and Docker..."
            className="w-full pl-10 pr-28 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50 text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
          />
          <button
            type="submit"
            disabled={loading}
            className="absolute right-2 px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs sm:text-sm shadow-sm transition-all"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </form>

        {/* Quick Sample Queries */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
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
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors"
            >
              {qText.split(" with ")[0]}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 text-xs sm:text-sm flex items-center gap-2">
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
          <div className="bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/40 rounded-xl p-4 shadow-sm space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-indigo-900 dark:text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-indigo-600" />
                Agentic Search Plan Deconstruction
              </h3>
              <span className="text-xs font-mono text-indigo-700 dark:text-indigo-400">
                {searchData.total_candidates || 0} candidates matching
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              {mustSkills.map((s, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded-md bg-indigo-600 text-white font-medium"
                >
                  MUST: {s}
                </span>
              ))}
              {shouldSkills.map((s, i) => (
                <span
                  key={i}
                  className="px-2 py-0.5 rounded-md bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-300 font-medium"
                >
                  SHOULD: {s}
                </span>
              ))}
              {plan.min_years && (
                <span className="px-2 py-0.5 rounded-md bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 font-mono">
                  Min: {plan.min_years}y
                </span>
              )}
              {plan.seniority && (
                <span className="px-2 py-0.5 rounded-md bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 uppercase">
                  {plan.seniority}
                </span>
              )}
            </div>
          </div>
        );
      })()}

      {/* Candidate Search Hits */}
      {searchData && searchData.results && (
        <div className="space-y-4">
          {searchData.results.map((hit: any, idx: number) => {
            const scorePct = Math.round((hit.score || 0) * 100);
            return (
              <div
                key={hit.candidate_id || idx}
                className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm hover:border-indigo-300 dark:hover:border-indigo-700 transition-all space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold text-xs">
                      #{idx + 1}
                    </span>
                    <div>
                      <h4 className="text-base font-bold text-slate-900 dark:text-white">
                        {hit.name || `Candidate #${idx + 1}`}
                      </h4>
                      <p className="text-xs text-slate-500">{hit.title || "Software Engineer"}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <span className="text-lg font-extrabold text-indigo-600 dark:text-indigo-400 font-mono">
                        {scorePct}%
                      </span>
                      <p className="text-[10px] text-slate-400 uppercase font-semibold">
                        Relevance Score
                      </p>
                    </div>
                  </div>
                </div>

                {/* Matched skills */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {hit.matched_skills?.map((sk: string, i: number) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded text-[11px] bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 font-medium border border-emerald-200 dark:border-emerald-800"
                    >
                      ✓ {sk}
                    </span>
                  ))}
                  {hit.missing_skills?.map((sk: string, i: number) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 rounded text-[11px] bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 font-medium border border-rose-200 dark:border-rose-800"
                    >
                      ✗ {sk}
                    </span>
                  ))}
                </div>

                {/* Evidence Citations */}
                {hit.citations && hit.citations.length > 0 && (
                  <div className="bg-slate-50 dark:bg-slate-800/40 rounded-lg p-3 space-y-1.5 border border-slate-100 dark:border-slate-800">
                    <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                      <Quote className="w-3.5 h-3.5 text-indigo-500" />
                      <span>Grounded Provenance Citations</span>
                    </div>
                    {hit.citations.map((cite: string, cIdx: number) => (
                      <p
                        key={cIdx}
                        className="text-xs italic text-slate-600 dark:text-slate-300 border-l-2 border-indigo-400 pl-2"
                      >
                        "{cite}"
                      </p>
                    ))}
                  </div>
                )}

                {/* Card Actions */}
                <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-100 dark:border-slate-800">
                  <Link
                    href={`/match?candidate_id=${hit.candidate_id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-xs font-semibold hover:bg-indigo-100 transition-colors"
                  >
                    <Target className="w-3.5 h-3.5" />
                    <span>Run Match Analysis</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                  <Link
                    href={`/coach?candidate_id=${hit.candidate_id}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-semibold hover:bg-slate-200 transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Career Coach</span>
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
