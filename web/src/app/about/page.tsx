"use client";

import { motion } from "framer-motion";
import {
  Layers,
  Cpu,
  ShieldCheck,
  Zap,
  GitBranch,
  FileText,
  Target,
  Search,
  Sparkles,
  BookOpen,
  CheckCircle2,
  Lock,
  Database,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";

const PIPELINE_STAGES = [
  {
    step: "01",
    title: "Parsing Agent",
    color: "from-brand-600 to-indigo-600",
    description: "Hybrid PDF/DOCX extractor combining regex rules with verbatim-grounded line ranges (Feature F2).",
  },
  {
    step: "02",
    title: "Normalization",
    color: "from-indigo-600 to-violet-600",
    description: "Exact alias mapping, fuzzy token matching, and fine-tuned SentenceTransformer cascade into ESCO/O*NET DAG.",
  },
  {
    step: "03",
    title: "Matching Agent",
    color: "from-violet-600 to-purple-600",
    description: "Multi-factor scoring: hard requirements, taxonomic depth distance, semantic similarity, and blind screening.",
  },
  {
    step: "04",
    title: "Search Agent",
    color: "from-purple-600 to-cyan-600",
    description: "Agentic query deconstruction with LangGraph tool loop, candidate filtering, and grounded citation ranking.",
  },
  {
    step: "05",
    title: "Career Coach",
    color: "from-cyan-600 to-emerald-600",
    description: "Taxonomy prerequisite learning roadmap, interview questions, and factuality critic loop (0 hallucinations).",
  },
];

const ADRS = [
  {
    id: "ADR-0001",
    title: "Hybrid Regex + Grounded LLM Extraction",
    text: "Short fields (name, email, phone) use deterministic rules; free text and roles reference numbered source line ranges to prevent token bloat and hallucination.",
  },
  {
    id: "ADR-0002",
    title: "Hierarchical Normalization Cascade",
    text: "3-tier pipeline: exact alias lookup (O(1)) → token fuzzy matching (rapidfuzz) → fine-tuned SentenceTransformer cosine nearest-neighbors in Chroma.",
  },
  {
    id: "ADR-0003",
    title: "Subgraph Critic Loop with Revision Cap",
    text: "The Coach agent runs a 2-stage critic (deterministic profile overlap check + LLM claim verification) capped at 2 revisions, removing ungrounded claims.",
  },
  {
    id: "ADR-0004",
    title: "Server-Side API Key Isolation",
    text: "Browser clients communicate solely with Next.js route handlers (/api/...), which inject the secret X-API-Key server-side, preventing client bundle leakage.",
  },
];

export default function AboutPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8 max-w-5xl mx-auto"
    >
      {/* Page Header */}
      <SectionHeader
        eyebrow="System Blueprint"
        eyebrowIcon={<Layers className="w-3.5 h-3.5" />}
        title="Architecture & System Design"
        gradientWord="System Design"
        subtitle="Production-grade semantic intelligence engine for enterprise resume parsing, skill normalization, explainable job matching, and career coaching."
      />

      {/* Multi-Agent Pipeline Diagram */}
      <Card className="p-6 sm:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
            <Layers className="w-5 h-5 text-brand-500" />
            <span>Multi-Agent System Architecture</span>
          </h3>
          <Badge variant="brand" size="sm">
            5 Modular Stages
          </Badge>
        </div>

        {/* Visual Pipeline Block Diagram */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3.5">
          {PIPELINE_STAGES.map((stg) => (
            <div
              key={stg.step}
              className="p-4 rounded-2xl border border-slate-200/80 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 space-y-2.5 flex flex-col justify-between hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
            >
              <div className="space-y-2">
                <div
                  className={`w-8 h-8 rounded-xl bg-gradient-to-tr ${stg.color} text-white flex items-center justify-center font-bold text-xs font-mono shadow-sm`}
                >
                  {stg.step}
                </div>
                <h4 className="font-bold text-sm text-slate-900 dark:text-white">
                  {stg.title}
                </h4>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                {stg.description}
              </p>
            </div>
          ))}
        </div>
      </Card>

      {/* Architecture Decision Records (ADRs) */}
      <Card className="p-6 sm:p-8 space-y-6">
        <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
          <ShieldCheck className="w-5 h-5 text-brand-500" />
          <span>Architectural Decision Records (ADR Highlights)</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {ADRS.map((adr) => (
            <div
              key={adr.id}
              className="p-5 rounded-2xl bg-slate-50/70 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 space-y-2 hover:border-brand-300 dark:hover:border-brand-700 transition-colors"
            >
              <span className="text-[11px] font-mono font-bold text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950 px-2 py-0.5 rounded-md border border-brand-200 dark:border-brand-800">
                {adr.id}
              </span>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                {adr.title}
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                {adr.text}
              </p>
            </div>
          ))}
        </div>
      </Card>

      {/* Tech Stack Specs */}
      <Card className="p-6 sm:p-8 space-y-5">
        <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
          <Cpu className="w-5 h-5 text-brand-500" />
          <span>Technology Stack Specifications</span>
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs pt-1">
          <div className="p-4 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 space-y-1">
            <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px] block">Backend API</span>
            <p className="font-bold text-slate-900 dark:text-white text-sm">Python 3.12 / FastAPI</p>
            <p className="text-slate-500 dark:text-slate-400 text-[11px]">Pydantic v2, SlowAPI, RFC 7807</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 space-y-1">
            <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px] block">Embeddings & Vector</span>
            <p className="font-bold text-slate-900 dark:text-white text-sm">SentenceTransformers</p>
            <p className="text-slate-500 dark:text-slate-400 text-[11px]">ChromaDB, all-MiniLM-L6-v2</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 space-y-1">
            <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px] block">Web Frontend</span>
            <p className="font-bold text-slate-900 dark:text-white text-sm">Next.js 14 App Router</p>
            <p className="text-slate-500 dark:text-slate-400 text-[11px]">React 18, Tailwind, Framer Motion</p>
          </div>

          <div className="p-4 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 space-y-1">
            <span className="font-bold text-slate-400 uppercase tracking-wider text-[10px] block">Database & Storage</span>
            <p className="font-bold text-slate-900 dark:text-white text-sm">PostgreSQL / Redis</p>
            <p className="text-slate-500 dark:text-slate-400 text-[11px]">SQLAlchemy 2.0 async, Alembic</p>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
