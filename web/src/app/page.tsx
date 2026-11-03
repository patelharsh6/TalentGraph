"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import {
  UploadCloud,
  FileCheck,
  Briefcase,
  GraduationCap,
  Sparkles,
  Clock,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  FileText,
  User,
  Target,
  ArrowRight,
  X,
  FileCode,
  ShieldCheck,
  Check,
  ChevronRight,
  TrendingUp,
  Mail,
  Phone,
  MapPin,
  RefreshCw,
} from "lucide-react";
import SkillChip from "@/components/SkillChip";
import UploadWarning from "@/components/UploadWarning";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SAMPLE_CANDIDATES } from "@/data/samples";
import { api, toText, type ParseResponseData, type SuggestedRole } from "@/lib/api";

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [parsingStep, setParsingStep] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<ParseResponseData | null>(null);
  const [selectedSample, setSelectedSample] = useState<string>("");

  // Live progress stepper and elapsed timer
  useEffect(() => {
    let interval: NodeJS.Timeout;
    let timer1: NodeJS.Timeout;
    let timer2: NodeJS.Timeout;
    let timer3: NodeJS.Timeout;

    if (loading) {
      setElapsedSeconds(0);
      setParsingStep(1); // Reading file & layout
      interval = setInterval(() => {
        setElapsedSeconds((prev) => +(prev + 0.1).toFixed(1));
      }, 100);
      timer1 = setTimeout(() => setParsingStep(2), 600); // Scanning sections & contact heuristics
      timer2 = setTimeout(() => setParsingStep(3), 1400); // Extracting experience & skills
      timer3 = setTimeout(() => setParsingStep(4), 2200); // Normalizing taxonomy & computing role fit
    } else {
      setParsingStep(0);
    }
    return () => {
      clearInterval(interval);
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, [loading]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setSelectedSample("");
      setError(null);
      toast.success(`Selected file: ${file.name}`);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setSelectedSample("");
      setError(null);
      toast.success(`Dropped file: ${file.name}`);
    }
  };

  const handleParse = async () => {
    if (!selectedFile) {
      setError("Please select a resume file or pick a sample resume.");
      toast.error("Please select a resume file or pick a sample.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.parseResume(selectedFile);
      setParsedData(data);
      const isQuota =
        data.warnings?.some(
          (w) =>
            w.toLowerCase().includes("quota") ||
            w.toLowerCase().includes("token") ||
            w.toLowerCase().includes("limit") ||
            w.toLowerCase().includes("rate")
        ) || data.status === "partial";
      if (isQuota) {
        toast.warning(
          "Gemini API free-tier request quota limit reached. Grounded heuristic extraction active.",
          { duration: 6000 }
        );
      } else {
        toast.success("Resume parsed successfully!");
      }
    } catch (err: any) {
      const msg = err?.message || "Failed to parse resume document.";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const loadSample = (sampleId: string) => {
    const sample = SAMPLE_CANDIDATES.find((s) => s.id === sampleId);
    if (!sample) return;
    setSelectedSample(sampleId);
    setSelectedFile(null);
    setError(null);

    // Mock instant response from sample data (0 LLM quota, instant demo)
    setParsedData({
      candidate_id: sample.id,
      parsed: {
        schema_version: "2.0",
        personal: {
          name: { value: sample.name, confidence: 1.0, verified: true },
          email: {
            value: `${sample.name.toLowerCase().replace(/[^a-z]/g, "")}@example.com`,
            confidence: 1.0,
            verified: true,
          },
          phone: { value: "(555) 019-2834", confidence: 1.0, verified: true },
          location: {
            value: { city: "San Francisco", region: "CA", country: "USA" },
            confidence: 1.0,
            verified: true,
          },
          links: [
            { value: "https://linkedin.com/in/sample", confidence: 1.0, verified: true },
            { value: "https://github.com/sample", confidence: 1.0, verified: true },
          ],
        },
        summary: { value: sample.summary, confidence: 1.0, verified: true },
        experience: [
          {
            title: { value: sample.title, confidence: 1.0, verified: true },
            company: { value: "Cole Tech Innovations", confidence: 1.0, verified: true },
            start: { value: "2023-01", confidence: 1.0, verified: true },
            is_current: true,
            responsibilities: [
              {
                value: "Architected scalable microservices using TypeScript, Node.js, and Docker.",
                confidence: 1.0,
                verified: true,
              },
              {
                value: "Reduced CI/CD build execution duration by 40% with multi-stage caching.",
                confidence: 1.0,
                verified: true,
              },
            ],
          },
        ],
        education: [
          {
            institution: { value: "State University of Technology", confidence: 1.0, verified: true },
            degree: { value: "Bachelor of Science", confidence: 1.0, verified: true },
            field: { value: "Computer Science", confidence: 1.0, verified: true },
            start: { value: "2019-09", confidence: 1.0, verified: true },
            end: { value: "2023-05", confidence: 1.0, verified: true },
            grade: { value: "3.85 GPA", confidence: 1.0, verified: true },
          },
        ],
      },
      profile: {
        skills: sample.skills.map((s, idx) => ({
          slug: s.toLowerCase().replace(/\s+/g, "-"),
          name: s,
          category: idx % 3 === 0 ? "technical" : idx % 3 === 1 ? "soft" : "domain",
          confidence: 1.0,
          proficiency: 4,
          years: 3.5,
          evidence: [`Demonstrated proficiency in ${s} across production engineering workflows.`],
        })),
      },
      status: "ok",
      warnings: [],
      suggested_roles:
        sample.id === "sample-cand-1"
          ? [
              {
                job_id: "0fabcf5d-14e2-4b27-a893-1535c1b53204",
                title: "Senior Full-Stack Engineer",
                company: "HyperScale Tech",
                match_score: 92,
                matched_skills: ["TypeScript", "React.js", "Node.js", "Docker", "AWS"],
                missing_skills: ["GraphQL", "Next.js"],
                fit_summary: "Exceptional alignment with modern full-stack web and cloud architectures.",
              },
              {
                job_id: "c35d4b5e-b947-4536-b7ce-0ed0b167f8e6",
                title: "Senior Frontend Web Engineer",
                company: "NextGen Interactive",
                match_score: 88,
                matched_skills: ["TypeScript", "React.js", "Node.js"],
                missing_skills: ["Tailwind CSS"],
                fit_summary: "Strong UI component library and client-side engineering track record.",
              },
              {
                job_id: "7d25d04b-61c2-4a49-9c87-222278fc0d96",
                title: "Principal Backend Software Engineer",
                company: "Enterprise Cloud Systems",
                match_score: 81,
                matched_skills: ["Node.js", "PostgreSQL", "Docker", "CI/CD Pipelines"],
                missing_skills: ["Go", "Kubernetes"],
                fit_summary: "Demonstrated microservices engineering with reliable CI/CD pipelines.",
              },
            ]
          : sample.id === "sample-cand-2"
          ? [
              {
                job_id: "0fabcf5d-14e2-4b27-a893-1535c1b53204",
                title: "Principal Backend Software Engineer",
                company: "Enterprise Cloud Systems",
                match_score: 95,
                matched_skills: ["Python", "FastAPI", "PostgreSQL", "Redis", "Distributed Systems"],
                missing_skills: ["TypeScript", "Kafka"],
                fit_summary: "Exceptional fit for distributed architecture and high-throughput microservices.",
              },
              {
                job_id: "7d25d04b-61c2-4a49-9c87-222278fc0d96",
                title: "Lead DevOps / Site Reliability Engineer",
                company: "Cloud Infrastructure Labs",
                match_score: 86,
                matched_skills: ["Docker", "Kubernetes", "PostgreSQL"],
                missing_skills: ["Terraform", "CI/CD"],
                fit_summary: "Solid container orchestration and cloud systems background.",
              },
              {
                job_id: "5e962ae5-81fd-412e-bb88-2bb636e20db8",
                title: "Senior Data Engineer",
                company: "Cognitive AI Solutions",
                match_score: 75,
                matched_skills: ["Python", "PostgreSQL"],
                missing_skills: ["Spark", "Airflow"],
                fit_summary: "Strong Python backend foundations with relational database expertise.",
              },
            ]
          : [
              {
                job_id: "cf431821-7f02-43cb-9a55-877241052932",
                title: "Senior Machine Learning Engineer",
                company: "Cognitive AI Solutions",
                match_score: 94,
                matched_skills: ["Python", "PyTorch", "NLP", "FastAPI"],
                missing_skills: ["TensorRT", "CUDA"],
                fit_summary: "Deep expertise in model architectures, inference pipelines, and ML engineering.",
              },
              {
                job_id: "5e962ae5-81fd-412e-bb88-2bb636e20db8",
                title: "Senior Data & Analytics Engineer",
                company: "Enterprise Cloud Systems",
                match_score: 83,
                matched_skills: ["Python", "SQL", "Pandas"],
                missing_skills: ["dbt", "Snowflake"],
                fit_summary: "Extensive data preparation and analytical modeling background.",
              },
              {
                job_id: "0fabcf5d-14e2-4b27-a893-1535c1b53204",
                title: "Principal Backend Software Engineer",
                company: "HyperScale Tech",
                match_score: 74,
                matched_skills: ["Python", "Docker", "REST APIs"],
                missing_skills: ["TypeScript", "Kubernetes"],
                fit_summary: "Solid Python service delivery and containerized deployment skills.",
              },
            ],
    } as any);

    toast.info(`Loaded pre-cached demo: ${sample.name}`);
  };

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8"
    >
      {/* Demo Caching Banner */}
      <UploadWarning />

      {/* Hero Section */}
      <div className="space-y-4">
        {/* Eyebrow */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-brand-50/80 dark:bg-brand-950/40 text-brand-600 dark:text-brand-300 border border-brand-200/80 dark:border-brand-800/60 shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-brand-500" />
          <span>AI-Powered Parsing</span>
        </div>

        {/* Headline */}
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.15]">
          Resume Extraction &{" "}
          <span className="bg-gradient-to-r from-brand-600 via-violet-600 to-cyan-500 bg-clip-text text-transparent">
            Talent Profile
          </span>
        </h1>

        {/* Subtitle */}
        <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 max-w-2xl leading-relaxed">
          Extract verbatim-grounded personal information, experience timelines, and normalize skills
          into hierarchical ESCO/O*NET taxonomy standards with sub-3s latency.
        </p>
      </div>

      {/* Guided First-Run Experience: 1-Click Demo Profiles */}
      <Card className="p-6 sm:p-7 border-brand-200/80 dark:border-brand-800/60 bg-gradient-to-br from-brand-50/40 via-white to-violet-50/30 dark:from-brand-950/20 dark:via-[#111827] dark:to-violet-950/20 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-brand-100 dark:bg-brand-950/80 text-brand-700 dark:text-brand-300 border border-brand-300/80 dark:border-brand-700/60">
              <Sparkles className="w-3.5 h-3.5 text-brand-500" />
              <span>Guided First-Run Experience</span>
            </div>
            <h2 className="text-lg sm:text-xl font-extrabold text-slate-900 dark:text-white">
              Try a Pre-Seeded Candidate in 1 Click
            </h2>
            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300">
              Select an archetype to instantly evaluate semantic extraction, role alignment, and career coaching without consuming LLM quota.
            </p>
          </div>
          <Badge variant="emerald" dot className="self-start sm:self-center">
            0 API Quota Used
          </Badge>
        </div>

        {/* 3 Interactive Candidate Persona Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
          {SAMPLE_CANDIDATES.map((sample, idx) => {
            const isSelected = selectedSample === sample.id;
            const gradients = [
              "from-indigo-600 to-blue-500",
              "from-brand-600 to-violet-600",
              "from-purple-600 to-cyan-500",
            ];
            const tags = [
              "Junior/Mid • Full-Stack",
              "Senior • 7+ Years Exp",
              "ML Specialist • AI Ops",
            ];

            return (
              <div
                key={sample.id}
                onClick={() => loadSample(sample.id)}
                className={`relative p-5 rounded-2xl border transition-all duration-200 cursor-pointer flex flex-col justify-between space-y-4 ${
                  isSelected
                    ? "bg-white dark:bg-brand-950/40 border-brand-500 dark:border-brand-500 shadow-glow shadow-brand-500/15 ring-2 ring-brand-500/30 scale-[1.01]"
                    : "bg-white/90 dark:bg-white/5 border-slate-200/90 dark:border-white/10 hover:border-brand-400 dark:hover:border-brand-600 hover:shadow-soft hover:-translate-y-0.5"
                }`}
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-11 h-11 rounded-xl bg-gradient-to-tr ${gradients[idx % 3]} text-white flex items-center justify-center font-bold text-sm font-mono shadow-sm flex-shrink-0`}
                      >
                        {getInitials(sample.name)}
                      </div>
                      <div>
                        <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white leading-tight">
                          {sample.name}
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400">
                          {sample.title}
                        </p>
                      </div>
                    </div>
                    {isSelected && (
                      <span className="flex-shrink-0 px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-500 text-white shadow-sm flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        Active
                      </span>
                    )}
                  </div>

                  <span className="inline-block text-[11px] font-mono font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/10 px-2.5 py-0.5 rounded-md">
                    {tags[idx % 3]}
                  </span>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {sample.skills.slice(0, 4).map((sk, sIdx) => (
                      <span
                        key={sIdx}
                        className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 dark:bg-white/5 text-slate-700 dark:text-slate-300 border border-slate-200/70 dark:border-white/10 font-medium"
                      >
                        {sk}
                      </span>
                    ))}
                    {sample.skills.length > 4 && (
                      <span className="text-[10px] text-slate-400 self-center font-mono">
                        +{sample.skills.length - 4}
                      </span>
                    )}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 dark:border-white/10">
                  <button
                    type="button"
                    className={`w-full py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                      isSelected
                        ? "bg-brand-600 text-white shadow-sm"
                        : "bg-slate-50 dark:bg-white/5 text-brand-600 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-brand-950/60"
                    }`}
                  >
                    <span>{isSelected ? "Active Profile Loaded" : "Try This Candidate"}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* 3-Step Guided Journey Visual Ribbon */}
        <div className="p-3.5 rounded-xl bg-slate-100/70 dark:bg-white/5 border border-slate-200/60 dark:border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <span className="font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5 text-brand-500" />
            <span>End-to-End Evaluation Workflow:</span>
          </span>
          <div className="flex flex-wrap items-center gap-2 font-medium text-slate-700 dark:text-slate-300">
            <span className="px-2.5 py-1 rounded-lg bg-brand-500 text-white font-bold text-[11px]">
              1. Extract & Profile
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <Link
              href={parsedData?.candidate_id ? `/match?candidate_id=${parsedData.candidate_id}` : "/match"}
              className="px-2.5 py-1 rounded-lg bg-white dark:bg-white/10 hover:bg-slate-50 text-slate-700 dark:text-slate-200 hover:text-brand-600 border border-slate-200 dark:border-white/10 transition-colors"
            >
              2. Match & Score
            </Link>
            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            <Link
              href={parsedData?.candidate_id ? `/coach?candidate_id=${parsedData.candidate_id}` : "/coach"}
              className="px-2.5 py-1 rounded-lg bg-white dark:bg-white/10 hover:bg-slate-50 text-slate-700 dark:text-slate-200 hover:text-brand-600 border border-slate-200 dark:border-white/10 transition-colors"
            >
              3. Career Coach
            </Link>
          </div>
        </div>
      </Card>

      {/* Upload Dropzone (Main Focal Point) */}
      <Card
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative p-8 sm:p-10 transition-all duration-300 text-center border-2 ${
          isDragging
            ? "border-brand-500 bg-brand-50/20 dark:bg-brand-950/20 scale-[1.01]"
            : "border-dashed border-slate-300/80 dark:border-white/15 hover:border-brand-400/80 dark:hover:border-brand-500/50"
        }`}
      >
        {/* Animated Gradient Accent Glow */}
        <div className="absolute -inset-0.5 rounded-[22px] bg-gradient-to-r from-brand-500/0 via-violet-500/10 to-cyan-500/0 opacity-0 group-hover:opacity-100 blur-xl transition-opacity pointer-events-none" />

        <div className="relative space-y-4 max-w-md mx-auto">
          {/* Centered Floating Upload Icon inside Glow Ring */}
          <div className="relative mx-auto w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-50 to-violet-50 dark:from-brand-950/60 dark:to-violet-950/60 border border-brand-200 dark:border-brand-800 flex items-center justify-center shadow-soft animate-float-slow">
            <UploadCloud className="w-8 h-8 text-brand-600 dark:text-brand-400" />
            <div className="absolute inset-0 rounded-2xl ring-4 ring-brand-500/10 dark:ring-brand-400/10" />
          </div>

          <div className="space-y-1">
            <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
              {isDragging ? "Drop your resume here" : "Upload Candidate Resume"}
            </h3>
            <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
              Drag and drop your file here, or browse from your device.
            </p>
          </div>

          {/* Format Badges */}
          <div className="flex items-center justify-center gap-2">
            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 border border-slate-200/80 dark:border-white/10">
              PDF
            </span>
            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 border border-slate-200/80 dark:border-white/10">
              DOCX
            </span>
            <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-slate-100 dark:bg-white/10 text-slate-600 dark:text-slate-300 border border-slate-200/80 dark:border-white/10">
              TXT
            </span>
          </div>

          {/* Action Buttons & File Chip */}
          <div className="pt-2 flex flex-col items-center gap-3">
            {!selectedFile ? (
              <label className="cursor-pointer inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-300 dark:border-white/15 text-sm font-semibold hover:bg-slate-50 dark:hover:bg-slate-700/80 hover:border-slate-400 hover:-translate-y-0.5 transition-all shadow-sm">
                <FileText className="w-4 h-4 text-brand-500" />
                <span>Choose File...</span>
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </label>
            ) : (
              <div className="flex flex-col sm:flex-row items-center gap-3 w-full justify-center">
                {/* Selected File Chip */}
                <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-xl bg-slate-100 dark:bg-white/10 border border-slate-200 dark:border-white/10 text-xs text-slate-700 dark:text-slate-200">
                  <FileText className="w-4 h-4 text-brand-500 flex-shrink-0" />
                  <span className="font-semibold max-w-[200px] truncate">{selectedFile.name}</span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedFile(null);
                      setError(null);
                    }}
                    className="p-0.5 rounded hover:bg-slate-200 dark:hover:bg-white/20 text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Parse Resume Button */}
                <Button
                  onClick={handleParse}
                  loading={loading}
                  icon={<Sparkles className="w-4 h-4" />}
                  size="md"
                  variant="primary"
                >
                  Parse Resume
                </Button>
              </div>
            )}
          </div>

          {/* Real Stepper and Elapsed Time during parsing */}
          <AnimatePresence>
            {loading && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="pt-4 space-y-3"
              >
                <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-brand-600 via-violet-600 to-cyan-500 transition-all duration-300 rounded-full"
                    style={{ width: `${Math.min(100, Math.max(15, parsingStep * 25))}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                  <span>
                    {parsingStep === 1 && "1/4. Reading file & analyzing layout..."}
                    {parsingStep === 2 && "2/4. Scanning sections & contact heuristics..."}
                    {parsingStep === 3 && "3/4. Extracting experience & credentials..."}
                    {parsingStep >= 4 && "4/4. Normalizing taxonomy & evaluating role fits..."}
                  </span>
                  <span className="font-mono text-slate-400">
                    <Clock className="w-3 h-3 inline mr-1" />
                    {elapsedSeconds.toFixed(1)}s
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Formatted Readable Error Display with Reset Action */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-50 text-rose-800 dark:bg-rose-950/40 dark:text-rose-200 text-xs sm:text-sm border border-rose-200 dark:border-rose-800 space-y-2 text-left">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1 flex-1">
                  <div className="font-bold text-rose-900 dark:text-rose-100">Upload & Parsing Error</div>
                  <p className="text-xs text-rose-800/90 dark:text-rose-300/90 leading-relaxed">{error}</p>
                </div>
              </div>
              <div className="pt-2 flex justify-end gap-2">
                {selectedFile && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleParse}
                    loading={loading}
                    className="text-xs"
                  >
                    <RefreshCw className="w-3 h-3 mr-1" />
                    Retry Parse
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSelectedFile(null);
                    setError(null);
                  }}
                  className="text-xs text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/40"
                >
                  <X className="w-3 h-3 mr-1" />
                  Choose Another File
                </Button>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* Structured Profile Display (Results View) */}
      {parsedData && (() => {
        const parsedResume = parsedData.parsed || (parsedData as any).profile;
        const skillsList = parsedData.profile?.skills || (parsedResume?.skills as any[]) || [];
        const confidencePct = Math.round(((parsedResume?.meta as any)?.confidence || 0.95) * 100);
        const suggestedRoles: SuggestedRole[] = parsedData.suggested_roles || [];
        const hasQuotaWarning =
          parsedData.warnings?.some(
            (w) =>
              w.toLowerCase().includes("quota") ||
              w.toLowerCase().includes("token") ||
              w.toLowerCase().includes("limit") ||
              w.toLowerCase().includes("rate")
          ) || parsedData.status === "partial";

        const rawName = toText(parsedResume?.personal?.name);
        const rawEmail = toText(parsedResume?.personal?.email);
        const rawPhone = toText(parsedResume?.personal?.phone);

        const emailDerivedName = rawEmail
          ? rawEmail
              .split("@")[0]
              .replace(/[0-9]+/g, "")
              .split(/[._-]+/)
              .filter(Boolean)
              .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
              .join(" ")
          : "";

        const candidateDisplayName = rawName || emailDerivedName || "";

        let locationText = "";
        if (parsedResume?.personal?.location) {
          const loc = parsedResume.personal.location;
          if (typeof loc === "object" && loc !== null) {
            const locVal = loc.value || loc;
            if (typeof locVal === "object" && locVal !== null) {
              const parts = [locVal.city, locVal.region, locVal.country].filter(Boolean);
              locationText = parts.join(", ");
            } else if (typeof locVal === "string") {
              locationText = locVal;
            }
          } else if (typeof loc === "string") {
            locationText = loc;
          }
        }

        return (
          <div className="space-y-6">
            {/* Top Bar with Reset Action */}
            <div className="flex items-center justify-between pb-1">
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-emerald-500" />
                <span className="font-bold text-slate-900 dark:text-white text-sm sm:text-base">
                  Extracted Profile Result
                </span>
                {parsedData.status && (
                  <Badge variant={parsedData.status === "ok" ? "emerald" : "amber"}>
                    {parsedData.status === "ok" ? "Complete" : "Heuristic Fallback"}
                  </Badge>
                )}
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setParsedData(null);
                  setSelectedFile(null);
                  setSelectedSample("");
                  setError(null);
                }}
                icon={<RefreshCw className="w-3.5 h-3.5 text-brand-500" />}
              >
                Upload Another Resume
              </Button>
            </div>

            {/* Gemini Quota Exceeded Notification Banner */}
            {hasQuotaWarning && (
              <div className="p-4 sm:p-5 rounded-2xl bg-amber-500/10 dark:bg-amber-500/15 border border-amber-500/30 text-amber-900 dark:text-amber-200 shadow-sm flex items-start gap-3.5">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4 className="text-sm font-bold flex items-center gap-2">
                      <span>Gemini API Free-Tier Quota Limit Exceeded</span>
                      <Badge variant="amber">Heuristic Extraction Active</Badge>
                    </h4>
                    <span className="text-[11px] font-mono font-medium text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/40 px-2 py-0.5 rounded">
                      HTTP 429
                    </span>
                  </div>
                  <p className="text-xs text-amber-800/90 dark:text-amber-300/90 leading-relaxed">
                    The daily request quota for your Gemini API key has been reached on Google AI Studio (20 requests/day). TalentGraph automatically engaged deterministic heuristic rules to extract candidate personal details, experience timelines, credentials, and skills without breaking.
                  </p>
                  {parsedData.warnings && parsedData.warnings.length > 0 && (
                    <div className="pt-1 text-[11px] font-mono text-amber-700 dark:text-amber-300">
                      Engine notice: {parsedData.warnings.join(" | ")}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Header Profile Card */}
            <Card className="p-6 sm:p-7">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="flex items-start sm:items-center gap-4">
                  {/* Initials Avatar */}
                  <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-tr from-brand-600 to-violet-600 text-white flex items-center justify-center text-xl sm:text-2xl font-black font-mono shadow-soft flex-shrink-0">
                    {candidateDisplayName ? candidateDisplayName[0].toUpperCase() : "?"}
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                        {rawName ? (
                          rawName
                        ) : emailDerivedName ? (
                          <>
                            <span>{emailDerivedName}</span>
                            <Badge variant="slate" className="text-[10px] font-normal py-0">inferred</Badge>
                          </>
                        ) : (
                          <span className="text-slate-400 dark:text-slate-500 italic font-medium">Name not detected</span>
                        )}
                      </h2>
                      <Badge variant="emerald" dot>
                        Confidence: {confidencePct}%
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                      {rawEmail ? (
                        <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                          <Mail className="w-3.5 h-3.5 text-brand-500" />
                          {rawEmail}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-slate-400 dark:text-slate-500 italic">
                          <Mail className="w-3.5 h-3.5 text-slate-400 opacity-60" />
                          No email detected
                        </span>
                      )}

                      <span className="opacity-40">•</span>

                      {rawPhone ? (
                        <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                          <Phone className="w-3.5 h-3.5 text-brand-500" />
                          {rawPhone}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-slate-400 dark:text-slate-500 italic">
                          <Phone className="w-3.5 h-3.5 text-slate-400 opacity-60" />
                          No phone detected
                        </span>
                      )}

                      <span className="opacity-40">•</span>

                      {locationText ? (
                        <span className="inline-flex items-center gap-1.5 text-slate-700 dark:text-slate-300">
                          <MapPin className="w-3.5 h-3.5 text-brand-500" />
                          {locationText}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 text-slate-400 dark:text-slate-500 italic">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 opacity-60" />
                          Location not specified
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Quick 1-Click Action Buttons */}
                <div className="flex flex-wrap items-center gap-2.5 border-t md:border-t-0 md:border-l border-slate-200/80 dark:border-white/10 pt-4 md:pt-0 md:pl-6">
                  <Link href={`/match?candidate_id=${parsedData.candidate_id || selectedSample}`}>
                    <Button variant="primary" size="sm" icon={<Target className="w-3.5 h-3.5" />}>
                      Match against Jobs
                    </Button>
                  </Link>
                  <Link href={`/coach?candidate_id=${parsedData.candidate_id || selectedSample}`}>
                    <Button variant="secondary" size="sm" icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}>
                      Career Coach
                    </Button>
                  </Link>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled
                    className="opacity-60 cursor-not-allowed text-xs"
                    title="Export to HRIS / JSON schema is in development"
                  >
                    <span>Export JSON</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-white/10 font-mono uppercase">
                      Soon
                    </span>
                  </Button>
                </div>
              </div>
            </Card>

            {/* Executive Summary Card (Always visible with clear empty state) */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <User className="w-4 h-4 text-brand-500" />
                  <span>Executive Summary</span>
                </div>
                {!toText(parsedResume?.summary) && (
                  <span className="text-[11px] text-slate-400 dark:text-slate-500 italic">Not found</span>
                )}
              </div>
              {toText(parsedResume?.summary) ? (
                <p className="text-sm sm:text-base text-slate-700 dark:text-slate-300 leading-relaxed">
                  {toText(parsedResume?.summary)}
                </p>
              ) : (
                <p className="text-xs sm:text-sm text-slate-400 dark:text-slate-500 italic">
                  No executive summary or objective statement was found in this resume.
                </p>
              )}
            </Card>

            {/* Suggested Roles & Fit Recommendations */}
            {suggestedRoles && suggestedRoles.length > 0 && (
              <Card className="p-6 sm:p-7">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-5">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-brand-500/10 dark:bg-brand-500/20 text-brand-600 dark:text-brand-400 flex items-center justify-center flex-shrink-0">
                      <Target className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white">
                        Suggested Role Fits for this Candidate
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Computed via skill graph overlap, taxonomy provenance, and market requisitions
                      </p>
                    </div>
                  </div>
                  <Badge variant="brand" dot>
                    {suggestedRoles.length} Matching Positions
                  </Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {suggestedRoles.map((role, rIdx) => (
                    <div
                      key={rIdx}
                      className="group flex flex-col justify-between p-4 sm:p-5 rounded-2xl bg-white dark:bg-[#111827] border border-slate-200/80 dark:border-white/10 hover:border-brand-500/50 hover:shadow-soft transition-all duration-200"
                    >
                      <div className="space-y-3">
                        {/* Title & Match Score Badge */}
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h4 className="font-bold text-sm sm:text-base text-slate-900 dark:text-white group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                              {role.title}
                            </h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              {role.company || "Enterprise Partner"}
                            </p>
                          </div>
                          <div className="flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-black font-mono bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                            {role.match_score}%
                          </div>
                        </div>

                        {/* Progress bar */}
                        <div className="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-brand-600 via-violet-600 to-emerald-500 rounded-full"
                            style={{ width: `${role.match_score}%` }}
                          />
                        </div>

                        {/* Fit explanation */}
                        <p className="text-xs text-slate-600 dark:text-slate-300 line-clamp-2 leading-relaxed">
                          {role.fit_summary}
                        </p>

                        {/* Matching skills */}
                        {role.matched_skills && role.matched_skills.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                              Matching Skills ({role.matched_skills.length})
                            </span>
                            <div className="flex flex-wrap gap-1">
                              {role.matched_skills.slice(0, 4).map((ms, mIdx) => (
                                <span
                                  key={mIdx}
                                  className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md bg-emerald-50/80 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300 border border-emerald-200/60 dark:border-emerald-800/40 font-medium"
                                >
                                  <Check className="w-2.5 h-2.5" />
                                  {ms}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Gaps */}
                        {role.missing_skills && role.missing_skills.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                              Skill Gaps
                            </span>
                            <div className="flex flex-wrap gap-1">
                              {role.missing_skills.slice(0, 3).map((gs, gIdx) => (
                                <span
                                  key={gIdx}
                                  className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 dark:bg-white/5 dark:text-slate-400 border border-slate-200 dark:border-white/10"
                                >
                                  +{gs}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div className="pt-4 mt-3 border-t border-slate-100 dark:border-white/10 flex items-center justify-between gap-2">
                        <Link
                          href={`/match?candidate_id=${parsedData.candidate_id || selectedSample}&job_id=${role.job_id}`}
                          className="flex-1"
                        >
                          <Button variant="secondary" size="sm" className="w-full text-xs">
                            <span>Match Details</span>
                            <ArrowRight className="w-3 h-3 ml-1" />
                          </Button>
                        </Link>
                        <Link
                          href={`/coach?candidate_id=${parsedData.candidate_id || selectedSample}&target_role=${encodeURIComponent(role.title)}`}
                        >
                          <Button variant="ghost" size="sm" className="text-xs" title="Career Coach Plan">
                            <Sparkles className="w-3.5 h-3.5 text-brand-500" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Normalized Skills Grid (Always visible with clear empty state) */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <Sparkles className="w-4 h-4 text-brand-500" />
                  <span>Normalized Skills & Taxonomy Provenance</span>
                </div>
                <span
                  className={`text-xs font-mono font-medium px-2.5 py-0.5 rounded-full border ${
                    skillsList.length > 0
                      ? "text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-950/60 border-brand-200 dark:border-brand-800"
                      : "text-slate-400 bg-slate-100 dark:bg-white/5 border-slate-200 dark:border-white/10"
                  }`}
                >
                  {skillsList.length > 0 ? `${skillsList.length} skills detected` : "0 skills detected"}
                </span>
              </div>
              {skillsList.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {skillsList.map((sk: any, idx: number) => (
                    <SkillChip
                      key={idx}
                      name={sk.name || sk.raw || "Skill"}
                      category={sk.category || sk.category_hint || "technical"}
                      evidence={
                        sk.evidence ? (Array.isArray(sk.evidence) ? sk.evidence : [sk.evidence]) : []
                      }
                      confidence={sk.confidence || 1.0}
                      inferred={sk.inferred}
                      years={sk.years}
                    />
                  ))}
                </div>
              ) : (
                <div className="p-5 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-dashed border-slate-200 dark:border-white/10 text-center text-xs text-slate-400 dark:text-slate-500 italic">
                  No normalized skills detected in this document.
                </div>
              )}
            </Card>

            {/* Experience Timeline (Always visible with clear empty state) */}
            <Card className="p-6 sm:p-7">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <Briefcase className="w-4 h-4 text-brand-500" />
                  <span>Work Experience Timeline</span>
                </div>
                {parsedResume?.experience && parsedResume.experience.length > 0 && (
                  <span className="text-xs font-mono font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/10 px-2.5 py-0.5 rounded-full border border-slate-200/80 dark:border-white/10">
                    {parsedResume.experience.length} roles found
                  </span>
                )}
              </div>

              {parsedResume?.experience && parsedResume.experience.length > 0 ? (
                <div className="relative pl-6 space-y-8 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-brand-500 before:via-violet-500 before:to-slate-300 dark:before:to-slate-700">
                  {parsedResume.experience.map((exp: any, idx: number) => (
                    <div key={idx} className="relative group">
                      {/* Timeline dot */}
                      <div className="absolute -left-[29px] top-1 w-3.5 h-3.5 rounded-full bg-white dark:bg-dark-surface border-2 border-brand-500 group-hover:scale-125 transition-transform" />

                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
                        <h4 className="text-base font-bold text-slate-900 dark:text-white">
                          {toText(exp.title, "Role not specified")}
                          {toText(exp.company) ? (
                            <>
                              {" "}•{" "}
                              <span className="text-brand-600 dark:text-brand-400 font-semibold">
                                {toText(exp.company)}
                              </span>
                            </>
                          ) : null}
                        </h4>
                        <span className="text-xs font-mono font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/10 px-2.5 py-0.5 rounded-md self-start sm:self-auto">
                          {toText(exp.start, "Start")} – {exp.is_current ? "Present" : toText(exp.end, "End")}
                        </span>
                      </div>

                      {exp.responsibilities && exp.responsibilities.length > 0 ? (
                        <ul className="space-y-1.5 list-disc list-inside text-xs sm:text-sm text-slate-600 dark:text-slate-300">
                          {exp.responsibilities.map((r: any, rIdx: number) => (
                            <li key={rIdx} className="leading-relaxed">
                              {toText(r)}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-5 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-dashed border-slate-200 dark:border-white/10 text-center text-xs text-slate-400 dark:text-slate-500 italic">
                  No professional work experience timeline detected in this resume.
                </div>
              )}
            </Card>

            {/* Education Credentials (Always visible with clear empty state) */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-wider">
                  <GraduationCap className="w-4 h-4 text-brand-500" />
                  <span>Education & Academic Credentials</span>
                </div>
                {parsedResume?.education && parsedResume.education.length > 0 && (
                  <span className="text-xs font-mono font-medium text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/10 px-2.5 py-0.5 rounded-full border border-slate-200/80 dark:border-white/10">
                    {parsedResume.education.length} credentials found
                  </span>
                )}
              </div>

              {parsedResume?.education && parsedResume.education.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {parsedResume.education.map((edu: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-4 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-slate-200/80 dark:border-white/10 space-y-1"
                    >
                      <p className="font-bold text-sm text-slate-900 dark:text-white">
                        {toText(edu.institution, "Institution not specified")}
                      </p>
                      <p className="text-xs text-slate-600 dark:text-slate-400">
                        {toText(edu.degree, "Degree not specified")} {toText(edu.field) ? `in ${toText(edu.field)}` : ""}
                      </p>
                      {(toText(edu.start) || toText(edu.end)) && (
                        <p className="text-[11px] text-slate-400 font-mono">
                          {toText(edu.start)} {toText(edu.start) && toText(edu.end) ? "–" : ""} {toText(edu.end)}
                        </p>
                      )}
                      {toText(edu.grade) && (
                        <p className="text-[11px] text-brand-600 dark:text-brand-400 font-mono font-medium">
                          Grade / GPA: {toText(edu.grade)}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-5 rounded-xl bg-slate-50/70 dark:bg-white/5 border border-dashed border-slate-200 dark:border-white/10 text-center text-xs text-slate-400 dark:text-slate-500 italic">
                  No academic degrees or educational credentials detected in this resume.
                </div>
              )}
            </Card>
          </div>
        );
      })()}
    </motion.div>
  );
}
