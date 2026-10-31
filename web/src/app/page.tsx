"use client";

import { useState } from "react";
import Link from "next/link";
import {
  UploadCloud,
  FileCheck,
  Briefcase,
  GraduationCap,
  Sparkles,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  User,
  Target,
  ArrowRight,
} from "lucide-react";
import SkillChip from "@/components/SkillChip";
import UploadWarning from "@/components/UploadWarning";
import { SAMPLE_CANDIDATES } from "@/data/samples";
import { api, type ParseResponseData } from "@/lib/api";

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<ParseResponseData | null>(null);
  const [selectedSample, setSelectedSample] = useState<string>("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setSelectedSample("");
      setError(null);
    }
  };

  const handleParse = async () => {
    if (!selectedFile) {
      setError("Please select a resume file or pick a sample resume.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.parseResume(selectedFile);
      setParsedData(data);
    } catch (err: any) {
      setError(err?.message || "Failed to parse resume document.");
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
          email: { value: `${sample.name.toLowerCase().replace(/[^a-z]/g, "")}@example.com`, confidence: 1.0, verified: true },
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
        skills: sample.skills.map((name) => ({
          raw: name,
          confidence: 1.0,
          verified: true,
          category_hint: "technical",
          evidence: `Directly utilized ${name} in production project development.`,
        })),
        meta: {
          confidence: 0.98,
          field_sources: { name: "rules", experience: "llm", skills: "merged" },
          llm_field_count: 8,
          unverified_count: 0,
        },
      },
      profile: {
        skills: sample.skills.map((name) => ({
          slug: name.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
          name: name,
          category: "technical",
          proficiency: 4,
          years: 3.0,
          inferred: false,
          confidence: 1.0,
          evidence: [`Directly applied ${name} in production project development.`],
        })),
        unrecognized: [],
      },
      raw_text: sample.rawText,
      confidence: 0.98,
      unmapped_skills: [],
    } as any);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <UploadWarning />

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            Resume Extraction & Talent Profile
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Hybrid parser combining deterministic pattern extraction with grounded LLM reasoning.
          </p>
        </div>

        {/* Quick Sample Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Demo Samples:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {SAMPLE_CANDIDATES.map((sample) => (
              <button
                key={sample.id}
                onClick={() => loadSample(sample.id)}
                className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-all ${
                  selectedSample === sample.id
                    ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                    : "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-700 hover:border-indigo-400"
                }`}
              >
                {sample.name.split(" ")[0]} ({sample.title.split(" ")[0]})
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Upload Zone */}
      <div className="bg-white dark:bg-slate-900 border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-500 rounded-xl p-6 sm:p-8 text-center transition-colors">
        <UploadCloud className="w-12 h-12 text-indigo-500 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">
          Upload Candidate Resume
        </h3>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto mt-1 mb-4">
          Supports PDF, DOCX, or plain text formats. Text extraction is grounded with verbatim span references.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 text-sm font-medium hover:bg-indigo-100 transition-colors">
            <FileText className="w-4 h-4" />
            <span>{selectedFile ? selectedFile.name : "Choose File..."}</span>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>

          <button
            onClick={handleParse}
            disabled={!selectedFile || loading}
            className={`inline-flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold text-white shadow-sm transition-all ${
              !selectedFile || loading
                ? "bg-slate-300 dark:bg-slate-700 cursor-not-allowed"
                : "bg-indigo-600 hover:bg-indigo-700"
            }`}
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Parsing Pipeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Parse Resume</span>
              </>
            )}
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 text-xs sm:text-sm flex items-center justify-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Structured Profile Display */}
      {parsedData && (() => {
        const parsedResume = parsedData.parsed || (parsedData as any).profile;
        const skillsList = parsedData.profile?.skills || (parsedResume?.skills as any[]) || [];
        const confidencePct = Math.round(((parsedResume?.meta as any)?.confidence || 0.95) * 100);

        return (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Header Card */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-full bg-indigo-100 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-xl font-bold font-mono">
                  {parsedResume?.personal?.name?.value?.[0] || "C"}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>{parsedResume?.personal?.name?.value || "Candidate"}</span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300">
                      <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                      Confidence: {confidencePct}%
                    </span>
                  </h2>
                  <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {parsedResume?.personal?.email?.value && (
                      <span>{parsedResume.personal.email.value}</span>
                    )}
                    {parsedResume?.personal?.phone?.value && (
                      <span>• {parsedResume.personal.phone.value}</span>
                    )}
                    {parsedResume?.personal?.location?.value && (
                      <span>
                        • {typeof parsedResume.personal.location.value === "object"
                          ? `${(parsedResume.personal.location.value as any).city || ""}, ${(parsedResume.personal.location.value as any).region || ""}`
                          : String(parsedResume.personal.location.value)}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Quick Actions & Pipeline Stage Indicators */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 border-t md:border-t-0 md:border-l border-slate-200 dark:border-slate-800 pt-3 md:pt-0 md:pl-6 text-xs">
                <div className="flex items-center gap-2">
                  <Link
                    href={`/match?candidate_id=${parsedData.candidate_id || selectedSample}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs shadow-sm transition-colors"
                  >
                    <Target className="w-3.5 h-3.5" />
                    <span>Match against Jobs</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                  <Link
                    href={`/coach?candidate_id=${parsedData.candidate_id || selectedSample}`}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-medium text-xs border border-slate-200 dark:border-slate-700 transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Career Coach</span>
                  </Link>
                </div>
                <div className="hidden lg:flex items-center gap-2 text-slate-500 pl-2">
                  <div className="text-right">
                    <p className="font-semibold text-slate-700 dark:text-slate-300">Agent Trace</p>
                    <p className="text-[11px]">Parser: Grounded</p>
                  </div>
                  <FileCheck className="w-7 h-7 text-indigo-500" />
                </div>
              </div>
            </div>

            {/* Executive Summary */}
            {parsedResume?.summary?.value && (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <User className="w-4 h-4 text-indigo-500" />
                  Executive Summary
                </h3>
                <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  {parsedResume.summary.value}
                </p>
              </div>
            )}

            {/* Normalized Skills Breakdown */}
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-indigo-500" />
                  Normalized Skills & Provenance
                </h3>
                <span className="text-xs text-slate-400">
                  {skillsList.length} skills detected
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                {skillsList.map((sk: any, idx: number) => (
                  <SkillChip
                    key={idx}
                    name={sk.name || sk.raw || "Skill"}
                    category={sk.category || sk.category_hint || "technical"}
                    evidence={sk.evidence ? (Array.isArray(sk.evidence) ? sk.evidence : [sk.evidence]) : []}
                    confidence={sk.confidence || 1.0}
                    inferred={sk.inferred}
                    years={sk.years}
                  />
                ))}
              </div>
            </div>

            {/* Experience Timeline */}
            {parsedResume?.experience && parsedResume.experience.length > 0 && (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-1.5">
                  <Briefcase className="w-4 h-4 text-indigo-500" />
                  Work Experience Timeline
                </h3>
                <div className="space-y-4">
                  {parsedResume.experience.map((exp: any, idx: number) => (
                    <div key={idx} className="border-l-2 border-indigo-200 dark:border-indigo-800 pl-4 py-1">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                          {exp.title?.value || "Role"} • {exp.company?.value || "Company"}
                        </h4>
                        <span className="text-xs text-slate-500 font-mono">
                          {exp.start?.value || "Start"} – {exp.is_current ? "Present" : exp.end?.value || "End"}
                        </span>
                      </div>
                      {exp.responsibilities && (
                        <ul className="mt-2 space-y-1 list-disc list-inside text-xs text-slate-600 dark:text-slate-300">
                          {exp.responsibilities.map((r: any, rIdx: number) => (
                            <li key={rIdx}>{r.value || String(r)}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Education */}
            {parsedResume?.education && parsedResume.education.length > 0 && (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <GraduationCap className="w-4 h-4 text-indigo-500" />
                  Education & Credentials
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {parsedResume.education.map((edu: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                      <p className="font-semibold text-sm text-slate-900 dark:text-white">
                        {edu.institution?.value || "University"}
                      </p>
                      <p className="text-xs text-slate-600 dark:text-slate-400">
                        {edu.degree?.value} {edu.field?.value ? `in ${edu.field.value}` : ""}
                      </p>
                      {edu.grade?.value && (
                        <p className="text-[11px] text-slate-500 font-mono mt-1">GPA: {edu.grade.value}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
