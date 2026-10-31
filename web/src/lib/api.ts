import type { components, paths } from "./api-types";

export type ParseResponseData = components["schemas"]["ParseResponseData"];
export type MatchResult = components["schemas"]["MatchResult"];
export type MatchRequest = components["schemas"]["MatchRequest"];
export type RankRequest = components["schemas"]["RankRequest"];
export type RankResponseData = components["schemas"]["RankResponseData"];
export type SearchHit = components["schemas"]["SearchHit"];
export interface SearchPlan {
  must_skills?: string[];
  should_skills?: string[];
  min_years?: number | null;
  domain?: string | null;
  seniority?: string | null;
}
export type SearchResponseData = components["schemas"]["SearchResponseData"];
export type CoachReport = components["schemas"]["CoachReport"];
export type CoachRequest = components["schemas"]["CoachRequest"];
export type SkillSearchItem = components["schemas"]["SkillSearchItem"];
export type CandidateDetailResponse = components["schemas"]["CandidateDetailResponse"];

// Client-side helper calling Next.js route proxy (/api/...)
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = path.startsWith("/") ? path : `/${path}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      errorDetail = errJson.detail || errJson.title || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  // Parse
  async parseResume(file: File): Promise<ParseResponseData> {
    const formData = new FormData();
    formData.append("file", file);
    const res = await request<{ data: ParseResponseData }>("/api/v1/parse", {
      method: "POST",
      body: formData,
    });
    return res.data;
  },

  // Candidates
  async listCandidates(): Promise<
    Array<{
      id: string;
      name: string;
      title: string;
      summary: string;
      skills_count: number;
      top_skills: string[];
      quality?: number | null;
    }>
  > {
    return request("/api/v1/candidates");
  },

  async getCandidate(candidateId: string): Promise<CandidateDetailResponse> {
    return request(`/api/v1/candidates/${candidateId}`);
  },

  // Jobs
  async listJobs(): Promise<
    Array<{
      id: string;
      title: string;
      raw_text: string;
      requirements: any;
    }>
  > {
    return request("/api/v1/jobs");
  },

  // Match
  async match(
    req: MatchRequest,
    blind: boolean = false
  ): Promise<MatchResult> {
    const res = await request<{ data: MatchResult }>(
      `/api/v1/match?blind=${blind}`,
      {
        method: "POST",
        body: JSON.stringify(req),
      }
    );
    return res.data;
  },

  async rank(
    req: RankRequest,
    blind: boolean = false
  ): Promise<RankResponseData[]> {
    return request(`/api/v1/match/rank?blind=${blind}`, {
      method: "POST",
      body: JSON.stringify(req),
    });
  },

  // Search
  async searchTalent(
    query: string,
    limit: number = 10
  ): Promise<SearchResponseData> {
    const res = await request<{ data: SearchResponseData }>("/api/v1/search", {
      method: "POST",
      body: JSON.stringify({ query, limit }),
    });
    return res.data;
  },

  // Career Coach
  async getCoachReport(req: CoachRequest): Promise<CoachReport> {
    const res = await request<{ data: CoachReport }>("/api/v1/coach", {
      method: "POST",
      body: JSON.stringify(req),
    });
    return res.data;
  },

  // Taxonomy
  async getTaxonomyTree(
    parentId?: number,
    depth: number = 1
  ): Promise<
    Array<{
      id: number;
      slug: string;
      name: string;
      type: string;
      level: number;
      parent_slug?: string | null;
      has_children: boolean;
    }>
  > {
    const query = new URLSearchParams();
    if (parentId !== undefined) query.set("parent_id", String(parentId));
    query.set("depth", String(depth));
    return request(`/api/v1/skills/taxonomy?${query.toString()}`);
  },

  async searchTaxonomy(query: string): Promise<SkillSearchItem[]> {
    return request(`/api/v1/skills/search?q=${encodeURIComponent(query)}`);
  },

  // Evaluation Metrics
  async getEvalSummary(): Promise<{
    summary: {
      total_metrics: number;
      passing_metrics: number;
      compliance_rate: string;
      last_audit: string;
    };
    metrics: Array<{
      id: string;
      name: string;
      target: string;
      value: any;
      unit: string;
      status: string;
      source: string;
      description: string;
    }>;
  }> {
    return request("/api/v1/eval/summary");
  },
};
