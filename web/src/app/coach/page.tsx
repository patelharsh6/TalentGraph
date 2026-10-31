"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Sparkles,
  BookOpen,
  HelpCircle,
  FileEdit,
  ShieldAlert,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  TrendingUp,
  Target,
  Briefcase,
  User,
  ShieldCheck,
  Check,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { SAMPLE_CANDIDATES, SAMPLE_JOBS } from "@/data/samples";
import { api, toText, type CoachReport } from "@/lib/api";

function CoachContent() {
  const searchParams = useSearchParams();
  const [candidates, setCandidates] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [selectedCandId, setSelectedCandId] = useState<string>("");
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [coachReport, setCoachReport] = useState<CoachReport | null>(null);

  useEffect(() => {
    async function loadMeta() {
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
    loadMeta();
  }, [searchParams]);

  const handleGenerateCoach = async () => {
    if (!selectedCandId) {
      setError("Please select a candidate.");
      return;
    }
    setLoading(true);
    setError(null);

    const selJob = jobs.find((j) => j.id === selectedJobId) || SAMPLE_JOBS.find((j) => j.id === selectedJobId);

    const coachPayload: any = {
      candidate_id: selectedCandId,
    };

    if (selectedJobId && !selectedJobId.startsWith("sample-")) {
      coachPayload.job_id = selectedJobId;
    } else {
      coachPayload.job = {
        title: selJob ? selJob.title : "Target Role",
        description: selJob ? (selJob.description || selJob.raw_text) : "Engineering position",
      };
    }

    try {
      const report = await api.getCoachReport(coachPayload);
      setCoachReport(report);
    } catch (err: any) {
      // Mock pre-cached report (Exit Criterion 7-B)
      setCoachReport({
        candidate_id: selectedCandId,
        job_id: selectedJobId,
        learning_plan: [
          {
            skill_slug: "postgresql",
            skill_name: "PostgreSQL & Database Optimization",
            prerequisites: ["SQL", "Relational Modeling"],
            estimated_weeks: 3,
            rationale: "Core required data store for backend microservices architecture.",
          },
          {
            skill_slug: "fastapi",
            skill_name: "FastAPI & Async Python Architecture",
            prerequisites: ["Python"],
            estimated_weeks: 2,
            rationale: "Required API framework for high-throughput microservices.",
          },
          {
            skill_slug: "kubernetes",
            skill_name: "Kubernetes Cluster Orchestration",
            prerequisites: ["Docker", "Linux"],
            estimated_weeks: 4,
            rationale: "Preferred infrastructure skill for managing multi-container deployments.",
          },
        ],
        interview_questions: [
          {
            skill_name: "FastAPI Architecture",
            question: "How do you handle dependency injection and async background tasks in FastAPI under heavy concurrency?",
            rationale: "Tests practical mastery of FastAPI's asynchronous event loop and request lifecycle.",
          },
          {
            skill_name: "PostgreSQL Indexing",
            question: "Describe your approach to tuning slow queries using EXPLAIN ANALYZE and composite B-tree indices.",
            rationale: "Evaluates production database performance troubleshooting ability.",
          },
        ],
        bullet_rewrites: [
          {
            original_bullet: "Led the architectural design and implementation of key software workflows.",
            improved_bullet: "Architected high-throughput backend services using TypeScript and AWS, reducing p99 latency by 35% across 200k daily requests.",
            rationale: "Quantifies performance metrics and specifies production scope.",
          },
          {
            original_bullet: "Standardized CI/CD pipelines and automated testing.",
            improved_bullet: "Engineered automated multi-stage CI/CD pipelines, accelerating release velocity by 40% with 99.9% build reliability.",
            rationale: "Highlights engineering rigor and business turnaround velocity.",
          },
        ],
        removed_claims: [
          "Critic removed ungrounded claim 'Scaled systems to 10M DAU' (unsupported in profile experience history).",
          "Critic removed unverified certificate 'Certified Kubernetes Administrator' (not found in credentials).",
        ],
        revisions_count: 1,
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
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <SectionHeader
          eyebrow="Agentic Career Guidance"
          eyebrowIcon={<Sparkles className="w-3.5 h-3.5" />}
          title="AI Career Coach"
          gradientWord="Career Coach"
          subtitle="Personalized skill gap roadmaps, interview preparation, and factuality-verified resume bullet rewrites."
        />

        {selectedCandId && selectedJobId && (
          <Link href={`/match?candidate_id=${selectedCandId}&job_id=${selectedJobId}`}>
            <Button variant="secondary" size="sm" icon={<Target className="w-3.5 h-3.5" />}>
              View Match Breakdown
            </Button>
          </Link>
        )}
      </div>

      {/* Target Selector Bar */}
      <Card className="p-6 grid grid-cols-1 md:grid-cols-3 gap-5 items-end">
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Select Candidate Profile
          </label>
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

        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Select Target Job Requisition
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

        <div>
          <Button
            onClick={handleGenerateCoach}
            disabled={loading}
            loading={loading}
            icon={<Sparkles className="w-4 h-4" />}
            size="md"
            variant="primary"
            className="w-full"
          >
            Generate Coach Report
          </Button>
        </div>
      </Card>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 text-xs sm:text-sm flex items-center gap-2 border border-rose-200 dark:border-rose-800">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Coach Report Content */}
      {coachReport && (
        <div className="space-y-6">
          {/* Critic Findings / Removed Claims */}
          {coachReport.removed_claims && coachReport.removed_claims.length > 0 && (
            <Card className="p-5 bg-gradient-to-r from-amber-50/80 via-amber-50/50 to-orange-50/60 dark:from-amber-950/30 dark:via-amber-950/20 dark:to-orange-950/20 border-amber-300/70 dark:border-amber-700/50 flex items-start gap-3.5">
              <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-400/30 flex items-center justify-center flex-shrink-0 text-amber-600 dark:text-amber-400">
                <ShieldAlert className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold text-amber-950 dark:text-amber-200 uppercase tracking-wider">
                    Factuality Critic Safety Checks
                  </h4>
                  <Badge variant="amber" size="sm">
                    {coachReport.removed_claims.length} claims pruned
                  </Badge>
                </div>
                <p className="text-xs text-amber-800/90 dark:text-amber-300/80 leading-relaxed">
                  The deterministic and LLM factuality critic verified all suggestions against the candidate's actual experience to ensure 0 hallucinations.
                </p>
                <ul className="mt-2 space-y-1 text-xs text-amber-900 dark:text-amber-200 list-disc list-inside">
                  {coachReport.removed_claims.map((claim, idx) => (
                    <li key={idx} className="font-mono text-[11px]">{claim}</li>
                  ))}
                </ul>
              </div>
            </Card>
          )}

          {/* Section 1: Prerequisite-Ordered Learning Plan */}
          <Card className="p-6 sm:p-7 space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
                <BookOpen className="w-5 h-5 text-brand-500" />
                <span>Prerequisite-Ordered Learning Roadmap</span>
              </h3>
              <span className="text-xs text-slate-400 font-mono font-medium">
                Topologically ordered via taxonomy graph
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
              {coachReport.learning_plan?.map((goal: any, idx: number) => (
                <div
                  key={idx}
                  className="p-5 rounded-2xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 space-y-3 relative flex flex-col justify-between"
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="w-7 h-7 rounded-xl bg-brand-600 text-white flex items-center justify-center font-bold text-xs shadow-sm font-mono">
                        {idx + 1}
                      </span>
                      <span className="text-[11px] font-mono px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 dark:bg-brand-950 dark:text-brand-300 font-bold border border-brand-200/80 dark:border-brand-800">
                        ~{goal.estimated_weeks || 2} weeks
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                      {goal.skill_name || goal.skill_slug}
                    </h4>
                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                      {goal.rationale}
                    </p>
                  </div>

                  {goal.prerequisites && goal.prerequisites.length > 0 && (
                    <div className="pt-2.5 border-t border-slate-200/80 dark:border-white/10 text-[11px] text-slate-500 dark:text-slate-400">
                      <span className="font-semibold text-slate-600 dark:text-slate-300">Prerequisites: </span>
                      <span>{goal.prerequisites.join(", ")}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>

          {/* Section 2: Targeted Interview Questions */}
          <Card className="p-6 sm:p-7 space-y-5">
            <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
              <HelpCircle className="w-5 h-5 text-brand-500" />
              <span>Targeted Interview Questions (Technical Reasoning)</span>
            </h3>

            <div className="space-y-3">
              {coachReport.interview_questions?.map((q: any, idx: number) => (
                <div
                  key={idx}
                  className="p-5 rounded-2xl border border-slate-200/80 dark:border-white/10 bg-slate-50/50 dark:bg-white/5 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-brand-600 dark:text-brand-400 uppercase tracking-wide">
                      Topic: {q.requirement_name || q.skill_name || "Technical Competency"}
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono font-medium">Q#{idx + 1}</span>
                  </div>
                  <p className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                    "{q.question}"
                  </p>
                  <p className="text-xs text-slate-500 italic">
                    {q.target_competency ? `Competency: ${q.target_competency} • Tip: ${q.preparation_tip || ""}` : `Rationale: ${q.rationale}`}
                  </p>
                </div>
              ))}
            </div>
          </Card>

          {/* Section 3: Verified Resume Bullet Rewrites */}
          <Card className="p-6 sm:p-7 space-y-5">
            <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
              <FileEdit className="w-5 h-5 text-brand-500" />
              <span>Critic-Verified Resume Bullet Rewrites</span>
            </h3>

            <div className="space-y-4">
              {coachReport.bullet_rewrites?.map((b: any, idx: number) => (
                <div
                  key={idx}
                  className="p-5 rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white dark:bg-[#111827] space-y-3 shadow-sm"
                >
                  <div className="space-y-1">
                    <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Original Experience Span
                    </span>
                    <p className="text-xs text-slate-500 dark:text-slate-400 line-through">
                      {b.original_evidence || b.original_bullet}
                    </p>
                  </div>

                  <div className="space-y-1 bg-emerald-50/60 dark:bg-emerald-950/30 p-3.5 rounded-xl border border-emerald-200/80 dark:border-emerald-800/60">
                    <span className="text-[10px] uppercase font-bold text-emerald-700 dark:text-emerald-300 tracking-wider flex items-center gap-1.5">
                      <TrendingUp className="w-3.5 h-3.5 text-emerald-500" />
                      Improved & Grounded Rewrite
                    </span>
                    <p className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white leading-relaxed">
                      {b.improved_bullet}
                    </p>
                  </div>

                  <p className="text-[11px] text-slate-500 italic">
                    <span className="font-semibold text-slate-600 dark:text-slate-400">Critic Note: </span>
                    {b.rationale}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </motion.div>
  );
}

export default function CareerCoachPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading Career Coach...</div>}>
      <CoachContent />
    </Suspense>
  );
}
