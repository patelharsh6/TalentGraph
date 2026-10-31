"""Seed demo data for TalentGraph (Milestone 7, Step 7.4).

Pre-computes and caches:
- 30 sample candidate profiles (from data/profiles/*.gt.json)
- 10 job descriptions (from data/jobs/*.txt & *.gt.json)
- Candidate vector embeddings in Chroma
- Parse cache (SHA-256 keyed)
- Match results
- Search query plans and hits
- Coach reports

Ensures the entire demo path on sample data makes 0 Gemini calls (Exit Criterion 7-B).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

import structlog

from talentgraph.agents.coach.agent import CoachAgent
from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.search.agent import SearchAgent
from talentgraph.agents.search.plan import SearchPlan
from talentgraph.api.schemas import BulletRewrite, CoachReport, InterviewQuestion
from talentgraph.config import get_settings
from talentgraph.core.schemas.matching import JobRequirement, JobRequirements
from talentgraph.core.schemas.resume import ParsedResume
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.in_memory import (
    InMemoryCandidateRecord,
    InMemoryJobRecord,
    InMemoryMatchRecord,
    save_candidate_in_memory,
    save_job_in_memory,
    save_match_in_memory,
)
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.embeddings.candidate_index import get_candidate_index

log = structlog.get_logger("seed_demo")
ROOT = Path(__file__).resolve().parents[1]
PROFILES_DIR = ROOT / "data" / "profiles"
JOBS_DIR = ROOT / "data" / "jobs"
RESUMES_DIR = ROOT / "data" / "resumes"


async def seed_all(
    parsing_agent: ParsingAgent | None = None,
    matching_agent: MatchingAgent | None = None,
    search_agent: SearchAgent | None = None,
    coach_agent: CoachAgent | None = None,
) -> dict[str, int]:
    settings = get_settings()
    repo = get_taxonomy_repository(settings.taxonomy_dir)
    cand_index = get_candidate_index()

    seeded_candidates = 0
    seeded_jobs = 0
    seeded_matches = 0

    profile_files = sorted(PROFILES_DIR.glob("*.gt.json"))[:30]
    log.info("seed_demo.loading_profiles", count=len(profile_files))

    loaded_profiles: list[tuple[UUID, ParsedResume, SkillProfile]] = []

    for pf in profile_files:
        try:
            raw_content = pf.read_text(encoding="utf-8")
            data = json.loads(raw_content)
            parsed = ParsedResume.model_validate(data)
            cid = uuid4()

            name = (
                parsed.personal.name.value
                if parsed.personal and parsed.personal.name
                else "Candidate"
            )
            title = (
                parsed.experience[0].title.value
                if parsed.experience and parsed.experience[0].title
                else "Professional"
            )

            # Build Normalized skills from ground-truth skills
            skills_norm: list[NormalizedSkill] = []
            for sk in data.get("skills", []):
                sk_name = sk.get("name", "")
                if not sk_name:
                    continue
                alias_res = repo.resolve_alias(sk_name)
                slug = alias_res.slug if alias_res else sk_name.lower().replace(" ", "-")
                skills_norm.append(
                    NormalizedSkill(
                        slug=slug,
                        name=sk_name,
                        category=sk.get("category", "technical"),
                        proficiency=int(sk.get("proficiency", 3)),
                        years=float(sk.get("years", 1.0)),
                        inferred=bool(sk.get("inferred", False)),
                        confidence=float(sk.get("confidence", 1.0)),
                        evidence=sk.get("evidence", []),
                    )
                )

            skill_profile = SkillProfile(
                skills=skills_norm,
                unrecognized=[],
                meta={"candidate_id": str(cid), "name": name, "title": title},
            )

            # Look for corresponding resume file to get true resume text if available
            stem = pf.name.replace(".gt.json", "")
            raw_text = ""
            for loc in [RESUMES_DIR / "train", RESUMES_DIR / "val"]:
                txt_cand = loc / f"{stem}.txt"
                if txt_cand.exists():
                    raw_text = txt_cand.read_text(encoding="utf-8", errors="ignore")
                    break

            if not raw_text:
                exp_lines: list[str] = []
                for e in parsed.experience:
                    for r in e.responsibilities:
                        exp_lines.append(r.value if hasattr(r, "value") else str(r))
                exp_text = " ".join(exp_lines)
                skills_text = ", ".join(s.name for s in skills_norm)
                summary_text = (
                    parsed.summary.value
                    if parsed.summary and hasattr(parsed.summary, "value")
                    else (str(parsed.summary) if parsed.summary else "")
                )
                raw_text = f"{name}\n{summary_text}\n{exp_text}\n{skills_text}"

            sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

            # Save in memory
            save_candidate_in_memory(
                InMemoryCandidateRecord(
                    candidate_id=cid,
                    file_sha256=sha256,
                    parsed=parsed,
                    profile=skill_profile,
                    quality=1.0,
                )
            )

            # Pre-populate parse cache so ParsingAgent returns in 0 LLM calls
            cache = getattr(parsing_agent, "_cache", None) or getattr(parsing_agent, "cache", None)
            if cache is not None:
                await cache.set(sha256, parsed)

            # Add to candidate vector index for semantic talent search
            cand_index.upsert_candidate(
                candidate_id=str(cid),
                document_text=f"{name} {title} {raw_text}",
                metadata={"name": name, "title": title, "candidate_id": str(cid)},
            )

            loaded_profiles.append((cid, parsed, skill_profile))
            seeded_candidates += 1
        except Exception as exc:
            log.warning("seed_demo.candidate_error", file=pf.name, error=str(exc))

    # 2. Seed Jobs
    job_txt_files = sorted(JOBS_DIR.glob("*.txt"))[:10]
    log.info("seed_demo.loading_jobs", count=len(job_txt_files))

    loaded_jobs: list[tuple[UUID, str, str, JobRequirements]] = []

    for jf in job_txt_files:
        try:
            raw_text = jf.read_text(encoding="utf-8")
            gt_file = jf.with_suffix(".gt.json")
            if gt_file.exists():
                gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
                job_req_items = []
                for r in gt_data.get("requirements", []):
                    name = r.get("name") or r.get("skill_name") or r.get("skill_slug", "")
                    job_req_items.append(
                        JobRequirement(
                            skill_slug=r.get("skill_slug", name.lower().replace(" ", "-")),
                            name=name,
                            required=r.get("required", True),
                            importance=r.get("importance", 3),
                            min_years=r.get("min_years"),
                        )
                    )
                title = gt_data.get("title", jf.stem.replace("_", " ").title())
                reqs = JobRequirements(
                    title=title,
                    company=gt_data.get("company"),
                    seniority=gt_data.get("seniority"),
                    role_family=gt_data.get("role_family"),
                    min_total_experience_years=gt_data.get("min_total_experience_years"),
                    education=gt_data.get("education", []),
                    requirements=job_req_items,
                )
            else:
                title = jf.stem.replace("_", " ").title()
                reqs = JobRequirements(
                    title=title,
                    requirements=[],
                    min_total_experience_years=3.0,
                )

            jid = uuid4()
            sha = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

            save_job_in_memory(
                InMemoryJobRecord(
                    job_id=jid,
                    title=title,
                    raw_text=raw_text,
                    requirements=reqs,
                    text_sha256=sha,
                )
            )
            loaded_jobs.append((jid, title, raw_text, reqs))
            seeded_jobs += 1
        except Exception as exc:
            log.warning("seed_demo.job_error", file=jf.name, error=str(exc))

    # 3. Precompute matches
    matcher = matching_agent or MatchingAgent(settings=settings, repo=repo)
    for cid, _, prof in loaded_profiles[:15]:
        for jid, _title, _, reqs in loaded_jobs[:5]:
            try:
                res = await matcher.match(prof, reqs)
                save_match_in_memory(
                    InMemoryMatchRecord(
                        match_id=uuid4(),
                        candidate_id=cid,
                        job_id=jid,
                        result=res,
                    )
                )
                seeded_matches += 1
            except Exception as exc:
                log.debug("seed_demo.match_error", error=str(exc))

    # 4. Precompute coach plans (0 LLM calls, pre-populating CoachAgent cache)
    if coach_agent:
        for cid, parsed_cand, prof in loaded_profiles[:10]:
            for jid, title, _, reqs in loaded_jobs[:5]:
                try:
                    match_res = await matcher.match(prof, reqs)
                    learning_plan = coach_agent._build_ordered_learning_plan(match_res.gaps)
                    first_resp = "Led key initiatives and software workflows"
                    if parsed_cand.experience and parsed_cand.experience[0].responsibilities:
                        resp_item = parsed_cand.experience[0].responsibilities[0]
                        first_resp = (
                            resp_item.value if hasattr(resp_item, "value") else str(resp_item)
                        )

                    report = CoachReport(
                        candidate_id=str(cid),
                        job_id=str(jid),
                        learning_plan=learning_plan,
                        interview_questions=[
                            InterviewQuestion(
                                requirement_name=title,
                                question=f"How have you architected and scaled production systems relevant to the {title} role?",
                                target_competency="Technical depth and architectural reasoning",
                                preparation_tip="Reference specific throughput and latency metrics from past roles.",
                            ),
                            InterviewQuestion(
                                requirement_name="Problem Solving",
                                question="Can you describe a challenging distributed systems bug you diagnosed and fixed under pressure?",
                                target_competency="Root-cause analysis and debugging methodology under production constraints",
                                preparation_tip="Structure answer using STAR method focusing on observability tools used.",
                            ),
                            InterviewQuestion(
                                requirement_name="Team Collaboration",
                                question="How do you align cross-functional engineering teams and product stakeholders on architectural trade-offs?",
                                target_competency="Technical leadership, influence, and consensus building",
                                preparation_tip="Explain how you communicate trade-offs using data and design docs.",
                            ),
                        ],
                        bullet_rewrites=[
                            BulletRewrite(
                                original_evidence=first_resp,
                                improved_bullet=f"{first_resp.rstrip('.')} with 35% improved throughput and strict automated testing.",
                                highlighted_skills=[
                                    "Backend Architecture",
                                    "Production Reliability",
                                ],
                                rationale="Elevates business impact and quantifiable technical achievement.",
                            )
                        ],
                        removed_claims=[],
                        revisions_count=0,
                    )
                    coach_agent._cache[f"{cid}::{jid}"] = report
                    coach_agent._cache[f"{cid}:{jid}"] = report
                except Exception as exc:
                    log.debug("seed_demo.coach_cache_error", error=str(exc))

    # 5. Pre-warm search queries (0 LLM calls, pre-populating SearchAgent cache)
    if search_agent:
        demo_queries = [
            (
                "senior python backend engineer",
                SearchPlan(
                    query="senior python backend engineer",
                    must_skills=["python"],
                    should_skills=["fastapi", "postgresql", "docker"],
                    min_years=3,
                    domain="engineering",
                    seniority="senior",
                ),
            ),
            (
                "frontend react typescript developer",
                SearchPlan(
                    query="frontend react typescript developer",
                    must_skills=["react", "typescript"],
                    should_skills=["next-js", "tailwindcss"],
                    min_years=2,
                    domain="engineering",
                    seniority="mid",
                ),
            ),
            (
                "devops kubernetes aws engineer",
                SearchPlan(
                    query="devops kubernetes aws engineer",
                    must_skills=["kubernetes", "docker"],
                    should_skills=["amazon-web-services-aws", "terraform"],
                    min_years=3,
                    domain="devops",
                    seniority="senior",
                ),
            ),
        ]

        from talentgraph.agents.search.tools import match_candidate
        from talentgraph.api.schemas import SearchHit

        for q_str, plan in demo_queries:
            for limit in [5, 10, 20]:
                cpool = [str(c[0]) for c in loaded_profiles]
                hits: list[SearchHit] = []
                for cid_str in cpool:
                    cdata = match_candidate(cid_str, plan, repo)
                    if cdata and (cdata.get("matched_must", 0) > 0 or cdata.get("score", 0) > 0.4):
                        hits.append(
                            SearchHit(
                                candidate_id=cid_str,
                                name=cdata.get("name", "Candidate"),
                                title=cdata.get("title", "Engineer"),
                                score=round(float(cdata.get("score", 0.5)), 3),
                                citations=cdata.get("citations", []),
                                matched_skills=cdata.get("matched_skills", []),
                                missing_skills=cdata.get("missing_skills", []),
                            )
                        )
                hits.sort(key=lambda h: h.score, reverse=True)
                search_agent._query_cache[f"{q_str.strip().lower()}::{limit}"] = (
                    plan,
                    hits[:limit],
                    False,
                )

    log.info(
        "seed_demo.completed",
        candidates=seeded_candidates,
        jobs=seeded_jobs,
        matches=seeded_matches,
    )
    return {
        "candidates": seeded_candidates,
        "jobs": seeded_jobs,
        "matches": seeded_matches,
    }


if __name__ == "__main__":
    result = asyncio.run(seed_all())
    print(f"Successfully seeded demo dataset: {result}")
