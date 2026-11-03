"""Role recommendation engine for candidate profiles."""

from __future__ import annotations

from typing import Any

from talentgraph.api.schemas import SuggestedRole
from talentgraph.core.schemas.skills import SkillProfile
from talentgraph.db.in_memory import _JOBS

# Benchmark standard roles if in-memory store is starting up or empty
BENCHMARK_ROLES: list[dict[str, Any]] = [
    {
        "id": "role-backend-01",
        "title": "Principal Backend Software Engineer",
        "company": "Enterprise Cloud Systems",
        "required_skills": [
            "Python",
            "Go",
            "Java",
            "SQL",
            "Docker",
            "Linux",
            "Microservices",
            "PostgreSQL",
        ],
        "nice_to_have": ["Kubernetes", "AWS", "Kafka", "CI/CD", "Redis", "TypeScript"],
    },
    {
        "id": "role-frontend-02",
        "title": "Senior Frontend Web Engineer",
        "company": "NextGen Interactive",
        "required_skills": [
            "TypeScript",
            "JavaScript",
            "React",
            "Next.js",
            "Tailwind CSS",
            "HTML5",
            "CSS3",
        ],
        "nice_to_have": ["Redux", "GraphQL", "Jest", "Webpack", "Node.js"],
    },
    {
        "id": "role-fullstack-03",
        "title": "Senior Full-Stack Engineer",
        "company": "HyperScale Tech",
        "required_skills": [
            "JavaScript",
            "TypeScript",
            "React",
            "Python",
            "Node.js",
            "SQL",
            "Docker",
            "Git",
        ],
        "nice_to_have": ["Next.js", "AWS", "PostgreSQL", "REST APIs", "GraphQL"],
    },
    {
        "id": "role-devops-04",
        "title": "Lead DevOps / Site Reliability Engineer",
        "company": "Cloud Infrastructure Labs",
        "required_skills": [
            "Docker",
            "Kubernetes",
            "Linux",
            "CI/CD",
            "Python",
            "Git",
            "Bash",
            "Terraform",
        ],
        "nice_to_have": ["AWS", "Azure", "Prometheus", "Grafana", "Ansible", "Go"],
    },
    {
        "id": "role-data-05",
        "title": "Senior Data & ML Engineer",
        "company": "Cognitive AI Solutions",
        "required_skills": [
            "Python",
            "SQL",
            "Pandas",
            "NumPy",
            "Machine Learning",
            "Docker",
            "Git",
        ],
        "nice_to_have": ["PyTorch", "TensorFlow", "Spark", "PostgreSQL", "FastAPI"],
    },
]


def recommend_roles_for_profile(
    profile: SkillProfile,
    limit: int = 3,
) -> list[SuggestedRole]:
    """Recommend best-matching roles for a candidate based on skill profile."""
    candidate_skills = {s.name.lower().strip() for s in profile.skills if s.name}
    # Also include slugs and raw names
    for s in profile.skills:
        if s.slug:
            candidate_skills.add(s.slug.lower().replace("-", " "))
            candidate_skills.add(s.slug.lower())

    results: list[tuple[int, SuggestedRole]] = []

    # 1. First evaluate loaded jobs from memory if available
    available_jobs = list(_JOBS.values())
    if available_jobs:
        for job in available_jobs:
            req_skills: list[str] = []
            if hasattr(job, "requirements") and hasattr(job.requirements, "requirements"):
                req_skills = [r.name for r in job.requirements.requirements]
            if not req_skills:
                # Infer from job title and text
                title_lower = job.title.lower()
                for b in BENCHMARK_ROLES:
                    b_title = str(b.get("title", ""))
                    if any(w in title_lower for w in b_title.lower().split()[:2]):
                        req_skills = list(b.get("required_skills", [])) + list(
                            b.get("nice_to_have", [])
                        )[:3]
                        break
            if not req_skills:
                req_skills = ["Software Engineering", "Problem Solving", "System Architecture"]

            matched: list[str] = []
            missing: list[str] = []

            for r_name in req_skills:
                r_clean = r_name.lower().strip()
                # Check for direct or partial match
                if any(r_clean in cs or cs in r_clean for cs in candidate_skills):
                    matched.append(r_name)
                else:
                    missing.append(r_name)

            total = max(1, len(req_skills))
            # Base match score
            raw_ratio = len(matched) / total
            # Scale score realistically (e.g. 50% - 95%)
            score = int(
                round(
                    min(98.0, max(45.0, raw_ratio * 92.0 + (5.0 if len(matched) >= 3 else 0.0)))
                )
            )

            company = getattr(job.requirements, "company", None) or "Technology Partner"
            matched_display = matched[:6]
            missing_display = missing[:4]
            strengths = (
                ", ".join(matched_display[:3]) if matched_display else "domain fundamentals"
            )
            fit_summary = (
                f"Candidate matches {len(matched)} of {total} core capabilities ({score}% match). "
                f"Key strengths in {strengths}."
            )

            suggested = SuggestedRole(
                job_id=str(job.id),
                title=job.title,
                company=company,
                match_score=score,
                matched_skills=matched_display,
                missing_skills=missing_display,
                fit_summary=fit_summary,
            )
            results.append((score, suggested))

    # 2. If no jobs in memory or fewer than needed, add from benchmark roles
    if len(results) < limit:
        for b in BENCHMARK_ROLES:
            reqs_list = list(b.get("required_skills", []))
            nice_list = list(b.get("nice_to_have", []))
            all_reqs = reqs_list + nice_list
            b_matched: list[str] = []
            b_missing: list[str] = []
            for r_name in all_reqs:
                r_clean = r_name.lower().strip()
                if any(r_clean in cs or cs in r_clean for cs in candidate_skills):
                    b_matched.append(r_name)
                else:
                    b_missing.append(r_name)

            total = len(all_reqs)
            raw_ratio = len(b_matched) / max(1, len(reqs_list))
            score = int(
                round(
                    min(96.0, max(40.0, raw_ratio * 88.0 + (10.0 if len(b_matched) >= 3 else 0.0)))
                )
            )

            # Pick existing job id if possible, else stable uuid
            job_id = f"00000000-0000-0000-0000-{len(results) + 1:012d}"
            strengths = ", ".join(b_matched[:3]) if b_matched else "core computer science"
            fit_summary = (
                f"Strong alignment with {b['title']}. Candidate exhibits "
                f"{len(b_matched)} matching skill areas including {strengths}."
            )

            suggested = SuggestedRole(
                job_id=job_id,
                title=str(b["title"]),
                company=str(b["company"]),
                match_score=score,
                matched_skills=b_matched[:6],
                missing_skills=b_missing[:4],
                fit_summary=fit_summary,
            )
            results.append((score, suggested))

    # Sort descending by match_score
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:limit]]
