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
} from "lucide-react";

export default function AboutPage() {
  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Architecture & System Design
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Production-grade semantic intelligence engine for enterprise resume parsing, skill normalization, explainable job matching, and career coaching.
        </p>
      </div>

      {/* System Pipeline Architecture Diagram */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Layers className="w-5 h-5 text-indigo-500" />
          <span>Multi-Agent System Architecture</span>
        </h3>

        {/* Visual Pipeline Block Diagram */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-2">
          {/* Stage 1 */}
          <div className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-900 bg-indigo-50/50 dark:bg-indigo-950/30 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-xs">
              01
            </div>
            <h4 className="font-bold text-sm text-indigo-950 dark:text-indigo-200">
              Parsing Agent
            </h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Hybrid PDF/DOCX extractor combining regex rules with verbatim-grounded LLM line ranges (Feature F2).
            </p>
          </div>

          {/* Stage 2 */}
          <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/50 dark:bg-blue-950/30 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs">
              02
            </div>
            <h4 className="font-bold text-sm text-blue-950 dark:text-blue-200">
              Normalization
            </h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Exact alias mapping, fuzzy token matching, and fine-tuned SentenceTransformer vector cascade into ESCO/O*NET DAG.
            </p>
          </div>

          {/* Stage 3 */}
          <div className="p-4 rounded-xl border border-emerald-200 dark:border-emerald-900 bg-emerald-50/50 dark:bg-emerald-950/30 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-xs">
              03
            </div>
            <h4 className="font-bold text-sm text-emerald-950 dark:text-emerald-200">
              Matching Agent
            </h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Multi-factor scoring: hard requirements, taxonomic depth distance, semantic similarity, and anti-bias blind screening.
            </p>
          </div>

          {/* Stage 4 */}
          <div className="p-4 rounded-xl border border-purple-200 dark:border-purple-900 bg-purple-50/50 dark:bg-purple-950/30 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-purple-600 text-white flex items-center justify-center font-bold text-xs">
              04
            </div>
            <h4 className="font-bold text-sm text-purple-950 dark:text-purple-200">
              Search Agent
            </h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Agentic query deconstruction with LangGraph tool loop, candidate filtering, and grounded citation ranking.
            </p>
          </div>

          {/* Stage 5 */}
          <div className="p-4 rounded-xl border border-amber-200 dark:border-amber-900 bg-amber-50/50 dark:bg-amber-950/30 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-amber-600 text-white flex items-center justify-center font-bold text-xs">
              05
            </div>
            <h4 className="font-bold text-sm text-amber-950 dark:text-amber-200">
              Career Coach
            </h4>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              Taxonomy prerequisite learning roadmap, interview questions, and factuality critic loop (0 hallucinations).
            </p>
          </div>
        </div>
      </div>

      {/* Architecture Decision Records (ADRs) */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-500" />
          <span>Architectural Decision Records (ADR Highlights)</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-1">
            <span className="text-[10px] font-mono font-bold text-indigo-600 dark:text-indigo-400">ADR-0001</span>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Hybrid Regex + Grounded LLM Extraction
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Short fields (name, email, phone) use deterministic rules; free text and roles reference numbered source line ranges to prevent token bloat and hallucination.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-1">
            <span className="text-[10px] font-mono font-bold text-indigo-600 dark:text-indigo-400">ADR-0002</span>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Hierarchical Normalization Cascade
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              3-tier pipeline: exact alias lookup (O(1)) &rarr; token fuzzy matching (rapidfuzz) &rarr; fine-tuned SentenceTransformer cosine nearest-neighbors in Chroma.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-1">
            <span className="text-[10px] font-mono font-bold text-indigo-600 dark:text-indigo-400">ADR-0003</span>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Subgraph Critic Loop with Revision Cap
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              The Coach agent runs a 2-stage critic (deterministic profile overlap check + LLM claim verification) capped at 2 revisions, removing ungrounded claims.
            </p>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-100 dark:border-slate-800 space-y-1">
            <span className="text-[10px] font-mono font-bold text-indigo-600 dark:text-indigo-400">ADR-0004</span>
            <h4 className="text-sm font-bold text-slate-900 dark:text-white">
              Server-Side API Key Isolation
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-300">
              Browser clients communicate solely with Next.js route handlers (/api/...), which inject the secret X-API-Key server-side, preventing client bundle leakage.
            </p>
          </div>
        </div>
      </div>

      {/* Tech Stack Specs */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <Cpu className="w-5 h-5 text-indigo-500" />
          <span>Technology Stack Specifications</span>
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs pt-1">
          <div>
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px] block">Backend API</span>
            <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">Python 3.12 / FastAPI</p>
            <p className="text-slate-500">Pydantic v2, SlowAPI, RFC 7807</p>
          </div>

          <div>
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px] block">Embeddings & Vector</span>
            <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">SentenceTransformers</p>
            <p className="text-slate-500">ChromaDB, all-MiniLM-L6-v2</p>
          </div>

          <div>
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px] block">Web Frontend</span>
            <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">Next.js 14 (App Router)</p>
            <p className="text-slate-500">React 18, Tailwind CSS, Lucide</p>
          </div>

          <div>
            <span className="font-semibold text-slate-400 uppercase tracking-wider text-[10px] block">Database & Storage</span>
            <p className="font-bold text-slate-800 dark:text-slate-200 mt-0.5">PostgreSQL / Redis</p>
            <p className="text-slate-500">SQLAlchemy 2.0 async, Alembic</p>
          </div>
        </div>
      </div>
    </div>
  );
}
